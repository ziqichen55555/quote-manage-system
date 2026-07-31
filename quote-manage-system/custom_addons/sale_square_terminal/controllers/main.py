# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

from odoo.addons.sale_square_terminal import const

_logger = logging.getLogger(__name__)


def _json_error(message, status=400):
    return request.make_json_response({'ok': False, 'error': message}, status=status)


def _auth_company_from_bearer():
    """Authorize Reader app via company square_mobile_api_key."""
    auth = request.httprequest.headers.get('Authorization') or ''
    if not auth.lower().startswith('bearer '):
        return None
    token = auth.split(' ', 1)[1].strip()
    if not token:
        return None
    return request.env['res.company'].sudo().search([
        ('square_enabled', '=', True),
        ('square_mobile_api_key', '=', token),
    ], limit=1)


class SquareTerminalController(http.Controller):

    @http.route(
        '/square/terminal/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def square_terminal_webhook(self, **_kwargs):
        """Optional webhook for terminal.checkout.updated."""
        raw = request.httprequest.get_data()
        signature = request.httprequest.headers.get('x-square-hmacsha256-signature')
        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except ValueError:
            _logger.warning('Square webhook: invalid JSON')
            return request.make_json_response({'ok': False}, status=400)

        companies = request.env['res.company'].sudo().search([
            ('square_enabled', '=', True),
            ('square_access_token', '!=', False),
        ])
        keyed = companies.filtered('square_webhook_signature_key')
        verified = False
        if keyed:
            notification_url = request.httprequest.url
            body_text = raw.decode('utf-8')
            for company in keyed:
                digest = base64.b64encode(
                    hmac.new(
                        company.square_webhook_signature_key.encode('utf-8'),
                        (notification_url + body_text).encode('utf-8'),
                        hashlib.sha256,
                    ).digest()
                ).decode('utf-8')
                if hmac.compare_digest(digest, signature or ''):
                    verified = True
                    break
            if not verified:
                _logger.warning('Square webhook: signature mismatch')
                return request.make_json_response({'ok': False}, status=401)

        event_type = payload.get('type')
        if event_type not in (
            'terminal.checkout.updated',
            'terminal.checkout.created',
        ):
            return request.make_json_response({'ok': True, 'ignored': event_type})

        data_object = (payload.get('data') or {}).get('object') or {}
        checkout = (
            data_object.get('checkout')
            or data_object.get('terminal_checkout')
            or data_object
        )
        status = checkout.get('status')
        checkout_id = checkout.get('id')
        reference = checkout.get('reference_id')
        if status not in const.TERMINAL_SUCCESS_STATUSES or not checkout_id:
            return request.make_json_response({'ok': True, 'status': status})

        payment_ids = checkout.get('payment_ids') or []
        square_payment_id = payment_ids[0] if payment_ids else False

        Payment = request.env['account.payment'].sudo()
        if Payment.search([('square_checkout_id', '=', checkout_id)], limit=1):
            return request.make_json_response({'ok': True, 'already': True})

        order = False
        if reference:
            order = request.env['sale.order'].sudo().search([
                ('name', '=', reference),
            ], limit=1)
        if not order:
            _logger.info(
                'Square webhook: no sale order for checkout %s ref %s',
                checkout_id, reference,
            )
            return request.make_json_response({'ok': True, 'no_order': True})

        try:
            order._square_fulfill_after_payment(checkout, square_payment_id)
        except Exception:  # noqa: BLE001
            _logger.exception(
                'Square webhook fulfill failed for SO %s checkout %s',
                order.name, checkout_id,
            )
            return request.make_json_response({'ok': False}, status=500)

        return request.make_json_response({'ok': True, 'order': order.name})

    # ------------------------------------------------------------------
    # Reader companion app API
    # ------------------------------------------------------------------

    @http.route(
        '/square/reader/config',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def square_reader_config(self, **_kwargs):
        """Return Square SDK credentials for the authorized Reader app."""
        company = _auth_company_from_bearer()
        if not company:
            return _json_error('Unauthorized', 401)
        return request.make_json_response({
            'ok': True,
            'environment': company.square_environment or 'sandbox',
            'application_id': company.square_application_id or '',
            'access_token': company.square_access_token or '',
            'location_id': company.square_location_id or '',
            'company_name': company.name,
        })

    @http.route(
        '/square/reader/pending',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def square_reader_pending(self, **_kwargs):
        """List waiting Reader checkouts for this company."""
        company = _auth_company_from_bearer()
        if not company:
            return _json_error('Unauthorized', 401)
        checkouts = request.env['square.reader.checkout'].sudo().search([
            ('company_id', '=', company.id),
            ('state', '=', 'waiting'),
        ], order='id desc', limit=20)
        rows = []
        for c in checkouts:
            rows.append({
                'id': c.id,
                'name': c.name,
                'access_token': c.access_token,
                'amount': c.amount,
                'currency': c.currency_id.name,
                'sale_order': c.sale_order_id.name,
                'sale_order_id': c.sale_order_id.id,
                'partner': c.sale_order_id.partner_id.display_name,
            })
        return request.make_json_response({'ok': True, 'checkouts': rows})

    @http.route(
        '/square/reader/complete',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def square_reader_complete(self, **_kwargs):
        """Mark a pending checkout paid after Mobile Payments SDK success."""
        company = _auth_company_from_bearer()
        if not company:
            return _json_error('Unauthorized', 401)
        try:
            payload = json.loads(request.httprequest.get_data().decode('utf-8') or '{}')
        except ValueError:
            return _json_error('Invalid JSON')

        checkout_id = payload.get('checkout_id')
        access_token = payload.get('access_token')
        square_payment_id = payload.get('square_payment_id')
        if not square_payment_id:
            return _json_error('square_payment_id is required')

        Checkout = request.env['square.reader.checkout'].sudo()
        checkout = False
        if checkout_id:
            checkout = Checkout.browse(int(checkout_id)).exists()
        if not checkout and access_token:
            checkout = Checkout.search([('access_token', '=', access_token)], limit=1)
        if not checkout or checkout.company_id.id != company.id:
            return _json_error('Checkout not found', 404)

        try:
            payments = checkout.action_mark_paid(square_payment_id)
        except Exception as exc:  # noqa: BLE001
            _logger.exception('Reader complete failed for %s', checkout.name)
            return _json_error(str(exc), 500)

        return request.make_json_response({
            'ok': True,
            'checkout': checkout.name,
            'state': checkout.state,
            'payments': payments.mapped('name'),
            'sale_order': checkout.sale_order_id.name,
        })

    @http.route(
        '/square/reader/fail',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def square_reader_fail(self, **_kwargs):
        company = _auth_company_from_bearer()
        if not company:
            return _json_error('Unauthorized', 401)
        try:
            payload = json.loads(request.httprequest.get_data().decode('utf-8') or '{}')
        except ValueError:
            return _json_error('Invalid JSON')

        Checkout = request.env['square.reader.checkout'].sudo()
        checkout = False
        if payload.get('checkout_id'):
            checkout = Checkout.browse(int(payload['checkout_id'])).exists()
        if not checkout and payload.get('access_token'):
            checkout = Checkout.search([
                ('access_token', '=', payload['access_token']),
            ], limit=1)
        if not checkout or checkout.company_id.id != company.id:
            return _json_error('Checkout not found', 404)
        if checkout.state == 'waiting':
            checkout.write({
                'state': 'failed',
                'status_message': payload.get('message') or 'Failed on Reader App',
            })
        return request.make_json_response({'ok': True, 'state': checkout.state})
