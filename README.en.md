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

Combi and famila Nordwest belong to the Bünting group and only trade in north-western Germany. Both are therefore optional in the same sense as Marktkauf and GLOBUS: where they return nothing, that is not reported as a source error.

Their regional coverage in the Marktguru catalogue is uneven and is not the same for both brands. A postal code inside the sales area may return one brand, both, or neither, so the presence of a Bünting store near a postal code does not guarantee offers. KorbKlar shows what the regional catalogue actually contains and does not substitute data from another area.

famila Nordwest and famila Nordost are separate, unrelated retail groups. Only famila Nordwest is matched; famila Nordost is explicitly excluded so its offers can never appear under the Bünting brand.

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
- one row for an identical offer sold at several retailers for the same price
- product images through the local image proxy
- loyalty prices and specifically quantified euro benefits
- selection of multiple loyalty programs
- warnings for failed or incomplete sources
- automatic loading of additional results while scrolling
- adding offers to a Home Assistant shopping list such as Bring, individually or as a selection

When exactly one retailer is selected, the redundant retailer column is hidden.

## Identical offers at several retailers

Retail groups run one campaign across their brands, so famila Nordwest and Combi advertise the same product at the same price in the same week, and unrelated retailers sometimes carry the same manufacturer promotion. Those rows say the same thing.

When offers are already proven comparable and their price matches to within half a cent, they are shown as a single row listing every retailer that sells it. Nothing about the price changes, retailer filters still find the row under each of its retailers, and the retailer chips still count it for each of them.

Offers that were never matched to one another are left alone, even when their prices happen to be equal. A postal code returning `Orangen` for `2,49 €` as a 1500 g pack at one retailer and a 300 g pack at another describes two different deals, and merging them would hide that.

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

## Running it publicly: API key and VPN

Without `SUPERMARKT_API_KEY` nothing is restricted, and a private instance behaves as before.

With the key set, **every** route except `/health` requires either that bearer token or a source address inside `SUPERMARKT_TRUSTED_NETWORKS`:

```bash
SUPERMARKT_API_KEY=a-long-random-key
SUPERMARKT_TRUSTED_NETWORKS=10.8.0.0/24
SUPERMARKT_TRUSTED_PROXIES=127.0.0.1/32
```

One instance then covers both halves: the browser interface stays usable without a login for anyone on the VPN, scripts and the mobile client authenticate with the key from anywhere, and everyone else receives 401. The check runs as middleware in front of all routes, so a newly added route cannot be left open by accident.

`/health` stays reachable for container health checks but reveals only `status` and `service` to an unauthorised caller. Cache paths, source wiring and shopping-list details appear only for an authorised one.

### Behind a reverse proxy

`X-Forwarded-For` is believed only when the immediate peer is listed in `SUPERMARKT_TRUSTED_PROXIES`. The chain is read from the right with known proxies skipped, so a client cannot grant itself an allowed address by prepending an entry. With no proxies configured the header is ignored entirely.

**uvicorn must run with `--no-proxy-headers`.** By default uvicorn parses `X-Forwarded-For` itself and replaces the client address before KorbKlar sees it, which lets anyone able to set that header bypass `SUPERMARKT_TRUSTED_NETWORKS`. The bundled Docker image already starts correctly; keep the flag when starting uvicorn yourself.

The reverse proxy should additionally drop or overwrite any `X-Forwarded-For` supplied by the client.

## HTTPS and deployment

The Compose stack ships an optional reverse proxy. Caddy obtains and renews Let's Encrypt certificates on its own, with no certbot container and no cron job.

```bash
KORBKLAR_DOMAIN=korbklar.example.com
KORBKLAR_ACME_EMAIL=you@example.com
docker compose --profile proxy up -d
```

Without `--profile proxy` the stack starts exactly as before and the proxy container is never created.

Before the first start an A or AAAA record must point at the server and ports 80 and 443 must be reachable, because Let's Encrypt validates over them.

### Splitting VPN from internet

The network allowlist checks the source address **as the server sees it**. Anyone reaching the public domain over the internet appears with their provider's address, not their VPN one, so these are two separate paths:

| Path | Address | Authorisation |
| --- | --- | --- |
| Browser over VPN | `http://VPN-IP:8000` | source address in `SUPERMARKT_TRUSTED_NETWORKS`, no login |
| App and scripts | `https://korbklar.example.com` | bearer token |

`KORBKLAR_BIND_ADDRESS` selects the interface the published port binds to. Behind the proxy that is the VPN address, so the browser interface is not additionally exposed:

