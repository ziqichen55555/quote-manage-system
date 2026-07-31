# Re-Ware Square Reader companion apps

Phone/tablet apps that pair a **Square Reader** (Bluetooth) and complete
pending charges created from Odoo **Pay with Square** (Reader mode).

## Flow

1. Staff on any laptop opens a Sales Order in Odoo → **Pay with Square** → **Send to Reader**
2. This store device shows the pending checkout
3. Customer pays on the Square Reader
4. App calls Odoo `/square/reader/complete`
5. Odoo invoices + posts Square payment + stock

## Configure Odoo first

Settings → Sales → Square Card Payments:

- Hardware Mode = **Square Reader (phone/tablet app)**
- Environment, Application ID, Access Token, Location ID
- **Generate Reader App API Key** → Save
- Note **Reader App API Base URL** (usually `https://www.reware-project.com`)

## Apps

| Folder | Platform |
|--------|----------|
| `android/` | Kotlin + Square Mobile Payments SDK |
| `ios/` | Swift + Square Mobile Payments SDK |

Each app needs:

- Odoo base URL
- Reader App API Key (Bearer)
- Square Application ID (sandbox then production)

## Sandbox vs production Reader

- Sandbox: use Square **Mock Reader UI** in the SDK (physical Reader does not pair in sandbox).
- Production: pair the real Reader over Bluetooth on a supported phone/tablet.

## Docs

- [Mobile Payments SDK](https://developer.squareup.com/docs/mobile-payments-sdk)
- [Android](https://developer.squareup.com/docs/mobile-payments-sdk/android)
- [iOS](https://developer.squareup.com/docs/mobile-payments-sdk/ios)
