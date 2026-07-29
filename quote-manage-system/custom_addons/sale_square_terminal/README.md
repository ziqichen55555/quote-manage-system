# Sale: Square Terminal Payments
# ==============================

Pay **Sales Orders** with a paired Square Terminal / card-present device.
Odoo stays the source of truth; Square only takes the card payment.

## Install

1. Deploy / pull this module under `custom_addons`.
2. Apps → Update Apps List → install **Sale: Square Terminal Payments**
   (`sale_square_terminal`).

## Configure in the UI (API keys)

You do **not** put secrets in code. Enter them in Odoo Settings:

1. Log in as **Administrator** (Settings / Technical rights).
2. Open **Settings** (gear icon).
3. Open the **Sales** app settings (left: Sales, or Settings → Sales).
4. Scroll to the block **Square Terminal**.
5. Tick **Enable Square Terminal**.
6. Fill in:
   - **Environment** — Sandbox first, then Production
   - **Access Token** — from [Square Developer Dashboard](https://developer.squareup.com/apps)
   - **Location ID**
   - **Device ID** — paired Terminal `device_id` (not the 6-digit pair code)
   - **Square Payment Journal** — optional; defaults to first bank journal
   - **Webhook Signature Key** — optional
7. Click **Save**.
8. Click **Test connection** to verify the token (lists Square locations).

Webhook URL (shown on the same screen): `{web.base.url}/square/terminal/webhook`

## Staff flow

1. Sales Order → **Pay with Square**
2. **Send to Reader** → customer pays
3. **Check Status** → invoice + payment method **Square** + delivery when possible

## Refunds

1. Create & post a **Credit Note**
2. **Refund via Square**

## Notes

- No Square catalogue / inventory sync.
- Serial products may leave the picking open if lots are not set; payment still posts.
- Hardware must support Square **Terminal API**.
