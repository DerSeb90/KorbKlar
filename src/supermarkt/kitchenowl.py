"""Push offers to a KitchenOwl shopping list.

KitchenOwl is a self-hosted grocery list with collaborative households, which
makes it a natural target for a comparison this service already performed. Its
REST API needs only three calls:

* ``GET /api/household`` for the households the token can see
* ``GET /api/household/<id>/shoppinglist`` for that household's lists
* ``POST /api/shoppinglist/<id>/add-item-by-name`` with ``name`` and an
  optional ``description``

Authentication is a long-lived token, created in KitchenOwl under profile,
sessions, long-lived tokens, and sent as a bearer token.

The configured instance is a first-party target chosen by the operator, often
on the same host or a private network. That is why this client does not use
the SSRF guard from :mod:`.images`, which exists to protect against untrusted
image hosts. The token never leaves the server.
"""

from __future__ import annotations

import json
import re
import ssl
import threading
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .common import clean_text
from .config import (
    KITCHENOWL_CATEGORY_PREFIX,
    KITCHENOWL_LIST_ID,
    KITCHENOWL_MATCH_EXISTING_ITEMS,
    KITCHENOWL_MAX_ITEMS_PER_REQUEST,
    KITCHENOWL_TIMEOUT_SECONDS,
    KITCHENOWL_RETAILER_CATEGORIES,
    KITCHENOWL_TOKEN,
    KITCHENOWL_URL,
    KITCHENOWL_VERIFY_TLS,
    USER_AGENT,
)

LIST_CACHE_TTL_SECONDS = 300
CATALOGUE_CACHE_TTL_SECONDS = 300
# Below this an existing article says too little to be worth matching: "Ei"
# would swallow half a catalogue.
MIN_MATCH_LENGTH = 4
# A household staple is named in a word or three. Anything longer in the
# catalogue is an offer headline, most likely one an earlier version of this
# service filed there, and matching against it would keep every later offer
# for the same product away from the real article.
MAX_ARTICLE_WORDS = 3
_TRAILING_WORDS = frozenset(
    {"aus", "mit", "ohne", "in", "im", "von", "vom", "der", "die", "das",
     "und", "oder", "je", "pro", "à", "a", "zum", "zur", "nach", "verschiedene",
     "versch", "sowie", "auch", "z", "b"}
)
_UNIT = "g|kg|mg|ml|cl|l|stk|stück|st|x|er"
_PACK_WORD = re.compile(rf"([0-9]+([.,][0-9]+)?\s*({_UNIT})?|{_UNIT}|packung|beutel|dose|schale)[.,]?", re.IGNORECASE)
MAX_ITEM_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 300


