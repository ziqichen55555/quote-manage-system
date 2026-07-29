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
        """Optional webhook for terminal.checkout.updated.

        Primary UX uses the wizard Check Status button; this endpoint can
        auto-fulfill open sales orders when Square pushes COMPLETED.
        """
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
