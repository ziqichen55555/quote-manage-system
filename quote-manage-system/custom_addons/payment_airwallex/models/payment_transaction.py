# -*- coding: utf-8 -*-
"""payment.transaction extension for Airwallex.

Implements the four hooks that the generic payment framework calls into:

* ``_get_specific_rendering_values``  -- supply the front-end with the
  PaymentIntent client_secret so the JS SDK can redirect to the HPP.
* ``_send_payment_request``           -- create the PaymentIntent on
  Airwallex (server-to-server).
* ``_get_tx_from_notification_data``  -- locate the local transaction from
  webhook / return-URL payload.
* ``_process_notification_data``      -- update the local state based on
  the latest PaymentIntent status from Airwallex.
"""

import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_airwallex import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------------------
    # We persist the Airwallex IDs so webhook deduplication and refunds
    # can find the local row without a status round-trip.
    # --------------------------------------------------------------
    airwallex_intent_id = fields.Char(
        string="Airwallex PaymentIntent ID",
        readonly=True,
        copy=False,
        index=True,
    )
    airwallex_client_secret = fields.Char(
        string="Airwallex Client Secret",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )

    # ------------------------------------------------------------------
    # Step 1: render the form. We do NOT redirect from the server side --
    # Airwallex's HPP is reached via the JS SDK, so we hand the front-end
    # the credentials it needs and let payment_form.js call
    # ``payments.redirectToCheckout()``.
    # ------------------------------------------------------------------
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'airwallex':
            return res

        # PaymentIntent must exist before the front-end redirect. We create
        # it lazily here rather than in ``_send_payment_request`` because the
        # framework calls _send_payment_request only for direct/S2S flows.
        if not self.airwallex_intent_id:
            self._airwallex_create_payment_intent()

        return {
            'airwallex_env': 'prod' if self.provider_id.state == 'enabled' else 'demo',
            'airwallex_intent_id': self.airwallex_intent_id,
            'airwallex_client_secret': self.sudo().airwallex_client_secret,
            'airwallex_currency': self.currency_id.name,
            'airwallex_country_code': (
                self.partner_country_id.code or self.company_id.country_id.code or 'AU'
            ),
            'airwallex_success_url': self._airwallex_build_return_url('return'),
            'airwallex_cancel_url': self._airwallex_build_return_url('cancel'),
        }

    # ------------------------------------------------------------------
    # PaymentIntent creation (server -> Airwallex).
    # ------------------------------------------------------------------
    def _airwallex_create_payment_intent(self):
        """POST /pa/payment_intents/create.

        Stored fields ``airwallex_intent_id`` and ``airwallex_client_secret``
        are written back on success. Idempotent through ``request_id`` =
        local transaction reference.
        """
        self.ensure_one()
        provider = self.provider_id
        # Amount is sent in MAJOR units (e.g. 12.34 AUD). Airwallex differs
        # from Stripe here -- no x100 conversion.
        payload = {
            'request_id': self.reference,
            'amount': float(self.amount),
            'currency': self.currency_id.name,
            'merchant_order_id': self.reference,
            'descriptor': (self.company_id.name or 'Re-Ware')[:32],
            'order': {
                'products': [{
                    'name': line.name[:120],
                    'quantity': int(line.product_uom_qty or 1),
                    'unit_price': float(line.price_unit or 0.0),
                    'desc': (line.name or '')[:250],
                } for line in self.sale_order_ids.order_line[:50]],
            } if self.sale_order_ids else {},
            'customer': self._airwallex_build_customer_payload(),
            'return_url': self._airwallex_build_return_url('return'),
        }
        result = provider._airwallex_make_request(
            const.ENDPOINT_INTENT_CREATE,
            payload=payload,
            idempotency_key=self.reference,
        )
        intent_id = result.get('id')
        client_secret = result.get('client_secret')
        if not intent_id or not client_secret:
            raise ValidationError(_(
                "Airwallex did not return a usable PaymentIntent. "
                "Got: %s", result,
            ))
        self.sudo().write({
            'airwallex_intent_id': intent_id,
            'airwallex_client_secret': client_secret,
            'provider_reference': intent_id,
        })
        _logger.info(
            "Airwallex PaymentIntent created: ref=%s intent_id=%s",
            self.reference, intent_id,
        )
        return result

    def _airwallex_build_customer_payload(self):
        """Optional -- pre-fills the HPP. Skipped silently when partner is bare."""
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return {}
        return {
            'merchant_customer_id': str(partner.id),
            'first_name': (partner.name or '').split(' ', 1)[0][:50] or 'Customer',
            'last_name': (partner.name or '').split(' ', 1)[-1][:50] or '-',
            'email': partner.email or '',
            'phone_number': partner.phone or '',
        }

    def _airwallex_build_return_url(self, kind):
        """Public absolute URL the customer is bounced back to after HPP."""
        base = (
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            or ''
        ).rstrip('/')
        return f"{base}/payment/airwallex/{kind}?reference={self.reference}"

    # ------------------------------------------------------------------
    # Step 2: webhook / return URL handling.
    # ------------------------------------------------------------------
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Resolve the local transaction matching an incoming webhook payload.

        Airwallex webhook envelope::

            {
              "id": "evt_...",
              "name": "payment_intent.succeeded",
              "data": {"object": {"id": "int_...", "merchant_order_id": "..."}}
            }
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'airwallex' or tx:
            return tx

        obj = (notification_data or {}).get('data', {}).get('object', {}) or {}
        intent_id = obj.get('id') or obj.get('payment_intent_id')
        reference = obj.get('merchant_order_id') or obj.get('request_id')

        domain = []
        if intent_id:
            domain = [('airwallex_intent_id', '=', intent_id)]
        elif reference:
            domain = [
                ('reference', '=', reference),
                ('provider_code', '=', 'airwallex'),
            ]
        if not domain:
            raise ValidationError(_(
                "Airwallex: webhook did not contain an intent_id or "
                "merchant_order_id. Payload: %s", notification_data,
            ))

        tx = self.search(domain, limit=1)
        if not tx:
            raise ValidationError(_(
                "Airwallex: no transaction found for %s.",
                intent_id or reference,
            ))
        return tx

    def _process_notification_data(self, notification_data):
        """Translate Airwallex PaymentIntent status -> Odoo state."""
        super()._process_notification_data(notification_data)
        if self.provider_code != 'airwallex':
            return

        obj = (notification_data or {}).get('data', {}).get('object', {}) or {}
        status = obj.get('status') or obj.get('payment_status')
        if not status:
            _logger.warning(
                "Airwallex notification for %s missing status field.",
                self.reference,
            )
            return

        if status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "Airwallex reported the payment failed (status=%s).", status,
            ))
        elif status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        else:
            _logger.warning(
                "Airwallex unknown PaymentIntent status %s for tx %s.",
                status, self.reference,
            )

    # ------------------------------------------------------------------
    # Step 3: refund (called by the generic Refund button on the tx form).
    # ------------------------------------------------------------------
    def _send_refund_request(self, amount_to_refund=None):
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'airwallex':
            return refund_tx

        if not self.airwallex_intent_id:
            raise ValidationError(_(
                "Airwallex: cannot refund a transaction with no PaymentIntent."
            ))
        payload = {
            'request_id': refund_tx.reference,
            'payment_intent_id': self.airwallex_intent_id,
            'amount': float(refund_tx.amount),
            'reason': 'requested_by_customer',
            'metadata': {'odoo_tx': refund_tx.reference},
        }
        result = self.provider_id._airwallex_make_request(
            const.ENDPOINT_INTENT_REFUND,
            payload=payload,
            idempotency_key=refund_tx.reference,
        )
        refund_tx.sudo().write({
            'provider_reference': result.get('id') or '',
            'airwallex_intent_id': self.airwallex_intent_id,
        })
        # Final state is decided by the refund webhook (refund.succeeded /
        # refund.failed). For now leave the refund tx in pending.
        refund_tx._set_pending()
        return refund_tx