class ShoppingListError(RuntimeError):
    """A configuration or transport problem while talking to KitchenOwl."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _truncate(value: str, limit: int) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _is_brand_token(token: str) -> bool:
    """Whether a word reads as a brand or marketing line rather than a product.

    Leaflets shout their private labels: "GUT&GÜNSTIG", "JA!", "REWE BESTE
    WAHL". Three letters keep "H-Milch" and unit letters out of this.
    """
    letters = [char for char in token if char.isalpha()]
    return len(letters) >= 3 and token == token.upper() and token != token.lower()


def shorten_offer_name(product: str) -> str:
    """Return the staple an offer is about, without the leaflet wording.

    "GUT&GÜNSTIG Weizenbrötchen / Schrippen" is a household's "Weizenbrötchen".
    The full offer wording is not lost: it goes into the note. Keeping the
    article short is what lets the next week's differently worded offer for the
    same thing land on the same article instead of beside it.
    """
    text = clean_text(product)
    if not text:
        return ""
    # An alternative spelling after a slash describes the same product.
    head = text.split("/", 1)[0].strip()
    if len(head) >= MIN_MATCH_LENGTH:
        text = head
    words = [word for word in text.split() if word]
    # "Rinderhackfleisch aus der Region" is bought as Rinderhackfleisch; what
    # follows such a word qualifies the offer, not the product.
    for index, word in enumerate(words):
        if index and word.casefold().strip(",.") in _TRAILING_WORDS:
            words = words[:index]
            break
    kept = [word for word in words if not _is_brand_token(word)]
    if not kept:
        kept = words
    # A pack size belongs in the note, not in the article name.
    while len(kept) > 1 and _PACK_WORD.fullmatch(kept[-1]):
        kept.pop()
    # German puts the head noun last, so when trimming, the tail is the part
    # that says what the product is.
    return " ".join(kept[-MAX_ARTICLE_WORDS:])


def build_item_text(product: str, retailer: str) -> str:
    """Return the shopping list article name."""
    name = _truncate(shorten_offer_name(product), MAX_ITEM_LENGTH)
    if name:
        return name
    fallback = clean_text(retailer)
    return _truncate(f"Angebot {fallback}" if fallback else "Angebot", MAX_ITEM_LENGTH)


def build_item_description(
    retailer: str,
    price_text: str,
    validity: str,
    pack: str,
    quantity: int = 1,
    product: str = "",
) -> str:
    """Return the note shown underneath the article.

    Only values the offer actually carries are included. Nothing is estimated,
    matching how this service treats loyalty benefits. A quantity leads,
    because KitchenOwl has no separate amount field and shows this note next
    to the article.
    """
    parts = [
        f"{quantity}×" if quantity > 1 else "",
        # Only when the article was matched to a shorter household name, so
        # the offer it came from stays readable.
        clean_text(product),
        clean_text(retailer),
        clean_text(price_text),
        clean_text(pack),
        clean_text(validity),
    ]
    return _truncate(" · ".join(part for part in parts if part), MAX_DESCRIPTION_LENGTH)


def _fold(value: str) -> str:
    """Reduce a name to comparable words."""
    return re.sub(r"[^0-9a-zäöüß]+", " ", clean_text(value).casefold()).strip()


def match_existing_item(product: str, catalogue: Iterable[str]) -> str:
    """Return the household's own article name for this offer, if any.

    An offer is called "GUT&GÜNSTIG Weizenbrötchen / Schrippen" while the
    household keeps a plain "Brötchen". Matching on whole words lets the offer
    land on the article that already exists instead of creating a near
    duplicate, and the longest match wins so "Bio Butter" beats "Butter".
    """
    words = _fold(product).split()
    best = ""
    for name in catalogue:
        if _is_offer_headline(name):
            continue
        folded = _fold(name)
        if len(folded) < MIN_MATCH_LENGTH or len(folded) <= len(_fold(best)):
            continue
        parts = folded.split()
        if _contains_sequence(words, parts):
            best = name
    return best


def _is_offer_headline(name: str) -> bool:
    """Whether a catalogue entry is a leaflet headline instead of a staple.

    Such entries exist because this service used to file offers under their
    full advertised name. Left in the running they win every time, being the
    longest match for the very offer that created them, and the household's
    own "Brötchen" never gets used again.
    """
    words = clean_text(name).split()
    return len(words) > MAX_ARTICLE_WORDS or (
        len(words) > 1 and any(_is_brand_token(word) for word in words)
    )


def _contains_sequence(words: list[str], parts: list[str]) -> bool:
    """Whether the article's words appear in the offer, compounds included.

    German puts the head noun last, so an article named "Brötchen" is what
    "Weizenbrötchen" is. Only the final word may match as a suffix; matching
    the front would turn "Buttermilch" into butter.
    """
    if not parts:
        return False
    last = len(parts) - 1
    for start in range(len(words) - last):
        if all(words[start + offset] == part for offset, part in enumerate(parts[:last])):
            candidate = words[start + last]
            if candidate == parts[last] or candidate.endswith(parts[last]):
                return True
    return False


class KitchenOwlShoppingList:
    def __init__(
        self,
        base_url: str = KITCHENOWL_URL,
        token: str = KITCHENOWL_TOKEN,
        default_list_id: str = KITCHENOWL_LIST_ID,
        verify_tls: bool = KITCHENOWL_VERIFY_TLS,
        timeout_seconds: int = KITCHENOWL_TIMEOUT_SECONDS,
        max_items: int = KITCHENOWL_MAX_ITEMS_PER_REQUEST,
        match_items: bool = KITCHENOWL_MATCH_EXISTING_ITEMS,
        retailer_categories: bool = KITCHENOWL_RETAILER_CATEGORIES,
        category_prefix: str = KITCHENOWL_CATEGORY_PREFIX,
    ) -> None:
        self.base_url = clean_text(base_url).rstrip("/")
        # urlopen oeffnet auch file:/ und ftp:/. Eine falsch gesetzte
        # SUPERMARKT_KITCHENOWL_URL wuerde damit lokale Dateien lesen statt
        # eine Anfrage zu stellen, also gilt die Anbindung dann als nicht
        # konfiguriert.
        if self.base_url and urlsplit(self.base_url).scheme not in ("http", "https"):
            self.base_url = ""
        self.token = clean_text(token)
        self.default_list_id = clean_text(default_list_id)
        self.verify_tls = bool(verify_tls)
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.max_items = max(1, int(max_items))
        self.match_items = bool(match_items)
        self.retailer_categories = bool(retailer_categories)
        self.category_prefix = str(category_prefix)
        self._lists: list[dict[str, str]] = []
        self._catalogue: dict[str, tuple[float, list[str]]] = {}
        self._categories: dict[str, dict[str, int]] = {}
        self._lists_read_at = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _require_configured(self) -> None:
        if not self.configured:
            raise ShoppingListError(
                "Die Einkaufslisten-Anbindung ist nicht konfiguriert. "
                "SUPERMARKT_KITCHENOWL_URL und SUPERMARKT_KITCHENOWL_TOKEN setzen.",
                status_code=503,
            )

    def _ssl_context(self) -> ssl.SSLContext | None:
        if urlsplit(self.base_url).scheme != "https":
            return None
        context = ssl.create_default_context()
        if not self.verify_tls:
            # Opt-in only, for a self-signed certificate on a private instance.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _call(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        self._require_configured()
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST" if body is not None else "GET",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            # Das Schema ist im Konstruktor auf http/https begrenzt, file:/
            # und ftp:/ erreichen diese Zeile also nicht.
            with urlopen(request, timeout=self.timeout_seconds, context=self._ssl_context()) as response:  # nosec B310
                raw = response.read()
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise ShoppingListError(
                    "KitchenOwl hat den Zugriffstoken abgelehnt.", status_code=502
                ) from exc
            if exc.code == 404:
                raise ShoppingListError(
                    "KitchenOwl kennt diese Liste nicht.", status_code=400
                ) from exc
            raise ShoppingListError(
                f"KitchenOwl antwortete mit HTTP {exc.code}.", status_code=502
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ShoppingListError(
                f"KitchenOwl ist nicht erreichbar: {exc}", status_code=502
            ) from exc

        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise ShoppingListError(
                "KitchenOwl lieferte keine gültige JSON-Antwort.", status_code=502
            ) from exc

    @staticmethod
    def _entries(payload: Any) -> list[dict[str, Any]]:
        return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    def targets(self, refresh: bool = False) -> list[dict[str, str]]:
        """Return every shopping list the token can reach.

        A household with several lists contributes each of them, labelled with
        the household so two lists called "Einkauf" stay distinguishable.
        """
        self._require_configured()
        with self._lock:
            fresh = time.time() - self._lists_read_at < LIST_CACHE_TTL_SECONDS
            if self._lists and fresh and not refresh:
                return list(self._lists)

        households = self._entries(self._call("/api/household"))
        if not households:
            raise ShoppingListError(
                "KitchenOwl meldet keinen Haushalt für diesen Token.", status_code=502
            )

        lists: list[dict[str, str]] = []
        for household in households:
            household_id = household.get("id")
            if household_id is None:
                continue
            household_name = clean_text(household.get("name"))
            for entry in self._entries(self._call(f"/api/household/{household_id}/shoppinglist")):
                list_id = entry.get("id")
                if list_id is None:
                    continue
                name = clean_text(entry.get("name")) or f"Liste {list_id}"
                # Only qualify when it adds information.
                label = f"{household_name} · {name}" if household_name and len(households) > 1 else name
                lists.append({"entity_id": str(list_id), "label": label, "household_id": str(household_id)})

        lists.sort(key=lambda item: item["label"].casefold())
        with self._lock:
            self._lists = lists
            self._lists_read_at = time.time()
        return [
            {"entity_id": item["entity_id"], "label": item["label"]}
            for item in lists
        ]

    def _household_of(self, list_id: str) -> str:
        self.targets()
        with self._lock:
            for item in self._lists:
                if item["entity_id"] == list_id:
                    return item["household_id"]
        return ""

    def catalogue(self, household_id: str) -> list[str]:
        """Article names the household already keeps."""
        with self._lock:
            cached = self._catalogue.get(household_id)
            if cached and time.time() - cached[0] < CATALOGUE_CACHE_TTL_SECONDS:
                return list(cached[1])
        names = [
            clean_text(entry.get("name"))
            for entry in self._entries(self._call(f"/api/household/{household_id}/item"))
            if clean_text(entry.get("name"))
        ]
        with self._lock:
            self._catalogue[household_id] = (time.time(), names)
        return list(names)

    def _category_id(self, household_id: str, retailer: str) -> int | None:
        """Return the category for this retailer, creating it when missing."""
        name = f"{self.category_prefix}{clean_text(retailer)}".strip()
        if not clean_text(retailer):
            return None
        with self._lock:
            known = self._categories.get(household_id)
        if known is None:
            known = {
                clean_text(entry.get("name")).casefold(): entry["id"]
                for entry in self._entries(self._call(f"/api/household/{household_id}/category"))
                if entry.get("id") is not None and clean_text(entry.get("name"))
            }
            with self._lock:
                self._categories[household_id] = known
        existing = known.get(name.casefold())
        if existing is not None:
            return existing
        created = self._call(f"/api/household/{household_id}/category", {"name": name})
        if not isinstance(created, dict) or created.get("id") is None:
            return None
        known[name.casefold()] = created["id"]
        return created["id"]

    def resolve_entity(self, requested: str) -> str:
        """Return a list id KitchenOwl actually exposes."""
        wanted = clean_text(requested)
        if wanted and not wanted.isdigit():
            raise ShoppingListError(
                "Ungültige Ziel-Liste. Erwartet wird die numerische KitchenOwl-Listen-ID.",
                status_code=400,
            )

        known = {item["entity_id"] for item in self.targets()}
        for candidate in (wanted, self.default_list_id):
            if candidate and candidate in known:
                return candidate
        if wanted:
            raise ShoppingListError(
                f"KitchenOwl kennt die Liste {wanted} nicht.", status_code=400
            )
        if len(known) == 1:
            return next(iter(known))
        raise ShoppingListError(
            "Keine Ziel-Liste ausgewählt. SUPERMARKT_KITCHENOWL_LIST_ID setzen oder eine Liste übergeben.",
            status_code=400,
        )

    def entries(self, entity_id: str) -> list[str]:
        """Article names currently on the list.

        KitchenOwl removes an entry when it is checked off, so this is what
        tells a client that an offer it filed earlier is no longer pending.
        """
        target = self.resolve_entity(entity_id)
        names = []
        for entry in self._entries(self._call(f"/api/shoppinglist/{target}/items")):
            name = clean_text(entry.get("name"))
            if not name and isinstance(entry.get("item"), dict):
                name = clean_text(entry["item"].get("name"))
            if name:
                names.append(name)
        return names

    def add_items(self, entity_id: str, items: Iterable[dict[str, str]]) -> dict[str, Any]:
        """Add offers to one shopping list and report per-item success."""
        target = self.resolve_entity(entity_id)
        pending = [item for item in items if isinstance(item, dict)]
        if not pending:
            raise ShoppingListError("Es wurden keine Artikel übergeben.", status_code=400)
        if len(pending) > self.max_items:
            raise ShoppingListError(
                f"Es können höchstens {self.max_items} Artikel pro Anfrage übertragen werden.",
                status_code=400,
            )

        household_id = self._household_of(target)
        catalogue = (
            self.catalogue(household_id)
            if self.match_items and household_id
            else []
        )

        added: list[str] = []
        failed: list[dict[str, str]] = []
        for item in pending:
            product = item.get("product", "")
            retailer = item.get("retailer", "")
            name = build_item_text(product, retailer)
            # Land on the article the household already keeps; the full offer
            # name stays readable in the note.
            matched = match_existing_item(product, catalogue) if catalogue else ""
            if matched:
                name = matched

            try:
                quantity = max(1, int(item.get("quantity") or 1))
            except (TypeError, ValueError):
                quantity = 1

            use_category = self.retailer_categories and bool(household_id)
            # Only worth repeating when the article is named differently: a
            # previous send may have created the article under this very name,
            # and matching it then would print it twice.
            offer_name = product if clean_text(product) != clean_text(name) else ""
            description = build_item_description(
                "" if use_category else retailer,
                item.get("price_text", ""),
                item.get("validity", ""),
                item.get("pack", ""),
                quantity,
                offer_name,
            )
            payload: dict[str, Any] = {"name": name}
            if description:
                payload["description"] = description

            try:
                created = self._call(f"/api/shoppinglist/{target}/add-item-by-name", payload)
            except ShoppingListError as exc:
                failed.append({"item": name, "error": str(exc)})
                continue

            if use_category and isinstance(created, dict) and created.get("id") is not None:
                try:
                    category_id = self._category_id(household_id, retailer)
                    if category_id is not None:
                        self._call(f"/api/item/{created['id']}", {"category": {"id": category_id}})
                except ShoppingListError:
                    # The article is on the list; filing it is a nicety.
                    pass
            added.append(name)

        return {
            "status": "ok" if not failed else "partial",
            "entity_id": target,
            "added": added,
            "added_count": len(added),
            "failed": failed,
        }

    def health(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "host": urlsplit(self.base_url).netloc if self.base_url else "",
            "default_list": self.default_list_id,
            "verify_tls": self.verify_tls,
        }
