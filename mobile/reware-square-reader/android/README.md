# Re-Ware Square Reader (Android)

Kotlin companion app for Odoo Reader-mode payments.

## Open in Android Studio

1. Open the `android/` folder
2. Set values in `app/src/main/res/values/config.xml` (or use the in-app Settings screen)
3. Sync Gradle and run on a physical device (Bluetooth required for production Reader)

## config.xml

```xml
<string name="odoo_base_url">https://www.reware-project.com</string>
<string name="odoo_api_key">YOUR_READER_APP_API_KEY</string>
<string name="square_application_id">YOUR_SQUARE_APPLICATION_ID</string>
```

The app also loads Access Token + Location ID from Odoo `GET /square/reader/config`.

## Build notes

- Min SDK 28+
- Add Square Maven repo (already in `settings.gradle.kts`)
- For sandbox testing enable Mock Reader UI dependency
- Production requires Square application signature registration

See parent `../README.md`.
