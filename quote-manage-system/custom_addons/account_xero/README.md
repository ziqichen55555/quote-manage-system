# account_xero

Push **Re-Ware** customer invoices from Odoo 17 into the existing
**Co-Creative IT** Xero organisation (single ABN, no extra subscription).

## What syncs

| Odoo record | When | Xero object |
|-------------|------|-------------|
| `res.partner` | First invoice for customer | Contact |
| `account.move` (`out_invoice`, posted) | On post (or manual button) | Sales invoice (`ACCREC`, AUTHORISED) |

**Payments are not synced to Xero.** Odoo continues to record payment method and
payment status locally; Xero invoices remain unpaid/AUTHORISED so settlement can
be handled in Xero separately if needed.

Every invoice line is tagged with the configured **Tracking Category** (default
`Sales Channel` → `Re-Ware`) so sales can be filtered in Xero reports while
GST/BAS stays on one organisation.

## Install

```bash
# Local
docker compose run --rm web odoo \
  -c /etc/odoo/odoo.conf \
  -d cocreativeit-quote \
  -i account_xero \
  --stop-after-init

# Production
docker compose -f docker-compose.prod.yml --env-file .env run --rm web odoo \
  -c /etc/odoo/odoo.conf -d cocreativeit-quote \
  -i account_xero --stop-after-init
docker compose -f docker-compose.prod.yml --env-file .env restart web
```

## Xero app setup

1. [developer.xero.com](https://developer.xero.com/) → **New app** → **Web app**
2. **Redirect URI** (must match production Odoo URL):

   `https://www.reware-project.com/xero/oauth/callback`

3. Scopes: `openid profile email offline_access accounting.contacts accounting.invoices accounting.payments accounting.settings.read`
4. In Xero → **Settings → Advanced → Tracking categories**, create:
   - Category: `Sales Channel`
   - Option: `Re-Ware`

## Odoo configuration

**Settings → Invoicing → Xero Integration**

1. Enable **Sync Re-Ware sales to Xero**
2. Paste **Client ID** and **Client Secret**
3. Click **Connect to Xero** and authorise the Co-Creative IT organisation
4. Set account codes to match your Xero chart (defaults are placeholders):
   - **Revenue Account Code** — e.g. `200`
   - **Sales Tax Type** — usually `OUTPUT` for AU GST on sales
5. **Test connection**

Posted customer invoices sync automatically. Use **Push to Xero** on an invoice
or **Accounting → Configuration → Xero Sync Logs** to debug.

## Notes

- Sync failures do **not** block Odoo posting; errors are logged on the invoice and in sync logs.
- Invoice lines include product description and serial numbers (`S/N: …`) when stock lots are linked.
- Credit notes (`out_refund`) are not synced in v1.
- Payment method/status remain fully usable in Odoo; they are never pushed to Xero.
