from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from .authz import access_summary, authorize
from .config import CACHE_TTL_MINUTES
from . import runtime

router = APIRouter()


@router.get("/health", include_in_schema=False)
def health(request: Request) -> dict[str, Any]:
    # This route stays reachable for container health checks even on a public
    # instance, so an unauthorised caller only learns that the service is up.
    # Cache paths, source wiring and shopping-list details are withheld.
    client = request.client
    if not authorize(
        client.host if client else "",
        request.headers.get("x-forwarded-for", ""),
        request.headers.get("authorization", ""),
    ):
        return {"status": "ok", "service": "korbklar"}

    engine = runtime.get_engine()
    return {
        "status": "ok",
        "service": "korbklar",
        "backend": "persistent-sqlite-cache",
        "cache_ttl_minutes": CACHE_TTL_MINUTES,
        **access_summary(),
        **runtime.get_image_service().health(),
        "sources": {
            "REWE": "official primary with Marktguru fallback",
            "EDEKA": "official primary with Marktguru fallback",
            "Kaufland": "official primary with Marktguru fallback",
            "Marktkauf": "official primary with Marktguru fallback",
            "ALDI": "official primary with Marktguru fallback",
            "Lidl": "Marktguru regional catalogue",
            "PENNY": "Marktguru regional catalogue",
            "Netto": "Marktguru regional catalogue",
            "Globus": "Marktguru regional catalogue",
            "Combi": "Marktguru regional catalogue",
            "famila Nordwest": "Marktguru regional catalogue",
        },
        "shopping_list": runtime.get_shopping_list().health(),
        **engine.store.health(),
    }
