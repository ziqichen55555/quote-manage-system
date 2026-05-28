# -*- coding: utf-8 -*-
"""payment.provider extension for Airwallex.

Holds the merchant credentials (Client ID / API Key / Webhook Secret) and
the thin REST client (``_airwallex_make_request``) that
:class:`payment.transaction` uses for every server-to-server call.
"""

import logging
import time

import requests
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_airwallex import const

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth tokens are short-lived (~30 min). We cache the latest one in memory
# per provider record so back-to-back requests reuse it instead of paying a
# round-trip to /authentication/login each time.
# ---------------------------------------------------------------------------
_TOKEN_TTL_SECONDS = 25 * 60  # refresh slightly before the 30 min expiry


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('airwallex', "Airwallex")],
        ondelete={'airwallex': 'set default'},
    )
    airwallex_client_id = fields.Char(
        string="Airwallex Client ID",
        help="Found at Airwallex Web App -> Developer -> API keys.",
        required_if_provider='airwallex',
        groups='base.group_system',
    )
    airwallex_api_key = fields.Char(
        string="Airwallex API Key",
        required_if_provider='airwallex',
        groups='base.group_system',
    )
    airwallex_webhook_secret = fields.Char(
        string="Airwallex Webhook Secret",
        help="Used to verify the HMAC signature on incoming webhooks. "
             "Find it under Airwallex Web App -> Developer -> Webhooks.",
        groups='base.group_system',
    )

    # ------------------------------------------------------------------
    # Cached login token. Stored in-memory only -- never persisted to DB so
    # rotating an API key takes effect immediately (no stale token bug).
    # ------------------------------------------------------------------
    _airwallex_token_cache = {}  # {provider_id: (token, expires_ts)}

    # ------------------------------------------------------------------
    # Provider-specific feature flags. Required by the payment framework so
    # Odoo knows which generic actions are available for this provider.
    # ------------------------------------------------------------------
    def _get_supported_currencies(self):
        """Restrict to the currencies Airwallex can charge in (see ``const``)."""
        supported = super()._get_supported_currencies()
        if self.code == 'airwallex':
            supported = supported.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported

    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'airwallex':
            return default_codes
        # Card is the universal default. Country-specific methods (POLi,
        # WeChat, Alipay, etc.) are still resolved by Airwallex on the HPP
        # based on the merchant's enabled methods + customer locale.
        return ['card']

    # ------------------------------------------------------------------
    # REST client.
    # ------------------------------------------------------------------
    def _airwallex_get_api_url(self):
        """Pick the demo or live host based on the provider state."""
        self.ensure_one()
        return const.API_URLS.get(self.state, const.API_URLS['test'])

    def _airwallex_get_access_token(self, force_refresh=False):
        """Return a valid bearer token, fetching a fresh one when needed.

        Airwallex login responds with ``{"token": "...", "expires_at": "..."}``
        but the expiry is in ISO 8601 with timezone -- we stay on the safe
        side by simply refreshing every ``_TOKEN_TTL_SECONDS`` rather than
        parsing the timestamp.
        """
        self.ensure_one()
        cache = type(self)._airwallex_token_cache
        if not force_refresh:
            cached = cache.get(self.id)
            if cached and cached[1] > time.time():
                return cached[0]

        url = url_join(self._airwallex_get_api_url(), const.ENDPOINT_LOGIN)
        headers = {
            'x-client-id': self.airwallex_client_id or '',
            'x-api-key': self.airwallex_api_key or '',
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            _logger.exception("Airwallex authentication failed: %s", err)
            raise ValidationError(_(
                "Airwallex: could not authenticate. Check the Client ID / API "
                "Key configured on the Airwallex provider."
            )) from err

        token = response.json().get('token')
        if not token:
            raise ValidationError(_(
                "Airwallex: authentication succeeded but no token was "
                "returned. Response was: %s", response.text
            ))
        cache[self.id] = (token, time.time() + _TOKEN_TTL_SECONDS)
        return token

    def _airwallex_make_request(
        self, endpoint, payload=None, method='POST', idempotency_key=None,
    ):
        """Thin wrapper around ``requests``.

        :param endpoint: relative path; can include ``{placeholders}`` already
            resolved by the caller (e.g. via ``.format(intent_id=...)``).
        :param payload: dict serialised as JSON for non-GET requests.
        :param method: HTTP verb.
        :param idempotency_key: forwarded as ``x-request-id``. Use the
            transaction reference for ``Create PaymentIntent`` so retries do
            not double-charge the customer.
        :raises ValidationError: on transport errors or non-2xx responses.
        :return: parsed JSON body as ``dict``.
        """
        self.ensure_one()
        url = url_join(self._airwallex_get_api_url(), endpoint)

        # First attempt with cached token; on 401 we refresh once and retry.
        for attempt in (1, 2):
            token = self._airwallex_get_access_token(force_refresh=(attempt == 2))
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            if idempotency_key:
                headers['x-request-id'] = idempotency_key
            try:
                response = requests.request(
                    method, url,
                    json=payload if method != 'GET' else None,
                    params=payload if method == 'GET' else None,
                    headers=headers,
                    timeout=30,
                )
            except requests.exceptions.RequestException as err:
                _logger.exception("Airwallex %s %s failed: %s", method, endpoint, err)
                raise ValidationError(_(
                    "Airwallex is currently unreachable. Please try again."
                )) from err

            if response.status_code == 401 and attempt == 1:
                _logger.warning(
                    "Airwallex 401 on %s -- refreshing access token and retrying.",
                    endpoint,
                )
                continue
            break

        if not response.ok:
            try:
                err_body = response.json()
            except ValueError:
                err_body = {'raw': response.text}
            _logger.error(
                "Airwallex API error: %s %s -> %s | body=%s",
                method, endpoint, response.status_code, err_body,
            )
            raise ValidationError(_(
                "Airwallex rejected the request: %s",
                err_body.get('message') or err_body,
            ))

        try:
            return response.json()
        except ValueError as err:
            _logger.exception("Airwallex returned non-JSON body: %s", response.text)
            raise ValidationError(_(
                "Airwallex returned an unexpected response."
            )) from err

    # ------------------------------------------------------------------
    # Hooks called by the generic payment.provider machinery.
    # ------------------------------------------------------------------
    def _airwallex_compute_signature(self, timestamp, raw_body):
        """HMAC-SHA256 of ``timestamp + raw_body`` keyed by webhook secret.

        Implementation per https://www.airwallex.com/docs/developer-tools/webhooks#verify-events.
        Kept on the provider so the controller does not need to import the
        secret directly (groups='base.group_system' guards it).
        """
        import hashlib
        import hmac

        self.ensure_one()
        if not self.airwallex_webhook_secret:
            raise UserError(_(
                "Airwallex webhook secret is not configured on provider %s.",
                self.display_name,
            ))
        message = f"{timestamp}{raw_body}".encode('utf-8')
        key = self.airwallex_webhook_secret.encode('utf-8')
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @api.model
    def _get_compatible_providers(self, *args, **kwargs):
        """Hide the Airwallex provider when credentials are missing.

        Otherwise customers see a payment option that immediately errors out
        on click, which is worse than not showing it at all.
        """
        providers = super()._get_compatible_providers(*args, **kwargs)
        return providers.filtered(
            lambda p: p.code != 'airwallex' or (
                p.airwallex_client_id and p.airwallex_api_key
            )
        )
