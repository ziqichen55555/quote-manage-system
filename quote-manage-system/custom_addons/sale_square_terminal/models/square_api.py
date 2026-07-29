# -*- coding: utf-8 -*-
"""Square REST client methods on res.company."""

import logging
import uuid

import requests

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.sale_square_terminal import const

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _square_api_base_url(self):
        self.ensure_one()
        env_key = self.square_environment or 'sandbox'
        return const.API_URLS.get(env_key, const.API_URLS['sandbox'])

    def _square_require_config(self):
        self.ensure_one()
        missing = []
        if not self.square_access_token:
            missing.append('Access Token')
        if not self.square_location_id:
            missing.append('Location ID')
        if not self.square_device_id:
            missing.append('Device ID')
        if missing:
            raise UserError(_(
                'Square Terminal is not configured (%s). '
                'Go to Settings → Sales → Square Terminal.'
            ) % ', '.join(missing))

    def _square_headers(self):
        self.ensure_one()
        return {
            'Authorization': 'Bearer %s' % self.square_access_token,
            'Content-Type': 'application/json',
            'Square-Version': const.SQUARE_VERSION,
        }

    def _square_request(self, method, path, payload=None, timeout=30):
        self.ensure_one()
        self._square_require_config()
        url = '%s%s' % (self._square_api_base_url(), path)
        try:
            response = requests.request(
                method,
                url,
                headers=self._square_headers(),
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            _logger.exception('Square API request failed: %s %s', method, path)
            raise UserError(_('Square API request failed: %s') % exc) from exc

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}

        if response.status_code >= 400 or data.get('errors'):
            errors = data.get('errors') or []
            detail = '; '.join(
                e.get('detail') or e.get('code') or str(e) for e in errors
            ) or response.text or ('HTTP %s' % response.status_code)
            _logger.error(
                'Square API error %s %s -> %s: %s',
                method, path, response.status_code, detail,
            )
            raise UserError(_('Square API error: %s') % detail)

        return data

    def _square_amount_money(self, amount, currency):
        """Convert Odoo monetary amount to Square Money (smallest unit)."""
        currency.ensure_one()
        rounding = currency.decimal_places if currency.decimal_places is not None else 2
        factor = 10 ** rounding
        cents = int(round(amount * factor))
        return {
            'amount': cents,
            'currency': currency.name,
        }

    def _square_create_terminal_checkout(self, amount, currency, reference, note=None):
        self.ensure_one()
        checkout = {
            'amount_money': self._square_amount_money(amount, currency),
            'device_options': {
                'device_id': self.square_device_id,
                'skip_receipt_screen': True,
            },
            'reference_id': (reference or '')[:40],
            'note': (note or reference or '')[:500],
            'payment_type': 'CARD_PRESENT',
        }
        if self.square_location_id:
            checkout['location_id'] = self.square_location_id
        payload = {
            'idempotency_key': str(uuid.uuid4()),
            'checkout': checkout,
        }
        data = self._square_request('POST', '/v2/terminals/checkouts', payload=payload)
        return data.get('checkout') or {}

    def _square_get_terminal_checkout(self, checkout_id):
        self.ensure_one()
        data = self._square_request(
            'GET',
            '/v2/terminals/checkouts/%s' % checkout_id,
        )
        return data.get('checkout') or {}

    def _square_cancel_terminal_checkout(self, checkout_id):
        self.ensure_one()
        data = self._square_request(
            'POST',
            '/v2/terminals/checkouts/%s/cancel' % checkout_id,
        )
        return data.get('checkout') or {}

    def _square_refund_payment(self, payment_id, amount, currency, reason=None):
        self.ensure_one()
        payload = {
            'idempotency_key': str(uuid.uuid4()),
            'payment_id': payment_id,
            'amount_money': self._square_amount_money(amount, currency),
        }
        if reason:
            payload['reason'] = reason[:192]
        data = self._square_request('POST', '/v2/refunds', payload=payload)
        return data.get('refund') or {}

    def _square_test_connection(self):
        """Validate token (+ optional location/device) without taking a payment."""
        self.ensure_one()
        if not self.square_access_token:
            raise UserError(_('Enter a Square Access Token first.'))

        url = '%s/v2/locations' % self._square_api_base_url()
        try:
            response = requests.get(
                url,
                headers=self._square_headers(),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise UserError(_('Square API request failed: %s') % exc) from exc

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}
        if response.status_code >= 400 or data.get('errors'):
            errors = data.get('errors') or []
            detail = '; '.join(
                e.get('detail') or e.get('code') or str(e) for e in errors
            ) or response.text or ('HTTP %s' % response.status_code)
            raise UserError(_('Square API error: %s') % detail)

        locations = data.get('locations') or []
        names = [loc.get('name') or loc.get('id') for loc in locations]
        msg_parts = [
            _('Connected to Square (%s).') % (self.square_environment or 'sandbox'),
            _('Locations found: %s') % (', '.join(names) if names else _('none')),
        ]
        if self.square_location_id:
            match = next(
                (loc for loc in locations if loc.get('id') == self.square_location_id),
                None,
            )
            if match:
                msg_parts.append(
                    _('Configured Location ID matches: %s') % (match.get('name') or match.get('id'))
                )
            else:
                msg_parts.append(
                    _('Warning: Location ID %s was not found in this account.')
                    % self.square_location_id
                )
        if self.square_device_id:
            msg_parts.append(
                _('Device ID is set (%s). Pairing is verified when you send a checkout.')
                % self.square_device_id
            )
        else:
            msg_parts.append(_('Device ID is not set yet — add it before taking payments.'))
        return '\n'.join(msg_parts)
