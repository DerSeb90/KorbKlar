# KorbKlar

[← Language selection](README.md) · [Deutsch](README.de.md)

![KorbKlar](docs/readme-header.svg)

KorbKlar is a self-hosted service for comparing current regional supermarket offers in Germany. In normal use, the user only enters a German postal code. KorbKlar discovers matching retailers and stores, retrieves current weekly offers, normalizes product names and package sizes, keeps package size separate from unit-price reference quantities, and compares identical or meaningfully comparable products. Loyalty programs can be included optionally, and results are presented in an interactive web interface.

It does more than list leaflet prices: the comparison engine cleans inconsistent source data and presents price, actual package size, and unit price separately so differences between retailers and package formats remain understandable.

## How the project started

KorbKlar grew out of vibe coding for a specific personal use case. The original idea was to have a local LLM run the supermarket comparison automatically and provide or post the result through Conduit on Monday mornings, once the new weekly offers were available.

During development, it became clear that the comparison logic made more sense as a standalone service. In my view, that made KorbKlar faster, more flexible, easier to automate, and independent of any particular LLM model or frontend. Browsers, REST clients, scripts, Conduit, and LLMs can all use the same service.

An LLM is therefore optional and is not a runtime requirement. The original idea of an automatically generated Monday report using a local LLM and Conduit remains a possible use case.

## Quick start

You need Docker Engine, Docker Compose v2, Git, and internet access from the container.

```bash
git clone https://github.com/lesecuritae/KorbKlar.git
cd KorbKlar
docker compose pull
docker compose up -d --no-build
```

This uses the prebuilt `ghcr.io/lesecuritae/korbklar:latest` image published through GitHub Container Registry. The default setup does not require a `.env` file.

### Local source build

This separate development path builds the image from the checked-out Dockerfile:

```bash
docker compose build
docker compose up -d --no-build
```

The default port is `8000`. Open:

```text
http://SERVER-IP:8000
```

Normal browser use requires no account, no LLM, no API key, and no mandatory `.env` file.

## Running with Docker

The Compose project, service, and container are all named `korbklar`; persistent data is stored in the `korbklar-data` volume.

```bash
docker compose logs -f korbklar
curl http://127.0.0.1:8000/health
docker compose down
```

`docker compose down` preserves the volume. If host port 8000 is occupied, select another host port with the still-current internal variable `SUPERMARKT_PORT`; the container continues to listen on port 8000:

```bash
SUPERMARKT_PORT=8080 docker compose up -d --no-build
```

The interface is then available at `http://SERVER-IP:8080`. The value may also be stored in an optional `.env` file.

## What happens during a search

```text
postal code
    ↓
discover regional retailers and stores
    ↓
+retrieve current offers
    ↓
normalize product, price, and quantity data
    ↓
determine unit prices and comparable offers
    ↓
assign loyalty prices and quantified benefits
    ↓
store a snapshot in SQLite
    ↓
display the results
```

The browser interface and REST API use the same comparison engine. Retailer adapters, normalization, loyalty logic, and price comparison are not reimplemented in the frontend.

## Supported retailers and data paths

KorbKlar currently supports REWE, EDEKA, Marktkauf, ALDI Nord, ALDI Süd, Kaufland, Lidl, PENNY, Netto Marken-Discount, GLOBUS, Combi, and famila Nordwest.

REWE, EDEKA, Marktkauf, and Kaufland are loaded preferentially from direct retailer sources. For ALDI, the postal code determines the region and only ALDI Nord or ALDI Süd is retrieved directly. If the region cannot be determined unambiguously, ALDI is omitted and a warning is shown.

Lidl, PENNY, Netto Marken-Discount, GLOBUS, Combi, and famila Nordwest are loaded from regional Marktguru data. KorbKlar combines a broad regional search with supplementary retailer-name searches; the name queries alone are never treated as a complete catalogue.

Combi and famila Nordwest belong to the Bünting group and only trade in north-western Germany. Both are therefore optional: outside their sales area they simply return no offers, which is not reported as a source error. famila Nordost is a different, unrelated retail group and is never matched as famila Nordwest.

