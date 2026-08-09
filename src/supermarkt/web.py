from __future__ import annotations

import hmac
import secrets
import threading
from typing import Annotated, Any, Literal, Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, field_validator

from .assets import FAVICON_SVG
from .common import clean_text, validate_postal_code
from .config import (
    CACHE_TTL_MINUTES,
    IMAGE_CACHE_DIR,
    IMAGE_CACHE_MAX_BYTES,
    IMAGE_CACHE_TTL_SECONDS,
    IMAGE_MAX_FILE_BYTES,
    MARKTGURU_HOME,
    TIMEOUT_SECONDS,
)
from .images import ImageService, ImageServiceError, is_rejected_image_url, normalize_image_url
from .loyalty import PROGRAMS, VALID_PROGRAM_IDS, normalize_program_ids
from .models import AGGREGATOR_RETAILERS, ToolError
from .security import api_key, signature, valid_signature
from .service import SupermarketEngine
from .ui import build_home_html, build_results_html

router = APIRouter(tags=["Supermarkt"])
_engine: Optional[SupermarketEngine] = None
_engine_lock = threading.Lock()
_image_service: Optional[ImageService] = None
_image_service_lock = threading.Lock()


class SupermarketRequest(BaseModel):
    postal_code: str = Field(description="Deutsche Postleitzahl mit fünf Ziffern")
    aldi_region: Literal["auto", "nord", "sued"] = Field(
        default="auto",
        description="ALDI-Region. Explizite Nutzerangaben übernehmen, sonst auto.",
    )
    filter_text: str = Field(default="", max_length=120, description="Optionaler Produkt- oder Markenfilter")
    retailer: str = Field(default="", max_length=60, description="Optionaler Händlerfilter, z. B. Lidl oder Kaufland")
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=100, ge=1, le=100, description="Maximal 100 Angebote pro API-Antwort")
    view: Literal["best_only", "all"] = Field(default="best_only", description="Nur günstigste sichere Treffer oder alle")
    loyalty_programs: list[str] = Field(
        default_factory=list,
        description=(
            "Mehrere vorhandene Bonusprogramme gleichzeitig aktivieren. Gültige IDs: "
            + ", ".join(program.id for program in PROGRAMS)
        ),
    )
    sort: Literal["price", "unit_price", "retailer", "product"] = Field(default="price")
    refresh: bool = Field(default=False, description="Servercache ignorieren und Quellen neu abrufen")

    @field_validator("postal_code")
    @classmethod
    def valid_postal_code(cls, value: str) -> str:
        normalized = validate_postal_code(value)
        if normalized is None:
            raise ValueError("Postleitzahl muss genau fünf Ziffern enthalten")
        return normalized

    @field_validator("loyalty_programs")
    @classmethod
    def valid_loyalty_programs(cls, values: list[str]) -> list[str]:
        raw = [str(value or "").strip().casefold() for value in values]
        unknown = sorted({value for value in raw if value and value not in VALID_PROGRAM_IDS})
        if unknown:
            raise ValueError("Unbekannte Bonusprogramme: " + ", ".join(unknown))
        return list(normalize_program_ids(raw))


def get_engine() -> SupermarketEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = SupermarketEngine()
        return _engine


def require_api_auth(request: Request) -> None:
    """Protect the REST endpoint only when SUPERMARKT_API_KEY is configured."""
    expected = api_key()
    if not expected:
        return
    authorization = request.headers.get("authorization", "")
    scheme, _, credential = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not credential or not secrets.compare_digest(credential, expected):
        raise HTTPException(status_code=401, detail="Ungültiger Bearer-Token")


def result_token(search_id: str) -> str:
    return signature(search_id, namespace="result")


def verify_result_token(search_id: str, token: str) -> None:
    if not valid_signature(token, search_id, namespace="result"):
        raise HTTPException(status_code=403, detail="Ungültiger oder fehlender Ergebnis-Schlüssel")


def build_result_path(search_id: str, loyalty_programs: tuple[str, ...] = ()) -> str:
    params: dict[str, str] = {"token": result_token(search_id)}
    selected = normalize_program_ids(loyalty_programs)
    if selected:
        params["loyalty"] = ",".join(selected)
    return f"/results/{quote(search_id, safe='')}?{urlencode(params)}"


def build_result_url(request: Request, search_id: str, loyalty_programs: tuple[str, ...] = ()) -> str:
    """Build one absolute result URL from the current request, without a configured public base URL."""
    path = build_result_path(search_id, loyalty_programs)
    return str(request.base_url).rstrip("/") + path


def _image_service_instance() -> ImageService:
    global _image_service
    with _image_service_lock:
        if _image_service is None:
            _image_service = ImageService(
                cache_dir=IMAGE_CACHE_DIR,
                ttl_seconds=IMAGE_CACHE_TTL_SECONDS,
                max_cache_bytes=IMAGE_CACHE_MAX_BYTES,
                max_file_bytes=IMAGE_MAX_FILE_BYTES,
                timeout_seconds=min(TIMEOUT_SECONDS, 30),
            )
        return _image_service


def image_proxy_signature(source_url: str, referer: str, product: str, retailer: str) -> str:
    return signature(source_url, referer, product, retailer, namespace="image")


def build_image_proxy_url(offer: dict[str, Any]) -> str:
    source_url = normalize_image_url(offer.get("image_url"))
    if not source_url or is_rejected_image_url(source_url):
        return ""
    retailer = clean_text(offer.get("retailer"))
    product = clean_text(offer.get("product"))
    if not product:
        return ""
    referer = MARKTGURU_HOME if retailer in AGGREGATOR_RETAILERS else normalize_image_url(offer.get("source_url"))
    sig = image_proxy_signature(source_url, referer, product, retailer)
    return "/image?" + urlencode({
        "src": source_url,
        "ref": referer,
        "q": product,
        "retailer": retailer,
        "sig": sig,
    })


