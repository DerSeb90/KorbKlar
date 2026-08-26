# Shopping list via KitchenOwl

[Deutsch](kitchenowl.de.md)

KorbKlar writes offers to a list in [KitchenOwl](https://kitchenowl.org), a
self-hosted shopping list with shared households. The integration is optional:
leave `SUPERMARKT_KITCHENOWL_URL` or `SUPERMARKT_KITCHENOWL_TOKEN` empty and it
is off, with the interface hiding its controls. The rest of KorbKlar is
unaffected.

Running KitchenOwl itself alongside KorbKlar is covered in
[deployment](deployment.en.md).

## Connecting

Create the token in KitchenOwl under profile, sessions, long-lived tokens.
Then in `.env`:

```bash
SUPERMARKT_KITCHENOWL_URL=http://kitchenowl-web
SUPERMARKT_KITCHENOWL_TOKEN=your-long-lived-token
```

In the bundled stack KorbKlar talks to the web container over the compose
network rather than to the backend, which listens on a uwsgi socket and not on
HTTP. The requests never leave the server. If KitchenOwl runs elsewhere, put
the address of its web interface here.

`SUPERMARKT_KITCHENOWL_LIST_ID` only preselects a list. KorbKlar reads the
lists of every household the token can reach and offers them for selection.
Lists that do not exist are rejected before anything is written. The token
stays on the server and does not appear in `/health` either.

The configured instance is a first-party target chosen by the operator, often
on the same network. That is why the SSRF guard KorbKlar uses for untrusted
product images deliberately does **not** apply here: that guard blocks private
addresses, which is exactly what this target is.

## Using it

Every offer in the results has a **→ KitchenOwl** button. One click files it
in the list selected once in the bar above, and the button confirms with
`✓ in <list>`. There is no intermediate step. The app behaves the same way.

The **Einkauf** tab remains. That list is labelled "Eigene Liste" and stays in
the browser profile — it handles quantities, deposits and per-retailer totals,
which KitchenOwl has no concept of. Beside it sits a separate **KitchenOwl**
area with the target list and a "send copy" button. What is sent is a copy:
the local list is unchanged, checked-off items are skipped, and the response
names the count, the target list and what was skipped.

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
than articles. Otherwise the long names earlier versions filed would win every
time against your "Brötchen": they are the longest match for the very offer
that created them.

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
