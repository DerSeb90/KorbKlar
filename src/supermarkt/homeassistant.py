"""Push offers to a Home Assistant todo list, for example a Bring shopping list.

Home Assistant's Bring integration exposes every Bring list as a ``todo``
entity. KorbKlar therefore talks to the generic ``todo.add_item`` service
instead of a Bring-specific interface, which also covers the built-in
shopping list, KitchenOwl and any other todo provider.

The configured Home Assistant instance is a first-party target chosen by the
operator, usually reachable only over LAN or VPN. That is why this client does
not use the SSRF guard from :mod:`.images`, which exists to protect against
untrusted image hosts. The token never leaves the server.
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
    HOMEASSISTANT_MAX_ITEMS_PER_REQUEST,
    HOMEASSISTANT_TIMEOUT_SECONDS,
    HOMEASSISTANT_TODO_ENTITY,
    HOMEASSISTANT_TOKEN,
    HOMEASSISTANT_URL,
    HOMEASSISTANT_VERIFY_TLS,
    USER_AGENT,
)

ENTITY_PATTERN = re.compile(r"^todo\.[a-z0-9_]{1,120}$")
ENTITY_CACHE_TTL_SECONDS = 300
MAX_ITEM_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 300


class ShoppingListError(RuntimeError):
    """A configuration or transport problem while talking to Home Assistant."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _truncate(value: str, limit: int) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def build_item_text(product: str, retailer: str) -> str:
    """Return the Bring article name."""
    name = _truncate(product, MAX_ITEM_LENGTH)
    if name:
        return name
    fallback = clean_text(retailer)
    return _truncate(f"Angebot {fallback}" if fallback else "Angebot", MAX_ITEM_LENGTH)


def build_item_description(retailer: str, price_text: str, validity: str, pack: str) -> str:
    """Return the Bring note shown underneath the article name.

    Only values that the offer actually carries are included. Nothing is
    estimated or invented, matching how KorbKlar treats loyalty benefits.
    """
    parts = [
        clean_text(retailer),
        clean_text(price_text),
        clean_text(pack),
        clean_text(validity),
    ]
    return _truncate(" · ".join(part for part in parts if part), MAX_DESCRIPTION_LENGTH)


class HomeAssistantShoppingList:
    def __init__(
        self,
        base_url: str = HOMEASSISTANT_URL,
        token: str = HOMEASSISTANT_TOKEN,
        default_entity: str = HOMEASSISTANT_TODO_ENTITY,
        verify_tls: bool = HOMEASSISTANT_VERIFY_TLS,
        timeout_seconds: int = HOMEASSISTANT_TIMEOUT_SECONDS,
        max_items: int = HOMEASSISTANT_MAX_ITEMS_PER_REQUEST,
    ) -> None:
        self.base_url = clean_text(base_url).rstrip("/")
        self.token = clean_text(token)
        self.default_entity = clean_text(default_entity).casefold()
        self.verify_tls = bool(verify_tls)
        self.timeout_seconds = max(3, int(timeout_seconds))
        self.max_items = max(1, int(max_items))
        self._entities: list[dict[str, str]] = []
        self._entities_read_at = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _require_configured(self) -> None:
        if not self.configured:
            raise ShoppingListError(
                "Die Einkaufslisten-Anbindung ist nicht konfiguriert. "
                "SUPERMARKT_HA_URL und SUPERMARKT_HA_TOKEN setzen.",
                status_code=503,
            )

    def _ssl_context(self) -> ssl.SSLContext | None:
        if urlsplit(self.base_url).scheme != "https":
            return None
        if self.verify_tls:
            return ssl.create_default_context()
        # Opt-in only, for a self-signed certificate on a private instance.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    def _call(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        self._require_configured()
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
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
                    "Home Assistant hat den Zugriffstoken abgelehnt.", status_code=502
                ) from exc
            raise ShoppingListError(
                f"Home Assistant antwortete mit HTTP {exc.code}.", status_code=502
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ShoppingListError(
                f"Home Assistant ist nicht erreichbar: {exc}", status_code=502
            ) from exc

        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise ShoppingListError(
                "Home Assistant lieferte keine gültige JSON-Antwort.", status_code=502
            ) from exc

    @staticmethod
    def _entity_from_state(state: Any) -> dict[str, str] | None:
        if not isinstance(state, dict):
            return None
        entity_id = clean_text(state.get("entity_id")).casefold()
        if not ENTITY_PATTERN.match(entity_id):
            return None
        attributes = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
        label = clean_text(attributes.get("friendly_name")) or entity_id
        return {"entity_id": entity_id, "label": label}

    def targets(self, refresh: bool = False) -> list[dict[str, str]]:
        """Return the todo entities Home Assistant currently exposes."""
        self._require_configured()
        with self._lock:
            fresh = time.time() - self._entities_read_at < ENTITY_CACHE_TTL_SECONDS
            if self._entities and fresh and not refresh:
                return list(self._entities)

        states = self._call("/api/states")
        if not isinstance(states, list):
            raise ShoppingListError("Home Assistant lieferte keine Entitätsliste.", status_code=502)
        entities = [
            entity
            for entity in (self._entity_from_state(state) for state in states)
            if entity is not None
        ]
        entities.sort(key=lambda entity: entity["label"].casefold())

        with self._lock:
            self._entities = entities
            self._entities_read_at = time.time()
        return list(entities)

    def resolve_entity(self, requested: str) -> str:
        """Return a todo entity id that Home Assistant actually exposes."""
        wanted = clean_text(requested).casefold()
        if wanted and not ENTITY_PATTERN.match(wanted):
            raise ShoppingListError(
                "Ungültige Ziel-Liste. Erwartet wird eine todo-Entität, z. B. todo.bring_einkaufsliste.",
                status_code=400,
            )

        known = {entity["entity_id"] for entity in self.targets()}
        for candidate in (wanted, self.default_entity):
            if candidate and candidate in known:
                return candidate
        if wanted:
            raise ShoppingListError(
                f"Home Assistant kennt die Liste {wanted} nicht.", status_code=400
            )
        if len(known) == 1:
            return next(iter(known))
        raise ShoppingListError(
            "Keine Ziel-Liste ausgewählt. SUPERMARKT_HA_TODO_ENTITY setzen oder eine Liste übergeben.",
            status_code=400,
        )

    def add_items(self, entity_id: str, items: Iterable[dict[str, str]]) -> dict[str, Any]:
        """Add offers to one todo list and report per-item success."""
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
            payload: dict[str, Any] = {"entity_id": target, "item": name}
            description = build_item_description(
                item.get("retailer", ""),
                item.get("price_text", ""),
                item.get("validity", ""),
                item.get("pack", ""),
            )
            if description:
                payload["description"] = description
            try:
                self._call("/api/services/todo/add_item", payload)
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
            "default_entity": self.default_entity,
            "verify_tls": self.verify_tls,
        }
