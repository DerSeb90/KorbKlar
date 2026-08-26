"""Access control for a publicly reachable instance.

The rule is deliberately simple, so it can be reasoned about:

* Without ``SUPERMARKT_API_KEY`` nothing is restricted. A private instance
  behaves exactly as before.
* With an API key set, every request must either carry that key as a bearer
  token or originate from a network listed in ``SUPERMARKT_TRUSTED_NETWORKS``.

That covers both halves of a split deployment: the browser interface stays
usable without a login for anyone on the VPN, while scripts and the mobile
client authenticate with the key from anywhere.

Only ``/health`` stays reachable for everyone, because container health checks
need it. It answers with a minimal payload unless the caller is authorised, so
cache paths and source details are not exposed publicly.
"""

from __future__ import annotations

import ipaddress
import secrets
from functools import lru_cache
from typing import Any, Awaitable, Callable, Iterable, MutableMapping

from fastapi.responses import JSONResponse

from . import config
from .security import api_key

# Reachable without authorisation. Everything else is gated.
OPEN_PATHS = frozenset({"/health"})


@lru_cache(maxsize=8)
def _networks(values: tuple[str, ...]) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    parsed = []
    for value in values:
        try:
            parsed.append(ipaddress.ip_network(value.strip(), strict=False))
        except ValueError:
            # A malformed entry must never silently widen access, so it is
            # dropped rather than treated as "match anything".
            continue
    return tuple(parsed)


def trusted_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    # Read through the module so tests and reloads see a changed setting.
    return _networks(tuple(config.TRUSTED_NETWORKS))


def trusted_proxies() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return _networks(tuple(config.TRUSTED_PROXIES))


def _address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    text = (value or "").strip()
    if not text:
        return None
    # A forwarded entry may carry a port, and IPv6 may be bracketed.
    if text.startswith("["):
        text = text.partition("]")[0].lstrip("[")
    elif text.count(":") == 1:
        text = text.partition(":")[0]
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _in_networks(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    return any(address in network for network in networks)


def client_address(peer: str, forwarded_for: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Return the address the request really came from.

    ``X-Forwarded-For`` is only consulted when the immediate peer is a
    configured reverse proxy. The list is walked from the right, discarding
    proxies we ourselves trust, so a client cannot pick its own address by
    prepending a forged entry.
    """
    peer_address = _address(peer)
    if peer_address is None:
        return None

    proxies = trusted_proxies()
    if not proxies or not _in_networks(peer_address, proxies):
        return peer_address

    for candidate in reversed([item for item in forwarded_for.split(",") if item.strip()]):
        address = _address(candidate)
        if address is None:
            # An unparsable hop means the chain can no longer be trusted.
            return None
        if not _in_networks(address, proxies):
            return address
    return peer_address


def has_valid_token(authorization: str) -> bool:
    expected = api_key()
    if not expected:
        return False
    scheme, _, credential = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not credential:
        return False
    return secrets.compare_digest(credential, expected)


def is_trusted_client(peer: str, forwarded_for: str) -> bool:
    networks = trusted_networks()
    if not networks:
        return False
    address = client_address(peer, forwarded_for)
    return address is not None and _in_networks(address, networks)


def authorize(peer: str, forwarded_for: str, authorization: str) -> bool:
    """Whether this request may use the service."""
    if not api_key():
        return True
    return has_valid_token(authorization) or is_trusted_client(peer, forwarded_for)


def access_summary() -> dict[str, object]:
    """What the health endpoint may reveal about the current configuration."""
    return {
        "api_auth_configured": bool(api_key()),
        "trusted_networks": [str(network) for network in trusted_networks()],
        "trusted_proxies": [str(network) for network in trusted_proxies()],
    }


class AccessControlMiddleware:
    """Applies :func:`authorize` to every request.

    Implemented as ASGI middleware rather than per-route dependencies so a
    newly added route cannot accidentally be left unprotected.
    """

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path", "") in OPEN_PATHS or not api_key():
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").casefold(): value.decode("latin-1")
            for key, value in scope.get("headers") or []
        }
        client = scope.get("client")
        peer = client[0] if client else ""

        if authorize(peer, headers.get("x-forwarded-for", ""), headers.get("authorization", "")):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            {
                "detail": (
                    "Zugriff nur mit gültigem Bearer-Token oder aus einem "
                    "freigegebenen Netz."
                )
            },
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
