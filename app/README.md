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
- one row for an identical offer sold at several retailers for the same price
- loyalty program selection, with the server's benefit note
- product images through the server's signed image proxy
- warnings for failed or incomplete sources
- endless scrolling
- collecting offers across searches and sending them together; the collection
  survives a reload and a restart
- putting offers on a KitchenOwl shopping list, one at a time or as a whole collection
- a refresh action that bypasses the server's snapshot cache and re-queries
  every source

Server address, postal code, loyalty selection and target list are remembered
on the device.

## Shopping list

Every offer carries an **Auf KitchenOwl** button that files it straight into
the list named in the bar above the results, the same one-tap flow the browser
uses. The button then reads "in <list>" so a filed offer stays recognisable
while scrolling. The chosen list is remembered on the device.

The KitchenOwl token stays on the server; the app never sees it.

Where no list is configured the offer is copied to the clipboard instead, so
the button is never a dead end.

## Running it

```bash
flutter pub get
flutter run
```

On first start the app asks for the server address, for example
`http://192.0.2.10:8000`, plus an optional API key, and verifies both against
`/health` before saving them.

The key is only needed when the server is publicly reachable and has
`SUPERMARKT_API_KEY` set. `/health` answers without authorisation but withholds
its detail fields, which lets the app tell a wrong address from a wrong or
missing key without triggering a search. Once saved, the key is sent as a
bearer token on every request, so the app works from outside the VPN.

### Installing on Android

The `Build Android app` workflow produces an installable APK on every push
that touches `app/`, and can also be started by hand from the Actions tab.
Download the `korbklar-apk` artifact and install `app-arm64-v8a-release.apk`
on the phone; Android asks once to allow installation from that source.

Building locally works too, when the machine's Gradle toolchain is healthy:

```bash
flutter build apk --release
```

Both builds are signed with Flutter's debug key. That is fine for sideloading
a personal build, but a differently signed build cannot replace it without
uninstalling first. For a stable signing identity, create a keystore and a
`android/key.properties` referencing it; keep both out of the repository.

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

Add `--dart-define=KORBKLAR_KEY=...` for an instance that requires an API key.

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
│   ├── shopping_list.dart  list route and the text format
│   └── settings.dart    locally remembered preferences
├── widgets/
│   └── offer_card.dart  one offer row
├── theme.dart           colour tokens taken from the web stylesheets
└── main.dart
```

`theme.dart` mirrors the CSS custom properties in `home.css` and `results.css`,
including the dark palette, so both clients look like one product.