If a direct adapter fails or returns no offers for the target week, Marktguru may act as a fallback for that retailer only. A successful direct catalogue is never mixed with a second complete Marktguru catalogue. Actual availability depends on postal code, region, and reachable sources; retailers without results are not shown as empty filters.

```bash
docker exec korbklar python -m supermarkt.diagnostics 12345
```

The command above runs the current source diagnostic for a postal code inside the container.

## Results interface

The interface includes:

- retailer filtering
- combined product and brand search
- sorting by price, unit price, retailer, or product
- regular price and unit-price comparisons
- a view containing only the cheapest safe comparison matches
- an all-results view including more expensive duplicates
- product images through the local image proxy
- loyalty prices and specifically quantified euro benefits
- selection of multiple loyalty programs
- warnings for failed or incomplete sources
- automatic loading of additional results while scrolling
- adding offers to a Home Assistant shopping list such as Bring, individually or as a selection

When exactly one retailer is selected, the redundant retailer column is hidden.

## Package sizes and data cleaning

Package size and the reference quantity used for a unit price are handled separately. A can containing `330 ml` with a unit price per `1 litre` remains a `330 ml` package. The litre reference appears only with the unit price and is not combined into an incorrect quantity.

Alternative sizes are not added together. Source text such as `85 g or 100 g` describes two possible packages and must not become `85 g + 100 g` or `185 g`. A `+` appears only when the source actually describes a combined pack.

Product names, brands, prices, and quantities are cleaned before comparison groups are built. Placeholders such as `This is no brand` are treated as missing brand data and are not displayed.

## Loyalty programs

The current code recognizes:

- REWE Bonus
- Lidl Plus
- PENNY App
- Netto plus App
- Kaufland Card XTRA
- EDEKA App
- MARKTKAUF App
- mein GLOBUS
- PAYBACK at supported retailers

Multiple programs may be selected together. KorbKlar only applies product prices or euro-denominated benefits explicitly present in the offer data. Direct loyalty prices may reduce the checkout price, while a specifically stated euro credit is applied as a benefit.

Points, personal coupons, status benefits, percentage promotions without a concrete resulting price, and unknown discounts are never estimated or converted into invented euro amounts.

## No mandatory LLM

KorbKlar is a standalone service:

```text
Browser / script / REST client / LLM
                  ↓
               KorbKlar
                  ↓
            retailer sources
```

A local LLM can still use KorbKlar, for example for an automatic Monday report through Conduit, natural-language queries, or summaries. The price comparison itself requires no LLM and remains independent of any model, agent, or frontend.

## REST API

External clients and automations use:

```text
POST /api/v1/compare
```

Minimal request:

```json
{
  "postal_code": "01067"
}
```

Optional fields include loyalty programs, product or brand filters, retailer, pagination, view, sorting, ALDI region, and forced refresh:

```json
{
  "postal_code": "01067",
  "loyalty_programs": ["rewe_bonus", "lidl_plus", "kaufland_xtra", "payback"],
  "view": "best_only",
  "sort": "unit_price"
}
```

Two further endpoints exist once the shopping-list integration is configured:

```text
GET  /api/v1/shopping-list/targets
POST /api/v1/shopping-list/items
```

Browser access remains unauthenticated. If `SUPERMARKT_API_KEY` is set, a bearer token protects `POST /api/v1/compare` and both shopping-list endpoints. See [`.env.example`](.env.example) for current settings.

## Shopping list through Home Assistant

KorbKlar can write offers to a Home Assistant todo list. Because the Bring integration exposes every Bring list as a `todo` entity, KorbKlar calls the generic `todo.add_item` service instead of a Bring-specific interface. The same path therefore also covers the built-in shopping list and other todo providers.

Configure the connection with a long-lived access token from the Home Assistant user profile:

```bash
SUPERMARKT_HA_URL=http://homeassistant.local:8123
SUPERMARKT_HA_TOKEN=your-long-lived-access-token
SUPERMARKT_HA_TODO_ENTITY=todo.bring_einkaufsliste
```

The Home Assistant instance may be reachable only over LAN or VPN. Only the KorbKlar server talks to it, the token never reaches the browser, and it is not exposed through `/health`. This client deliberately does not use the SSRF guard applied to untrusted product images, because the target here is a first-party host chosen by the operator.