def _proxy_page_images(page: dict[str, Any]) -> dict[str, Any]:
    for offer in page.get("offers") or []:
        if isinstance(offer, dict):
            offer["image_url"] = build_image_proxy_url(offer)
    return page


@router.get("/favicon.svg", include_in_schema=False)
def favicon_svg() -> Response:
    return Response(
        content=FAVICON_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/favicon.ico", include_in_schema=False)
def favicon_ico() -> Response:
    # Fallback fuer Browser, die weiterhin /favicon.ico automatisch anfragen.
    return Response(
        content=FAVICON_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/", include_in_schema=False, response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(build_home_html(), headers={"Cache-Control": "no-store"})


@router.post("/search", include_in_schema=False)
def browser_search(postal_code_input: Annotated[str, Form(alias="postal_code")] = "") -> Response:
    raw_postal_code = clean_text(postal_code_input)
    postal_code = validate_postal_code(raw_postal_code)
    if postal_code is None:
        return HTMLResponse(
            build_home_html(error="Bitte eine gültige fünfstellige deutsche Postleitzahl eingeben.", postal_code=raw_postal_code),
            status_code=400,
            headers={"Cache-Control": "no-store"},
        )
    try:
        snapshot, _ = get_engine().snapshot(postal_code, "auto", False)
    except ToolError as exc:
        return HTMLResponse(
            build_home_html(error=str(exc), postal_code=postal_code),
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )
    return RedirectResponse(build_result_path(snapshot["search_id"]), status_code=303)


@router.post(
    "/api/v1/compare",
    operation_id="supermarkt_preisvergleich",
    summary="Supermarktangebote vergleichen",
    description=(
        "Lädt aktuelle regionale Supermarktangebote serverseitig, vergleicht sie und gibt eine kompakte Ergebnisseite "
        "sowie genau einen absoluten result_url zur vollständigen interaktiven Liste zurück."
    ),
)
def supermarket_compare(
    request_data: SupermarketRequest,
    request: Request,
    _: None = Depends(require_api_auth),
) -> dict[str, Any]:
    try:
        engine = get_engine()
        snapshot, from_cache = engine.snapshot(request_data.postal_code, request_data.aldi_region, request_data.refresh)
        page = engine.page(
            snapshot,
            filter_text=request_data.filter_text,
            retailer=request_data.retailer,
            page=request_data.page,
            page_size=request_data.page_size,
            view=request_data.view,
            loyalty_programs=tuple(request_data.loyalty_programs),
            sort=request_data.sort,
            include_image_urls=False,
        )
        page["status"] = "ok"
        page["from_cache"] = from_cache
        page["result_url"] = build_result_url(request, snapshot["search_id"], tuple(request_data.loyalty_programs))
        return page
    except ToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/results/{search_id}", include_in_schema=False)
def result_data(
    search_id: str,
    token: str = Query(default=""),
    q: str = Query(default="", max_length=120),
    retailer: str = Query(default="", max_length=60),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=100, ge=1, le=100),
    view: Literal["best_only", "all"] = Query(default="best_only"),
    loyalty: str = Query(default="", max_length=500),
    sort: Literal["price", "unit_price", "retailer", "product"] = Query(default="price"),
) -> dict[str, Any]:
    verify_result_token(search_id, token)
    try:
        snapshot = get_engine().by_id(search_id)
        page_data = get_engine().page(
            snapshot,
            filter_text=q,
            retailer=retailer,
            page=page,
            page_size=page_size,
            view=view,
            loyalty_programs=normalize_program_ids(loyalty.split(",")),
            sort=sort,
            include_image_urls=True,
        )
        return _proxy_page_images(page_data)
    except ToolError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc


@router.get("/results/{search_id}", include_in_schema=False, response_class=HTMLResponse, name="supermarket_results")
def results_page(
    search_id: str,
    token: str = Query(default=""),
    loyalty: str = Query(default="", max_length=500),
) -> HTMLResponse:
    verify_result_token(search_id, token)
    try:
        get_engine().by_id(search_id)
    except ToolError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    selected = normalize_program_ids(loyalty.split(","))
    return HTMLResponse(
        build_results_html(search_id, token, selected),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/image", include_in_schema=False)
def supermarket_image(
    src: str = Query(default="", max_length=5000),
    ref: str = Query(default="", max_length=5000),
    q: str = Query(..., min_length=1, max_length=300),
    retailer: str = Query(default="", max_length=80),
    sig: str = Query(..., min_length=16, max_length=64),
) -> Response:
    expected = image_proxy_signature(src, ref, q, retailer)
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="Ungültiger Bildschlüssel")
    try:
        result = _image_service_instance().get(
            source_url=src,
            referer=ref,
            product=q,
            retailer=retailer,
        )
    except ImageServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
            "X-Supermarkt-Image-Origin": result.origin,
        },
    )


@router.get("/health", include_in_schema=False)
def health() -> dict[str, Any]:
    engine = get_engine()
    return {
        "status": "ok",
        "service": "supermarkt-preisvergleich",
        "backend": "persistent-sqlite-cache",
        "cache_ttl_minutes": CACHE_TTL_MINUTES,
        "api_auth_configured": bool(api_key()),
        **_image_service_instance().health(),
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
        },
        **engine.store.health(),
    }
