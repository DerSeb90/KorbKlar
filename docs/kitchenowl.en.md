# Shopping list via KitchenOwl

[Deutsch](kitchenowl.de.md)

KorbKlar can write offers to a list in [KitchenOwl](https://kitchenowl.org), a
self-hosted shopping list with shared households. The integration is optional
and off by default: leave `SUPERMARKT_KITCHENOWL_URL` or
`SUPERMARKT_KITCHENOWL_TOKEN` empty and nothing changes, the interface hides
its controls and the routes answer `configured: false`.

The browser-local **Einkauf** list stays exactly as it is. KitchenOwl is a
second destination next to it, not a replacement.

## Two ways to connect

| | Where the token lives | Who talks to KitchenOwl |
| --- | --- | --- |
| Android app, **Settings → Connections** | on the phone | the app, directly over HTTPS |
| This server-side integration | on the KorbKlar server | KorbKlar, on behalf of browser and app |

The app's own connection needs nothing from this page. The server-side
integration is what gives the **browser** a KitchenOwl button at all, since a
web page cannot hold the token, and it is what the app falls back to when no
KitchenOwl is configured on the phone. Both can coexist.

## Connecting

Create the token in KitchenOwl under profile, sessions, long-lived tokens.
Then in `.env`:

```bash
SUPERMARKT_KITCHENOWL_URL=https://kitchenowl.your-domain.example
SUPERMARKT_KITCHENOWL_TOKEN=your-long-lived-token
```

Running KitchenOwl itself next to KorbKlar is one compose file away:

```bash
openssl rand -base64 48        # becomes KITCHENOWL_JWT_SECRET
docker compose -f compose.yml -f compose.kitchenowl.yml up -d
```

KitchenOwl then answers on `http://127.0.0.1:8080` and KorbKlar reaches it
over the compose network as `http://kitchenowl-web`, which the overlay sets as
the default URL. Create the account and household on first visit, create the
token, put it in `.env` and run `docker compose up -d` once more. The
combinations with the HTTPS overlay are in [deployment](deployment.en.md).

The signing secret is required and checked before startup, because KitchenOwl
itself **does not reject a missing value**: it quietly falls back to a
published default, and an empty value yields an empty signing key, which would
make its tokens forgeable. Once set, leave it alone; a new one invalidates
every session and long-lived token.

`SUPERMARKT_KITCHENOWL_LIST_ID` only preselects a list. KorbKlar reads the
lists of every household the token can reach and offers them for selection.
Lists that do not exist are rejected before anything is written. The token
stays on the server and does not appear in `/health` either.

The configured instance is a first-party target chosen by the operator, often
on the same network. That is why the SSRF guard KorbKlar uses for untrusted
product images deliberately does **not** apply here: that guard blocks private
addresses, which is exactly what this target is. Only `http://` and `https://`
URLs are accepted.

## Using it

Once configured, the results page shows a bar with the target list above the
offers, and every offer gets a **→ KitchenOwl** button next to **Zur
Einkaufsliste**. One click files the offer in the selected list, and the
button confirms with `✓ in <list>`. There is no intermediate step. The app
behaves the same way.

The **Einkauf** tab keeps the browser-local list unchanged: quantities,
deposits and per-retailer totals, which KitchenOwl has no concept of, stay
there. Beside its toolbar sits a **→ KitchenOwl** box with the target list and
a button that sends a copy. A copy: the local list is unchanged, checked-off
items are skipped, and the response names the count, the target list and what
was skipped.

## Which article is created

When a fitting article already exists in the household, the offer lands there
instead of beside it as a near duplicate: "GUT&GÜNSTIG Weizenbrötchen /
Schrippen" becomes your existing "Brötchen". Matching is on whole words, and
German puts the head noun last — "Weizenbrötchen" matches "Brötchen", while
"Buttermilch" matches "Milch" and not "Butter". Switch it off with
`SUPERMARKT_KITCHENOWL_MATCH_ITEMS=0`.

When no article fits yet, the new one is named short as well: shouted private
labels, pack sizes and qualifiers such as "aus der Region" are dropped, so
"GUT&GÜNSTIG Weizenbrötchen / Schrippen" becomes "Weizenbrötchen" and next
week's differently worded offer lands on the same article.

Catalogue entries of more than three words count as leaflet headlines rather
than articles and are never matched against.

## Note and category

The note carries only what the offer actually has: quantity, price, pack size,
validity and the full advertised wording. The last one appears only when the
article is named differently, or it would be printed twice. Nothing is
estimated.

Quantity leads the note, because KitchenOwl has no separate amount field.

The retailer becomes the category so the list groups by store; missing
categories are created. KitchenOwl categories have a name and no image field,
so a store logo is not possible — `SUPERMARKT_KITCHENOWL_CATEGORY_PREFIX` puts
an emoji in front instead, `🛒` by default.

**Worth knowing:** the category belongs to the article, not to the list entry.
An article therefore moves along as soon as another store offers it cheaper.
To sort by aisle instead, set `SUPERMARKT_KITCHENOWL_RETAILER_CATEGORIES=0` and
the retailer stays in the note.

## REST API

The same three calls exist for automations, protected by `SUPERMARKT_API_KEY`
like `POST /api/v1/compare`:

```text
GET  /api/v1/shopping-list/targets
GET  /api/v1/shopping-list/entries?entity_id=4
POST /api/v1/shopping-list/items
```

```bash
curl -H "Authorization: Bearer $SUPERMARKT_API_KEY" -H "Content-Type: application/json" \
     -d '{"entity_id": "4", "items": [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €"}]}' \
     http://127.0.0.1:8000/api/v1/shopping-list/items
```

The browser and the app use the same handlers under
`/results/<search_id>/shopping-list/...`, guarded by the signed result token
that already protects result data and the image proxy.
