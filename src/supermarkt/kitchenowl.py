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
import ssl
import threading
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .common import clean_text
from .config import (
    KITCHENOWL_LIST_ID,
    KITCHENOWL_MAX_ITEMS_PER_REQUEST,
    KITCHENOWL_TIMEOUT_SECONDS,
    KITCHENOWL_TOKEN,
    KITCHENOWL_URL,
    KITCHENOWL_VERIFY_TLS,
    USER_AGENT,
)

LIST_CACHE_TTL_SECONDS = 300
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


def build_item_text(product: str, retailer: str) -> str:
    """Return the shopping list article name."""
    name = _truncate(product, MAX_ITEM_LENGTH)
    if name:
        return name
    fallback = clean_text(retailer)
    return _truncate(f"Angebot {fallback}" if fallback else "Angebot", MAX_ITEM_LENGTH)


def build_item_description(retailer: str, price_text: str, validity: str, pack: str) -> str:
    """Return the note shown underneath the article.

    Only values the offer actually carries are included. Nothing is estimated,
    matching how this service treats loyalty benefits.
    """
    parts = [
        clean_text(retailer),
        clean_text(price_text),
        clean_text(pack),
        clean_text(validity),
    ]
    return _truncate(" · ".join(part for part in parts if part), MAX_DESCRIPTION_LENGTH)


class KitchenOwlShoppingList:
    def __init__(
        self,
        base_url: str = KITCHENOWL_URL,
        token: str = KITCHENOWL_TOKEN,
        default_list_id: str = KITCHENOWL_LIST_ID,
        verify_tls: bool = KITCHENOWL_VERIFY_TLS,
        timeout_seconds: int = KITCHENOWL_TIMEOUT_SECONDS,
        max_items: int = KITCHENOWL_MAX_ITEMS_PER_REQUEST,
    ) -> None:
        self.base_url = clean_text(base_url).rstrip("/")
        self.token = clean_text(token)
        self.default_list_id = clean_text(default_list_id)
        self.verify_tls = bool(verify_tls)
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.max_items = max(1, int(max_items))
        self._lists: list[dict[str, str]] = []
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
            with urlopen(request, timeout=self.timeout_seconds, context=self._ssl_context()) as response:
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
                lists.append({"entity_id": str(list_id), "label": label})

        lists.sort(key=lambda item: item["label"].casefold())
        with self._lock:
            self._lists = lists
            self._lists_read_at = time.time()
        return list(lists)

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

        added: list[str] = []
        failed: list[dict[str, str]] = []
        for item in pending:
            name = build_item_text(item.get("product", ""), item.get("retailer", ""))
            payload: dict[str, Any] = {"name": name}
            description = build_item_description(
                item.get("retailer", ""),
                item.get("price_text", ""),
                item.get("validity", ""),
                item.get("pack", ""),
            )
            if description:
                payload["description"] = description
            try:
                self._call(f"/api/shoppinglist/{target}/add-item-by-name", payload)
            except ShoppingListError as exc:
                failed.append({"item": name, "error": str(exc)})
                continue
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