```bash
KORBKLAR_BIND_ADDRESS=10.8.0.1
```

`SUPERMARKT_TRUSTED_PROXIES` must contain the Compose network Caddy runs in, otherwise its `X-Forwarded-For` is ignored. Both default to `172.28.0.0/24`.

Caddy **overwrites** a client-supplied `X-Forwarded-For` with the actual peer rather than appending to it, so the allowlist never sees an address the client chose.

### Publishing your own image

The workflow builds on every push to `main` and publishes to GHCR under the repository owner's namespace, which in a fork is that fork's own. The server then only needs:

```bash
docker compose pull && docker compose up -d --no-build
```

Point `KORBKLAR_IMAGE` at it:

```bash
KORBKLAR_IMAGE=ghcr.io/your-name/korbklar:latest
```

A freshly forked repository has GitHub Actions disabled; enable them once under the Actions tab. The resulting package starts out private: either make it public under Packages, or run `docker login ghcr.io` on the server with a token that grants `read:packages`.

## Controlling the cache

KorbKlar keeps several caches with different lifetimes:

| What | Key | Fresh for | Afterwards |
| --- | --- | --- | --- |
| Offer snapshot | postal code and ALDI region | `SUPERMARKT_CACHE_TTL_MINUTES`, 30 minutes by default | reloaded |
| Result link | `search_id` | — | stays openable for `SUPERMARKT_RESULT_RETENTION_HOURS`, even when stale |
| REWE and Kaufland store mapping | postal code | 24 hours | re-resolved |
| Image cache | image URL | 7 days, 512 MiB | discarded |

Within the freshness window every search for the same postal code returns the same snapshot. A reload can be forced three ways:

- the **Neu laden** button on the results page and in the app
- `"refresh": true` in the body of `POST /api/v1/compare`
- the command line tool, which also clears the other caches

```bash
docker exec korbklar python -m supermarkt.cache_cli status
docker exec korbklar python -m supermarkt.cache_cli purge --postal-code 26188
docker exec korbklar python -m supermarkt.cache_cli purge --all
```

`purge` drops snapshots, optionally the image cache (`--images`) and the store mappings (`--stores`); `--all` covers both. The signing key is never touched, so result links from other searches stay valid.

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
- `SUPERMARKT_TRUSTED_NETWORKS`
- `SUPERMARKT_TRUSTED_PROXIES`
- `SUPERMARKT_CHROMIUM_BINARY`
- `KORBKLAR_IMAGE`
- `KORBKLAR_BIND_ADDRESS`
- `KORBKLAR_SUBNET`
- `KORBKLAR_DOMAIN`
- `KORBKLAR_ACME_EMAIL`

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
├── authz.py             API key, trusted networks, proxy handling
├── cache_cli.py         cache status and purge command
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

The Kaufland adapter needs a Chromium-compatible browser. The Docker image ships one; a local checkout probes the usual names and install locations for Chromium, Chrome and Edge, and `SUPERMARKT_CHROMIUM_BINARY` sets the path explicitly. Without a browser only that one adapter fails and Marktguru stands in for it.

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

## What is new in 0.0.3

Categories map to 18 stable German top-level labels. HOL’AB! appears only for postcodes in its official store list; six structured offers are honestly marked as partial coverage. Deposits and quantity conditions remain separate. REWE uses card deeplinks where present, while Lidl without a reliable identifier uses an official product search. The lightbox, local background and automatic light/dark theme load no third-party assets.

The **Einkauf** area stores the personal shopping list exclusively in IndexedDB in the current browser profile. There are no accounts, server-side personal lists, trackers, or automatic device synchronisation. Offers and manual items can be added, edited, checked and grouped by retailer. Goods and deposits use separate integer-cent arithmetic. Missing prices result in an explicitly incomplete known total; saved offer prices are never silently refreshed and expiry and quantity conditions remain visible.

Portable options include readable text, clipboard, Web Share, TXT, and a versioned JSON backup with a local preview. Imports are limited to 256 KiB and never sent to the backend. The canonical model keeps quantity, unit, pack, local ID, offer ID, source ID, and optional barcode separate. A small adapter boundary allows future KitchenOwl/Grocy adapters, but 0.0.3 includes no connection or synchronisation.

ALDI resolution uses exact official postcode evidence or strong store tags. Border regions load North and South separately. The offer chain uses official pages, a schema- and region-bound last-known-good cache, then replaceable external catalogue data; one ALDI region is never substituted for the other.
