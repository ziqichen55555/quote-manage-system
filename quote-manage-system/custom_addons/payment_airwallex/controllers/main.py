# -*- coding: utf-8 -*-
"""HTTP endpoints used by Airwallex.

Two routes:

* ``/payment/airwallex/return`` -- the customer is redirected here by the
  HPP after attempting payment. We re-fetch the PaymentIntent server-side
  (we do not trust query params) and let the framework decide where to
  push the customer next based on the resulting transaction state.

* ``/payment/airwallex/webhook`` -- Airwallex's authoritative POST. We
  verify the HMAC signature against the configured secret before doing
  anything with the body.
"""

import json
import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment_airwallex import const

_logger = logging.getLogger(__name__)


class AirwallexController(http.Controller):

    _return_url = '/payment/airwallex/return'
    _cancel_url = '/payment/airwallex/cancel'
    _webhook_url = '/payment/airwallex/webhook'

    # ------------------------------------------------------------------
    # Customer-facing return URL.
    # ------------------------------------------------------------------
    @http.route(
        _return_url, type='http', auth='public', methods=['GET'],
        csrf=False, save_session=False,
    )
    def airwallex_return_from_checkout(self, **data):
        """Customer hit Airwallex's ``successUrl``.

        We re-pull the PaymentIntent so the local state reflects what
        Airwallex actually recorded, then hand control back to the generic
        ``/payment/status`` page.
        """
        reference = data.get('reference')
        _logger.info("Airwallex return-URL hit: reference=%s data=%s", reference, data)
        if reference:
            tx_sudo = request.env['payment.transaction'].sudo().search(
                [('reference', '=', reference), ('provider_code', '=', 'airwallex')],
                limit=1,
            )
            if tx_sudo and tx_sudo.airwallex_intent_id:
                self._poll_intent_and_update(tx_sudo)
        return request.redirect('/payment/status')

    @http.route(
        _cancel_url, type='http', auth='public', methods=['GET'],
        csrf=False, save_session=False,
    )
    def airwallex_cancel_from_checkout(self, **data):
        """Customer hit Airwallex's ``cancelUrl`` (clicked Cancel on HPP)."""
        reference = data.get('reference')
        _logger.info("Airwallex cancel-URL hit: reference=%s", reference)
        if reference:
            tx_sudo = request.env['payment.transaction'].sudo().search(
                [('reference', '=', reference), ('provider_code', '=', 'airwallex')],
                limit=1,
            )
            if tx_sudo:
                tx_sudo._set_canceled("Customer cancelled on Airwallex HPP.")
        return request.redirect('/payment/status')

    # ------------------------------------------------------------------
    # Webhook (server-to-server, HMAC-signed).
    # ------------------------------------------------------------------
    @http.route(
        _webhook_url, type='http', auth='public', methods=['POST'],
        csrf=False, save_session=False,
    )
    def airwallex_webhook(self, **kwargs):
        """Receive an Airwallex webhook event.

        Verification per https://www.airwallex.com/docs/developer-tools/webhooks.
        Headers used:

        * ``x-timestamp`` -- ms since epoch when Airwallex sent it.
        * ``x-signature`` -- HMAC_SHA256(secret, timestamp + raw_body).

        We always return 200 once we've recorded the event so Airwallex
        doesn't retry; logical errors are captured in the log instead.
        """
        raw_body = request.httprequest.get_data(as_text=True)
        timestamp = request.httprequest.headers.get('x-timestamp', '')
        signature = request.httprequest.headers.get('x-signature', '')

        try:
            payload = json.loads(raw_body) if raw_body else {}
        except ValueError:
            _logger.warning("Airwallex webhook: non-JSON body received.")
            return ''

        event_name = payload.get('name') or ''
        _logger.info(
            "Airwallex webhook received: event=%s timestamp=%s payload=%s",
            event_name, timestamp, pprint.pformat(payload),
        )

        if event_name not in const.HANDLED_WEBHOOK_EVENTS:
            # Ack but don't process: Airwallex will not retry, and we keep
            # an audit-line in the server log.
            return ''

        # Resolve provider via the matching merchant_order_id -> tx.
        # We look the provider up via the candidate transaction so that
        # signature verification uses *that provider's* webhook secret
        # (multi-website / multi-provider safe).
        try:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'airwallex', payload,
            )
        except ValidationError:
            _logger.exception("Airwallex webhook: could not resolve transaction.")
            return ''

        provider_sudo = tx_sudo.provider_id.sudo()
        try:
            expected_sig = provider_sudo._airwallex_compute_signature(timestamp, raw_body)
        except Exception:  # noqa: BLE001 -- provider misconfigured, we want generic 401
            _logger.exception("Airwallex webhook: failed to compute signature.")
            return ''

        if not signature or not _safe_compare(signature, expected_sig):
            _logger.warning(
                "Airwallex webhook: HMAC mismatch for tx=%s (provider=%s).",
                tx_sudo.reference, provider_sudo.display_name,
            )
            # Returning 401 makes Airwallex retry, which is what we want
            # when somebody is forging events: real ones will keep
            # validating, forged ones will keep failing.
            return request.make_response('', status=401)

        try:
            tx_sudo._handle_notification_data('airwallex', payload)
        except Exception:  # noqa: BLE001 -- never raise out of a webhook
            _logger.exception(
                "Airwallex webhook: error while processing tx=%s event=%s.",
                tx_sudo.reference, event_name,
            )
        return ''


# ---------------------------------------------------------------------------
# Module-private helpers.
# ---------------------------------------------------------------------------
def _safe_compare(a, b):
    """Constant-time comparison of two strings (avoids HMAC timing leaks)."""
    import hmac
    return hmac.compare_digest(a or '', b or '')


def _poll_intent_and_update(tx_sudo):
    """Re-fetch the PaymentIntent on Airwallex and feed it through the
    standard notification pipeline.

    Used by the customer-facing return URL so the local state is up to
    date even if the webhook is delayed (rare but happens).
    """
    provider_sudo = tx_sudo.provider_id.sudo()
    endpoint = const.ENDPOINT_INTENT_RETRIEVE.format(intent_id=tx_sudo.airwallex_intent_id)
    try:
        intent = provider_sudo._airwallex_make_request(endpoint, method='GET')
    except ValidationError:
        _logger.exception("Airwallex: could not poll intent %s.", tx_sudo.airwallex_intent_id)
        return
    fake_event = {
        'name': 'payment_intent.poll',
        'data': {'object': intent},
    }
    tx_sudo._handle_notification_data('airwallex', fake_event)


# Bind module-private helper to controller class so the route handler can
# call it without monkey-patching ``self``.
AirwallexController._poll_intent_and_update = staticmethod(_poll_intent_and_update)
