# KorbKlar App

Flutter client for a self-hosted [KorbKlar](../README.md) server, styled after
the web interface.

The app is a view, not a second implementation. Retailer adapters,
normalisation, unit prices, comparison groups and loyalty logic all stay on the
server, exactly as they do for the browser. The app never computes or formats a
price; it renders the values the comparison engine returns.

## What it does

- postal-code search with live progress, the same job endpoint the web page uses
- result list with product and brand filter, retailer chips, sorting, and the
  cheapest-only / include-duplicates views
- unit prices, package sizes, validity and source links
- loyalty program selection, with the server's benefit note
- product images through the server's signed image proxy
- warnings for failed or incomplete sources
- endless scrolling
- putting offers on a Bring shopping list, one at a time or as a selection

Server address, postal code, loyalty selection and target list are remembered
on the device.

## Bring

Two routes, offered side by side when both are available:

**Share sheet.** The app hands the offer text to the platform share sheet;
Bring registers as a receiver and adds the item. Works without a server and
without a token, but carries only text. Android and iOS only.

**KorbKlar server.** Uses the server's Home Assistant integration, which writes
a proper article plus a note holding retailer, price, package size and
validity. Requires that integration to be configured and the server to be
reachable from the phone. The app never sees the Home Assistant token.

Bring has no documented public write API for third-party apps, so the app does
not pretend to talk to Bring directly.

## Running it

```bash
flutter pub get
flutter run
```

On first start the app asks for the server address, for example
`http://192.0.2.10:8000`, and verifies it against `/health` before saving it.

A release build for Android:

```bash
flutter build apk --release
```

### Cleartext HTTP

Most self-hosted instances run plain HTTP on a LAN, a VPN or a home server, so
`android/app/src/main/res/xml/network_security_config.xml` permits cleartext.
Certificate validation for HTTPS addresses stays fully enabled; nothing trusts
user-added or invalid certificates. If your instance is reachable over HTTPS,
drop that file and the `networkSecurityConfig` attribute from the manifest.

## Tests

```bash
flutter analyze
flutter test
```

Two opt-in suites exist beyond the default run.

Against a real server:

```bash
flutter test --tags live --dart-define=KORBKLAR_URL=http://127.0.0.1:8000 --dart-define=KORBKLAR_PLZ=26188
```

Golden images of the result list in both themes, useful for reviewing layout
and palette without a device:

```bash
flutter test --tags golden --update-goldens
```

The goldens load Roboto and the Material icon font from the Flutter SDK, so
`FLUTTER_ROOT` must be set for the rendered text and icons to be legible.

## Layout

```text
lib/
├── api/
│   ├── client.dart      server calls, signed result handles, image URLs
│   └── models.dart      typed views over the REST responses
├── screens/
│   ├── home_screen.dart      server setup, postal code, search progress
│   └── results_screen.dart   filters, chips, loyalty, list, selection
├── services/
│   ├── bring.dart       share-sheet route and its text format
│   └── settings.dart    locally remembered preferences
├── widgets/
│   └── offer_card.dart  one offer row
├── theme.dart           colour tokens taken from the web stylesheets
└── main.dart
```

`theme.dart` mirrors the CSS custom properties in `home.css` and `results.css`,
including the dark palette, so both clients look like one product.
