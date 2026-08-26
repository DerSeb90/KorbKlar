"""Routes that push offers to a KitchenOwl shopping list.

Two entry points share one handler:

* ``/api/v1/shopping-list/...`` for automations, protected by the optional
  bearer token like every other REST route.
* ``/results/{search_id}/shopping-list/...`` for the browser interface,
  protected by the same HMAC result token that already guards result data and
  the image proxy. Without a valid results link nobody can write to the list.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .access import require_api_auth, verify_result_token
from .kitchenowl import ShoppingListError
from . import runtime

router = APIRouter()


class ShoppingListItem(BaseModel):
    product: str = Field(default="", max_length=300, description="Produktname als Listenartikel")
    retailer: str = Field(default="", max_length=80, description="Händler, erscheint in der Notiz")
    price_text: str = Field(default="", max_length=40, description="Angebotspreis, erscheint in der Notiz")
    validity: str = Field(default="", max_length=120, description="Gültigkeit, erscheint in der Notiz")
    pack: str = Field(default="", max_length=80, description="Packungsgröße, erscheint in der Notiz")
    quantity: int = Field(default=1, ge=1, le=999, description="Menge, führt die Notiz an")


class ShoppingListRequest(BaseModel):
    entity_id: str = Field(
        default="",
        max_length=140,
        description="KitchenOwl-Listen-ID, z. B. 1",
    )
    items: list[ShoppingListItem] = Field(
        default_factory=list,
        max_length=200,
        description="Angebote, die auf die Liste geschrieben werden",
    )


def _targets() -> dict[str, Any]:
    service = runtime.get_shopping_list()
    if not service.configured:
        return {"configured": False, "targets": [], "default_entity": ""}
    try:
        return {
            "configured": True,
            "targets": service.targets(),
            # Wire name kept stable for existing clients.
            "default_entity": service.default_list_id,
        }
    except ShoppingListError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _add_items(request_data: ShoppingListRequest) -> dict[str, Any]:
    if not request_data.items:
        raise HTTPException(status_code=400, detail="Es wurden keine Artikel übergeben.")
    try:
        return runtime.get_shopping_list().add_items(
            request_data.entity_id,
            [item.model_dump() for item in request_data.items],
        )
    except ShoppingListError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "/api/v1/shopping-list/targets",
    operation_id="einkaufsliste_ziele",
    summary="Verfügbare Einkaufslisten abrufen",
    description="Listet die Einkaufslisten der konfigurierten KitchenOwl-Instanz.",
)
def shopping_list_targets(_: None = Depends(require_api_auth)) -> dict[str, Any]:
    return _targets()


@router.post(
    "/api/v1/shopping-list/items",
    operation_id="einkaufsliste_ergaenzen",
    summary="Angebote auf die Einkaufsliste setzen",
    description=(
        "Schreibt Angebote auf eine KitchenOwl-Einkaufsliste. "
        "Der Artikelname ist das Produkt, die Notiz enthält Händler, Preis und Gültigkeit."
    ),
)
def shopping_list_add(
    request_data: ShoppingListRequest,
    _: None = Depends(require_api_auth),
) -> dict[str, Any]:
    return _add_items(request_data)


def _entries(entity_id: str) -> dict[str, Any]:
    service = runtime.get_shopping_list()
    if not service.configured:
        return {"configured": False, "items": []}
    try:
        return {"configured": True, "items": service.entries(entity_id)}
    except ShoppingListError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "/api/v1/shopping-list/entries",
    operation_id="einkaufsliste_eintraege",
    summary="Aktuelle Einträge einer Einkaufsliste",
    description="Listet, was gerade auf der Liste steht. Abgehakte Artikel entfernt KitchenOwl daraus.",
)
def shopping_list_entries(
    entity_id: str = Query(default="", max_length=140),
    _: None = Depends(require_api_auth),
) -> dict[str, Any]:
    return _entries(entity_id)


@router.get("/results/{search_id}/shopping-list/entries", include_in_schema=False)
def result_shopping_list_entries(
    search_id: str,
    token: str = Query(default=""),
    entity_id: str = Query(default="", max_length=140),
) -> dict[str, Any]:
    verify_result_token(search_id, token)
    return _entries(entity_id)


@router.get("/results/{search_id}/shopping-list/targets", include_in_schema=False)
def result_shopping_list_targets(search_id: str, token: str = Query(default="")) -> dict[str, Any]:
    verify_result_token(search_id, token)
    return _targets()


@router.post("/results/{search_id}/shopping-list/items", include_in_schema=False)
def result_shopping_list_add(
    search_id: str,
    request_data: ShoppingListRequest,
    token: str = Query(default=""),
) -> dict[str, Any]:
    verify_result_token(search_id, token)
    return _add_items(request_data)
