# Re-Ware Square Reader (iOS)

Swift companion app for Odoo Reader-mode payments.

## Open in Xcode (requires macOS)

1. Create a new iOS App project named `RewareSquareReader` (or open the sources below into a project)
2. Add Square Mobile Payments SDK via SPM / CocoaPods per Square docs
3. Set `Config.plist` values
4. Run on a **physical iPhone/iPad** (Bluetooth)

## Config.plist

| Key | Value |
|-----|--------|
| OdooBaseURL | `https://www.reware-project.com` |
| OdooApiKey | Reader App API Key from Odoo Settings |
| SquareApplicationId | Square Application ID |

## Flow

Same as Android: poll `/square/reader/pending` → take payment with Mobile Payments SDK → `POST /square/reader/complete`.

## Docs

https://developer.squareup.com/docs/mobile-payments-sdk/ios