`SUPERMARKT_HA_TODO_ENTITY` only preselects a list. KorbKlar reads the available `todo` entities from Home Assistant and offers them in the results interface, so several Bring lists can be used from the same instance. Entities from other domains are rejected before anything is written.

Each offer becomes one list entry: the product name is the article, and the note holds retailer, price, package size, and validity, for example `famila Nordwest · 1,59 € · 250 g · bis 29.08.`. Only values the offer actually carries are written; nothing is estimated.

In the results interface each offer has a `+ Liste` button, and a checkbox collects several offers for one combined transfer. The browser path is protected by the same HMAC result token that already guards result data and the image proxy, so the feature is reachable only with a valid results link.

If `SUPERMARKT_HA_URL` or `SUPERMARKT_HA_TOKEN` is empty, the integration stays switched off and the interface hides the shopping-list controls.

## Cache and data

No external database server is required. SQLite stores offer snapshots so filtering, sorting, and incremental result loading do not repeatedly query retailer sources.

The persistent data path holds offer snapshots, an automatically generated signing key, the local image cache, and cached REWE and Kaufland store mappings. Snapshots are fresh for 30 minutes by default (`SUPERMARKT_CACHE_TTL_MINUTES=30`), up to 100 are retained (`SUPERMARKT_CACHE_MAX_SNAPSHOTS=100`), and result links remain available for 168 hours or seven days (`SUPERMARKT_RESULT_RETENTION_HOURS=168`). REWE and Kaufland store mappings are cached for 86,400 seconds or one day; this does not replace fresh offer retrieval.

The image cache defaults to 604,800 seconds or seven days, 512 MiB total, and 4 MiB per file. These values are configurable.

## Image proxy and security

Product images are delivered through a local cache. The image service accepts only HTTP and HTTPS targets, resolves target hosts, and blocks private, loopback, link-local, multicast, reserved, and unspecified addresses. Redirect targets are validated again, providing SSRF protection.

Common tracking pixels, logos, placeholders, loyalty badges, and unsupported image types are rejected. Downloads have timeout, file-size, and cache-size limits. Result and image links are HMAC-signed. KorbKlar generates and persistently stores a random signing key on first start unless an explicit key is configured.

## Configuration

The default setup needs no `.env`. [`.env.example`](.env.example) documents every current variable:

- `SUPERMARKT_PORT`
- `SUPERMARKT_API_KEY`
- `SUPERMARKT_DATA_DIR`
- `SUPERMARKT_CACHE_DB`
- `SUPERMARKT_SIGNING_SECRET_FILE`
- `SUPERMARKT_SIGNING_SECRET`
- `SUPERMARKT_IMAGE_CACHE_DIR`
- `SUPERMARKT_KAUFLAND_CACHE_DIR`
- `SUPERMARKT_REWE_CACHE_DIR`
- `SUPERMARKT_CACHE_TTL_MINUTES`
- `SUPERMARKT_CACHE_MAX_SNAPSHOTS`
- `SUPERMARKT_RESULT_RETENTION_HOURS`
- `SUPERMARKT_TIMEOUT_SECONDS`
- `SUPERMARKT_MARKTGURU_PAGE_SIZE`
- `SUPERMARKT_MAX_WORKERS`
- `SUPERMARKT_USER_AGENT`
- `SUPERMARKT_KAUFLAND_STORE_CACHE_TTL_SECONDS`
- `SUPERMARKT_REWE_STORE_CACHE_TTL_SECONDS`
- `SUPERMARKT_IMAGE_CACHE_TTL_SECONDS`
- `SUPERMARKT_IMAGE_CACHE_MAX_BYTES`
- `SUPERMARKT_IMAGE_MAX_FILE_BYTES`
- `SUPERMARKT_HA_URL`
- `SUPERMARKT_HA_TOKEN`
- `SUPERMARKT_HA_TODO_ENTITY`
- `SUPERMARKT_HA_VERIFY_TLS`
- `SUPERMARKT_HA_TIMEOUT_SECONDS`
- `SUPERMARKT_HA_MAX_ITEMS`

