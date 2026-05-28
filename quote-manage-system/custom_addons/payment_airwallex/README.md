# payment_airwallex

Native Odoo 17 [`payment.provider`](https://www.odoo.com/documentation/17.0/developer/reference/standard_modules/payment/payment_provider.html) integration for **Airwallex** using their **Hosted Payment Page (HPP)** flow.

> Internal Co-Creative IT / Re-Ware module. Not published to the Odoo Apps Store.

---

## Why HPP (and not Drop-in / Embedded)

| Mode | PCI scope | Effort | When to use |
|---|---|---|---|
| **Hosted Payment Page** ✅ | SAQ-A (lowest) | 1 module, ~400 LOC | Default, current implementation |
| Drop-in Element | SAQ-A-EP | +front-end iframe lifecycle | Want the form on Odoo's checkout page |
| Embedded Card Element | SAQ-A-EP | +token vaulting | Building bespoke checkout |

HPP also unlocks the full Airwallex method library (cards, Apple Pay, Google Pay, WeChat Pay, Alipay, POLi, BECS DD…) with a single integration.

---

## Installation

The module is shipped in-tree. Mount path is already configured in `docker-compose.prod.yml` via `./quote-manage-system/custom_addons:/mnt/custom-addons`.

```bash
# Local dev
docker compose run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d cocreativeit-quote \
  -i payment_airwallex \
  --stop-after-init

# Production (server)
docker compose -f docker-compose.prod.yml --env-file .env run --rm web odoo \
  -c /etc/odoo/odoo.conf -d cocreativeit-quote \
  -i payment_airwallex --stop-after-init
docker compose -f docker-compose.prod.yml --env-file .env restart web
```

After install, an `Airwallex` row appears at **Settings → Payment Providers**.

---

## Configuration

1. **Airwallex Web App → Developer → API keys** — create a pair of keys
   (Client ID + API Key). For sandbox use the *Demo* tenant; for live use
   the *Production* tenant.
2. **Odoo → Settings → Payment Providers → Airwallex** — fill in:
   * `Client ID`
   * `API Key`
   * `Webhook Secret` (Settings → Webhooks → Reveal secret)
3. Set **State = Test** while you wire things up; flip to **Enabled** when
   you are ready to take real money.

### Webhook URL

Register exactly one URL on Airwallex (Demo or Prod, matching your state):

```
https://<SITE_HOSTNAME>/payment/airwallex/webhook
```

Subscribe to at minimum:

* `payment_intent.succeeded`
* `payment_intent.cancelled`
* `payment_intent.failed`
* `payment_intent.requires_payment_method`
* `refund.succeeded`
* `refund.failed`

---

## File map

```
payment_airwallex/
├── __init__.py
├── __manifest__.py
├── README.md                              # this file
├── const.py                               # endpoints, currencies, status maps
├── controllers/
│   ├── __init__.py
│   └── main.py                            # /payment/airwallex/return + /webhook
├── data/
│   └── payment_provider_data.xml          # seeds the `airwallex` provider row
├── models/
│   ├── __init__.py
│   ├── payment_provider.py                # API client + credential fields
│   └── payment_transaction.py             # state machine + REST calls
├── static/
│   └── src/
│       └── js/
│           └── payment_form.js            # SDK redirectToCheckout()
└── views/
    └── payment_provider_views.xml         # credentials form
```

---

## Flow diagram

```
Customer                Odoo                       Airwallex
   |                     |                              |
   |  /shop/payment      |                              |
   |-------------------> |                              |
   |                     |  POST /authentication/login  |
   |                     |----------------------------> |
   |                     | <----token-------------------|
   |                     |                              |
   |                     | POST /pa/payment_intents/    |
   |                     |     create                   |
   |                     |----------------------------> |
   |                     | <- intent_id, client_secret  |
   |                     |                              |
   | <-- form + JS ------|                              |
   |                                                    |
   | -- redirectToCheckout({intent_id, client_secret}) ->|
   |                                                    |
   |                       (customer pays on Airwallex)
   |                                                    |
   | <-- 302 successUrl --------------------------------|
   |                     |                              |
   |  /payment/airwallex/return                         |
   |-------------------> |                              |
   |                     |                              |
   |                     | <-- POST /webhook (HMAC) ----|
   |                     |                              |
   |                     | (verify sig, _process_       |
   |                     |  notification_data)          |
   |                     |                              |
   |                     | sale.order.action_confirm()  |
```

---

## Refund

Implemented via `payment.transaction._send_refund_request`. From a confirmed
sale order, click **Action → Refund** on the linked `payment.transaction` and
the module calls `POST /pa/refunds/create` then writes back the new tx as
`done` once Airwallex sends `refund.succeeded`.

---

## Operational notes

* **`web.base.url`** must be the public HTTPS URL (no trailing slash). The
  module builds `successUrl` / `cancelUrl` / webhook URL from it.
* **`web.base.url.freeze`** should be `True` in production -- otherwise the
  first request from a different host rewrites it and breaks return URLs.
* **Idempotency**: PaymentIntent `request_id` is set to the
  `payment.transaction.reference`, so retried `_send_payment_request` calls
  do not double-create intents.
* **HMAC verification** is mandatory. We reject any webhook missing or
  failing the `x-signature` header to prevent third parties from forging
  `payment_intent.succeeded` events.

---

## TODO before go-live

- [ ] Replace placeholder `static/description/icon.png` with the Airwallex
      logo (96×96 PNG).
- [ ] Configure live API keys + webhook secret in production.
- [ ] Run an end-to-end sandbox test with a real (test) AUD amount.
- [ ] Audit `__system_email_addresses__` of Airwallex notifications -> make
      sure they go to `intern@cocreativeit.com`.
