# -*- coding: utf-8 -*-
"""Airwallex API endpoints, supported currencies, and status mappings.

Centralised so the rest of the module imports symbolic names instead of
hard-coding strings. Update this file when Airwallex versions an endpoint
or you want to extend supported currencies.
"""

# ---------------------------------------------------------------------------
# REST API base URLs.
# Airwallex exposes two physically separate environments. We pick by the
# ``payment.provider.state`` field (``test`` -> demo, ``enabled`` -> prod).
# ---------------------------------------------------------------------------
API_URLS = {
    'test': 'https://api-demo.airwallex.com',
    'enabled': 'https://api.airwallex.com',
}

# ---------------------------------------------------------------------------
# Components SDK (browser side). The SDK auto-targets the right environment
# based on the ``env`` we pass it, so a single CDN URL works for both.
# ---------------------------------------------------------------------------
SDK_URL = 'https://static.airwallex.com/components/sdk/v1/index.js'

# ---------------------------------------------------------------------------
# REST endpoints (relative to API_URLS[<state>]).
# ---------------------------------------------------------------------------
ENDPOINT_LOGIN = '/api/v1/authentication/login'
ENDPOINT_INTENT_CREATE = '/api/v1/pa/payment_intents/create'
ENDPOINT_INTENT_RETRIEVE = '/api/v1/pa/payment_intents/{intent_id}'
ENDPOINT_INTENT_CANCEL = '/api/v1/pa/payment_intents/{intent_id}/cancel'
ENDPOINT_INTENT_REFUND = '/api/v1/pa/refunds/create'

# ---------------------------------------------------------------------------
# Currencies Airwallex can charge in. Source:
# https://www.airwallex.com/docs/payments/currencies-and-payment-methods
# Keep this list narrow on purpose -- Re-Ware only needs the major ones, and
# Odoo will hide the provider on checkout for any currency not listed here.
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = (
    'AUD', 'CAD', 'CHF', 'CNY', 'EUR', 'GBP', 'HKD',
    'JPY', 'NZD', 'SGD', 'USD',
)

# ---------------------------------------------------------------------------
# PaymentIntent status -> Odoo transaction state.
# Reference: https://www.airwallex.com/docs/api#/Payment_Acceptance/Payment_Intents
# ---------------------------------------------------------------------------
PAYMENT_STATUS_MAPPING = {
    'pending': ('REQUIRES_PAYMENT_METHOD', 'REQUIRES_CUSTOMER_ACTION', 'REQUIRES_CAPTURE'),
    'done': ('SUCCEEDED',),
    'cancel': ('CANCELLED',),
    'error': ('FAILED', 'EXPIRED'),
}

# ---------------------------------------------------------------------------
# Webhook event names we care about. Any other event is ack'd with 200 but
# not processed (so Airwallex stops retrying).
# ---------------------------------------------------------------------------
HANDLED_WEBHOOK_EVENTS = (
    'payment_intent.succeeded',
    'payment_intent.cancelled',
    'payment_intent.failed',
    'payment_intent.requires_payment_method',
    'refund.succeeded',
    'refund.failed',
)