The historical internal prefixes remain part of the current technical interface. `.env.example` is authoritative for meanings, defaults, and Docker paths.

## Running without Docker

KorbKlar requires Python 3.12 or newer:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
uvicorn supermarkt.asgi:app --host 0.0.0.0 --port 8000
```

The application is then available at `http://127.0.0.1:8000`. By default, runtime data is kept in the local user state directory.

## Development and tests

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -m 'not live'
```

On Windows use `.venv\Scripts\python.exe` instead of the activation script. The `dev` extra pulls in `tzdata` there, because Windows ships no IANA time-zone database and `Europe/Berlin` would otherwise fail at import time.

To debug against live sources, run the app directly and keep runtime data out of the user state directory:

```bash
SUPERMARKT_DATA_DIR=.devdata uvicorn supermarkt.asgi:app --host 127.0.0.1 --port 8000 --reload
```

The Kaufland adapter drives a headless Chromium, which the Docker image provides. Without a local Chromium that one adapter fails and Marktguru serves as its fallback; every other source works unchanged.

Live retailer tests are deliberately opt-in:

```bash
RUN_LIVE_TESTS=1 pytest -m live
```

The offline suite covers postal-code validation, browser and API routes, cache behavior, package-size and unit-price normalization, comparison groups, loyalty combinations, retailer filters, the image proxy, SSRF protection, and release cleanliness. Live tests exercise changing external retailer paths and require internet access.

## Architecture

```text
src/supermarkt/
├── sources/             retailer adapters and Marktguru client
├── models.py            data models and retailer definitions
├── common.py            normalization and shared helpers
├── region.py            regional ALDI mapping
├── compare.py           mapping, deduplication, and price comparison
├── loyalty.py           loyalty programs and quantified benefits
├── cache.py             SQLite snapshot cache
├── service.py           source orchestration and comparison service
├── presentation.py      response fields
├── images.py            downloads, image cache, and SSRF protection
├── security.py          signatures and optional API key
├── homeassistant.py     Home Assistant todo lists, for example Bring
├── shopping_routes.py   shopping list routes
├── access.py            access and request helpers
├── api_routes.py        REST routes
├── browser_routes.py    browser routes
├── media_routes.py      image and media routes
├── health_routes.py     health check
├── runtime.py           shared runtime objects
└── static/              interface HTML, CSS, and JavaScript
```

The internal Python package name `supermarkt` remains for technical reasons. Adapters in `sources/` understand their sources, `service.py` orchestrates direct sources and fallbacks, and `compare.py` builds comparisons. The browser and REST API share the same runtime; the frontend does not calculate prices independently.

## Limitations

Retailer websites and undocumented interfaces may change at any time. An individual adapter may fail temporarily without making KorbKlar unusable as a whole. Where suitable regional fallback data exists, it can replace only the affected retailer; other reachable sources remain usable.

KorbKlar does not invent missing prices or estimate unknown loyalty benefits. Completeness and freshness depend on reachable regional source data.

## Roadmap

The Home Assistant shopping list described above is implemented. Potential future integrations include Grocy, KitchenOwl, and further REST or OpenAPI connections for local automations, agents, and Conduit or LLM workflows such as the originally planned automatic Monday report.

Those remaining integrations are not part of version 0.1.0. The existing REST API can already support custom automations.

## Support the project

To support KorbKlar and the work of Tarnkappe.info, see the current donation options at:

https://tarnkappe.info/spenden/

The Tarnkappe.info Monero address documented in the current repository is:

```text
87oownPVNFFciRNe2DLaNQPrVsjprbZBX7bHnPENABDyGpM6isrzKeWGsjT5W86h9d6A5nhE2Z2ZAXCHksvC2EikGGaWB8u
```

Wallet addresses can change. Before donating, verify the currently published address at [tarnkappe.info/spenden](https://tarnkappe.info/spenden/).

## License and trademarks

The source code is available under the [BSD 3-Clause License](LICENSE).

Copyright © 2026 lesecuritae for Tarnkappe.info.

KorbKlar is independent and is not affiliated with any retailer or loyalty program mentioned. Brand, retailer, and product names belong to their respective owners.
