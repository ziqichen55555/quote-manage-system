# Sale: Square Card Payments (Terminal + Reader)

## Reader mode (your Square Reader hardware)

1. Settings → Sales → **Square Card Payments**
2. Hardware Mode = **Square Reader (phone/tablet app)**
3. Fill Application ID, Access Token, Location ID
4. **Generate Reader App API Key** → Save
5. Install companion app from `mobile/reware-square-reader/` on a store phone/tablet
6. Enter Odoo URL + API key in the app
7. Sales Order → **Pay with Square** → **Send to Reader**
8. On the phone: refresh pending → take payment on Reader → Odoo Check Status

### Mobile API

| Method | Path | Auth |
|--------|------|------|
| GET | `/square/reader/config` | Bearer API key |
| GET | `/square/reader/pending` | Bearer API key |
| POST | `/square/reader/complete` | Bearer API key |
| POST | `/square/reader/fail` | Bearer API key |

## Terminal mode

Legacy cloud Terminal API (requires Square Terminal with screen). Set Hardware Mode to Terminal and fill Device ID.

## Refunds

Credit note → **Refund via Square**
