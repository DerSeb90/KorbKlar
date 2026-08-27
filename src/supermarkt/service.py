from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from typing import Any

from .cache import PersistentSnapshotStore
from .categories import normalize_category
from .common import clean_text, deduplicate_offers, filter_offers, normalize_aldi_region, normalize_view
from .compare import OfferComparator, OfferMapper
from .config import (
    CACHE_DB,
    CACHE_MAX_SNAPSHOTS,
    CACHE_TTL_MINUTES,
    KAUFLAND_CACHE_DIR,
    KAUFLAND_STORE_CACHE_TTL_SECONDS,
    REWE_CACHE_DIR,
    REWE_STORE_CACHE_TTL_SECONDS,
    MARKTGURU_PAGE_SIZE,
    MAX_WORKERS,
    RESULT_RETENTION_HOURS,
    TIMEOUT_SECONDS,
)
from .http import HttpClient, PostalCodeLocator
from .loyalty import available_programs, normalize_program_ids
from .models import AGGREGATOR_RETAILERS, RETAILER_SPECS, Offer, RetailerContext, ToolError, offer_from_dict, offer_retailers, offer_to_dict
from .presentation import offer_for_response, offer_sort_key, resolve_retailer_name
from .region import AldiRegionResolver
from .sources import MarktguruClient, OfficialAldiSource, OfficialEdekaSource, OfficialKauflandSource, OfficialMarktkaufSource, OfficialReweSource, OfficialHolabSource
from .sources.aldi_chain import AldiOfferChain

class SourceLoader:
    def __init__(self) -> None:
        http = HttpClient(TIMEOUT_SECONDS)
        locator = PostalCodeLocator(http)
        self.locator = locator
        self.marktguru = MarktguruClient(http, MARKTGURU_PAGE_SIZE, MAX_WORKERS)
        self.aldi_region = AldiRegionResolver(http)
        self.official_aldi = OfficialAldiSource(http)
        self.aldi_offers = AldiOfferChain(CACHE_DB, (self.official_aldi,))
        self.official_rewe = OfficialReweSource(
            locator,
            TIMEOUT_SECONDS,
            cache_dir=REWE_CACHE_DIR,
            store_cache_ttl_seconds=REWE_STORE_CACHE_TTL_SECONDS,
        )
        self.official_edeka = OfficialEdekaSource(TIMEOUT_SECONDS)
        self.official_holab = OfficialHolabSource(http)
        self.official_marktkauf = OfficialMarktkaufSource(TIMEOUT_SECONDS)
        self.official_kaufland = OfficialKauflandSource(
            http,
            locator,
            TIMEOUT_SECONDS,
            cache_dir=KAUFLAND_CACHE_DIR,
            store_cache_ttl_seconds=KAUFLAND_STORE_CACHE_TTL_SECONDS,
        )
        self.mapper = OfferMapper()

    @staticmethod
    def _contexts() -> dict[str, RetailerContext]:
        return {
            spec.name: RetailerContext(
                name=spec.name,
                aliases=tuple(alias.casefold() for alias in spec.aliases),
                excluded_aliases=tuple(alias.casefold() for alias in spec.excluded_aliases),
                color=spec.color,
                market_label=spec.name,
                market_url=spec.fallback_url,
            )
            for spec in RETAILER_SPECS
        }

    @staticmethod
    def _context_with_market(context: RetailerContext, label: str, url: str) -> RetailerContext:
        return replace(
            context,
            market_label=clean_text(label) or context.market_label,
            market_url=clean_text(url) or context.market_url,
        )

    def load(self, postal_code: str, aldi_region: str, progress=None) -> dict[str, Any]:
        notify = progress or (lambda **_fields: None)
        notify(status="loading", progress=5, source="Standortdienst", retailer="Alle Händler", category="Region", step="Region und Filialen werden ermittelt")
        contexts = self._contexts()
        request_errors: list[str] = []
        store_warnings: list[str] = []

        requested_region = normalize_aldi_region(aldi_region)
        resolved = requested_region
        if resolved == "auto":
            resolved = self.aldi_region.detect(postal_code)
        detected_regions = getattr(self.aldi_region, "last_regions", ())
        if requested_region == "auto":
            resolved_regions = list(detected_regions or ((resolved,) if resolved in {"nord", "sued"} else ()))
        elif requested_region == "both":
            resolved_regions = ["nord", "sued"]
        else:
            resolved_regions = [resolved] if resolved in {"nord", "sued"} else []
        aldi_names = ["ALDI Nord" if item == "nord" else "ALDI Süd" for item in resolved_regions]
        notify(total_sources=5 + len(aldi_names))
        if not aldi_names:
            detail = clean_text(self.aldi_region.last_error)
            warning = "ALDI-Region konnte geografisch nicht eindeutig bestimmt werden; ALDI wurde für diesen Abruf ausgelassen."
            store_warnings.append(warning + (f" ({detail})" if detail else ""))

        active_contexts = dict(contexts)
        for name in ("ALDI Nord", "ALDI Süd"):
            if name not in aldi_names:
                active_contexts.pop(name, None)

        source_states = {name: "keine Treffer" for name in active_contexts}
        final_by_retailer: dict[str, list[Offer]] = {}
        failed_primary: set[str] = set()

        # Retailers with maintained first-party adapters always prefer their
        # official source. A partial aggregator result must never suppress a
        # complete official catalogue or be mixed into it.
        official_jobs: dict[str, Any] = {
            "REWE": lambda: self.official_rewe.load(postal_code),
            "EDEKA": lambda: self.official_edeka.load(postal_code),
            "Kaufland": lambda: self.official_kaufland.load(postal_code),
            "Marktkauf": lambda: self.official_marktkauf.load(postal_code),
        }
        if hasattr(self, "official_holab"):
            official_jobs["HOL’AB!"] = lambda: self.official_holab.load(postal_code)
        completed_sources = 0
        processed_products = 0
        with ThreadPoolExecutor(max_workers=len(official_jobs)) as executor:
            futures = {executor.submit(loader): name for name, loader in official_jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                completed_sources += 1
                notify(status="processing", progress=10 + completed_sources * 9, source="Offizielle Webseite", retailer=name, category="Wochenangebote", step="Quelle wird ausgewertet", processed_sources=completed_sources, processed_products=processed_products)
                try:
                    offers = deduplicate_offers(list(future.result()))
                except Exception as exc:
                    failed_primary.add(name)
                    if name in {"Marktkauf", "HOL’AB!"}:
                        source_states[name] = "kein Markt"
                    else:
                        request_errors.append(f"{name} offiziell: {type(exc).__name__}: {exc}")
                    continue
                if not offers:
                    failed_primary.add(name)
                    if name in {"Marktkauf", "HOL’AB!"}:
                        source_states[name] = "kein Markt"
                    else:
                        request_errors.append(f"{name} offiziell: keine Angebote für die Zielwoche")
                    continue
                final_by_retailer[name] = offers
                source_states[name] = "offiziell"
                processed_products += len(offers)
                notify(status="processing", progress=10 + completed_sources * 9, source="Offizielle Webseite", retailer=name, category="Wochenangebote", step="Quelle verarbeitet", processed_sources=completed_sources, processed_products=processed_products)

        # ALDI is also first-party-first. Only the region determined for the
        # supplied postcode is loaded.
        if aldi_names:
            notify(status="loading", progress=50, source="Offizielle Webseite", retailer=" & ".join(aldi_names), category="Wochenangebote", step="Regionale Angebote werden getrennt geladen", processed_sources=completed_sources, processed_products=processed_products)
        with ThreadPoolExecutor(max_workers=max(1, len(aldi_names))) as executor:
            aldi_loader = getattr(self, "aldi_offers", self.official_aldi)
            aldi_futures = {executor.submit(aldi_loader.load, name): name for name in aldi_names}
            for future in as_completed(aldi_futures):
                aldi_name = aldi_futures[future]
                try:
                    aldi_result = future.result()
                    request_errors.extend(aldi_result.request_errors)
                    aldi_offers = deduplicate_offers(list(aldi_result.offers))
                except Exception as exc:
                    aldi_offers = []
                    request_errors.append(f"{aldi_name} offiziell: {type(exc).__name__}: {exc}")
                if aldi_offers:
                    final_by_retailer[aldi_name] = aldi_offers
                    source_states[aldi_name] = getattr(aldi_loader, "last_source", {}).get(aldi_name, "offiziell")
                    processed_products += len(aldi_offers)
                else:
                    failed_primary.add(aldi_name)
                completed_sources += 1
                notify(status="processing", progress=55, source="Offizielle Webseite", retailer=aldi_name, category="Wochenangebote", step="Quelle verarbeitet", processed_sources=completed_sources, processed_products=processed_products)

        # Lidl, PENNY, Netto and GLOBUS currently use Marktguru as their
        # catalogue source. The broad regional term search is supplemented by
        # retailer-name searches; those name queries are never treated as a
        # complete catalogue on their own. Failed first-party adapters may use
        # the same data only as a fallback.
        aggregator_names = {
            name for name in AGGREGATOR_RETAILERS
            if name in active_contexts
        }
        fallback_names = {
            name for name in failed_primary
            if name in active_contexts
        }
        marketguru_candidates = aggregator_names | fallback_names
        marktguru_mapped: list[Offer] = []
        if marketguru_candidates:
            completed_sources += 1
            notify(status="loading", progress=62, source="Marktguru", retailer="Lidl, PENNY, Netto, Globus, Combi, famila", category="Händlerkategorien", step="Regionale Angebote werden geladen", processed_sources=completed_sources, processed_products=processed_products)
            raw: list[dict[str, Any]] = []
            try:
                broad_raw, errors = self.marktguru.load_offers(postal_code)
                raw.extend(broad_raw)
                request_errors.extend(errors)
            except Exception as exc:
                request_errors.append(f"Marktguru: {type(exc).__name__}: {exc}")

            try:
                targeted_raw, errors = self.marktguru.load_retailer_queries(
                    postal_code,
                    sorted(marketguru_candidates, key=str.casefold),
                )
                raw.extend(targeted_raw)
                request_errors.extend(errors)
            except Exception as exc:
                request_errors.append(f"Marktguru Händlerergänzung: {type(exc).__name__}: {exc}")

            if raw:
                marktguru_mapped = deduplicate_offers(self.mapper.map_all(raw, active_contexts))
                processed_products += len(marktguru_mapped)
            notify(status="processing", progress=88, source="Marktguru", retailer="Lidl, PENNY, Netto, Globus, Combi, famila", category="Händlerkategorien", step="Angebote zugeordnet", processed_sources=completed_sources, processed_products=processed_products)

        for name in sorted(aggregator_names, key=str.casefold):
            offers = deduplicate_offers([
                offer for offer in marktguru_mapped
                if offer.retailer == name
            ])
            if offers:
                final_by_retailer[name] = offers
                source_states[name] = "Marktguru"
            elif not next((spec.optional for spec in RETAILER_SPECS if spec.name == name), False):
                request_errors.append(f"{name}: Marktguru lieferte keine Angebote für die Zielwoche")

        for name in sorted(fallback_names, key=str.casefold):
            # Never mix a fallback with a first-party catalogue that succeeded.
            if name in final_by_retailer:
                continue
            offers = deduplicate_offers([
                offer for offer in marktguru_mapped
                if offer.retailer == name
            ])
            if not offers:
                continue
            final_by_retailer[name] = offers
            source_states[name] = "Marktguru-Fallback"
            store_warnings.append(
                f"{name}: offizielle Quelle war nicht verfügbar; Marktguru wurde als Fallback verwendet."
            )

        # Update labels only from first-party adapters that actually supplied
        # the catalogue displayed to the user.
        if source_states.get("REWE") == "offiziell" and self.official_rewe.last_market_url:
            active_contexts["REWE"] = self._context_with_market(
                active_contexts["REWE"], self.official_rewe.last_market_label, self.official_rewe.last_market_url
            )
        if source_states.get("EDEKA") == "offiziell" and self.official_edeka.last_market_url:
            active_contexts["EDEKA"] = self._context_with_market(
                active_contexts["EDEKA"], self.official_edeka.last_market_label, self.official_edeka.last_market_url
            )
        if source_states.get("Marktkauf") == "offiziell" and self.official_marktkauf.last_market_url:
            active_contexts["Marktkauf"] = self._context_with_market(
                active_contexts["Marktkauf"], self.official_marktkauf.last_market_label, self.official_marktkauf.last_market_url
            )
        if source_states.get("Kaufland") == "offiziell" and self.official_kaufland.last_store_url:
            label = "Kaufland " + clean_text(self.official_kaufland.last_locality)
            active_contexts["Kaufland"] = self._context_with_market(
                active_contexts["Kaufland"], label, self.official_kaufland.last_store_url
            )

        offers = deduplicate_offers([
            offer
            for retailer_offers in final_by_retailer.values()
            for offer in retailer_offers
        ])
        offers = [replace(
            offer,
            source_category=offer.source_category or offer.category,
            category=normalize_category(offer.source_category or offer.category, offer.retailer, offer.name, offer.description),
            retailer_url=offer.retailer_url or contexts.get(offer.retailer, RetailerContext("", (), (), "", "", "")).market_url,
        ) for offer in offers]
        if not offers:
            raise ToolError("Keine Supermarktangebote konnten geladen werden")

        notify(status="processing", progress=96, source="KorbKlar", retailer="Alle Händler", category="Alle Kategorien", step="Angebote werden zusammengeführt", processed_sources=completed_sources, processed_products=len(offers))

        return {
            "postal_code": postal_code,
            "resolved_aldi_region": resolved,
            "resolved_aldi_regions": resolved_regions,
            "aldi_resolution": {"source": getattr(self.aldi_region, "last_provider", ""), "distance_km": getattr(self.aldi_region, "last_distance_km", None), "confidence": getattr(self.aldi_region, "last_confidence", "")},
            "offers": [offer_to_dict(offer) for offer in offers],
            "retailers": {name: asdict(context) for name, context in active_contexts.items()},
            "source_states": source_states,
            "request_errors": list(dict.fromkeys(clean_text(x) for x in request_errors if clean_text(x))),
            "store_warnings": list(dict.fromkeys(clean_text(x) for x in store_warnings if clean_text(x))),
        }

class SupermarketEngine:
    SNAPSHOT_SCHEMA = 3
    def __init__(self) -> None:
        self.store = PersistentSnapshotStore(CACHE_DB, CACHE_TTL_MINUTES, RESULT_RETENTION_HOURS, CACHE_MAX_SNAPSHOTS)
        self.loader = SourceLoader()
        self.comparator = OfferComparator()
        self._refresh_lock = threading.Lock()

    @staticmethod
    def cache_key(postal_code: str, aldi_region: str) -> str:
        return f"v{SupermarketEngine.SNAPSHOT_SCHEMA}:{postal_code}:{normalize_aldi_region(aldi_region)}"

    def snapshot(self, postal_code: str, aldi_region: str, refresh: bool = False, progress=None) -> tuple[dict[str, Any], bool]:
        key = self.cache_key(postal_code, aldi_region)
        if not refresh:
            cached = self.store.get_by_key(key)
            if cached is not None:
                if progress:
                    progress(status="processing", progress=90, source="Cache", retailer="Alle Händler", category="Alle Kategorien", step="Gespeicherter Vergleich wird geöffnet", processed_sources=1, total_sources=1, processed_products=len(cached.get("offers", [])))
                return cached, True
        with self._refresh_lock:
            if not refresh:
                cached = self.store.get_by_key(key)
                if cached is not None:
                    if progress:
                        progress(status="processing", progress=90, source="Cache", retailer="Alle Händler", category="Alle Kategorien", step="Gespeicherter Vergleich wird geöffnet", processed_sources=1, total_sources=1, processed_products=len(cached.get("offers", [])))
                    return cached, True
            fresh = self.loader.load(postal_code, aldi_region, progress=progress)
            return self.store.put(key, fresh), False

    def by_id(self, search_id: str) -> dict[str, Any]:
        snapshot = self.store.get_by_id(search_id)
        if snapshot is None:
            raise ToolError("Dieser Supermarktvergleich ist abgelaufen. Bitte die Suche neu starten.")
        return snapshot

    def page(
        self,
        snapshot: dict[str, Any],
        *,
        filter_text: str = "",
        retailer: str = "",
        category: str = "",
        page: int = 1,
        page_size: int = 100,
        view: str = "best_only",
        loyalty_programs: tuple[str, ...] = (),
        sort: str = "price",
        include_image_urls: bool = False,
    ) -> dict[str, Any]:
        offers = [offer_from_dict(item) for item in snapshot.get("offers", []) if isinstance(item, dict)]
        selected_programs = normalize_program_ids(loyalty_programs)
        source_retailer_counts: dict[str, int] = {}
        for offer in offers:
            source_retailer_counts[offer.retailer] = source_retailer_counts.get(offer.retailer, 0) + 1

        normalized_view = normalize_view(view)
        all_comparison = self.comparator.compare(offers, selected_programs, "all")
        best_comparison = self.comparator.compare(offers, selected_programs, "best_only")

        retailers_raw = snapshot.get("retailers") or {}
        retailers = {
            name: RetailerContext(**value)
            for name, value in retailers_raw.items()
            if isinstance(name, str) and isinstance(value, dict)
        }
        selected_retailer = resolve_retailer_name(retailer, retailers)
        selected_category = clean_text(category)

        def scope(items: list[Offer]) -> list[Offer]:
            scoped = filter_offers(items, filter_text)
            if selected_retailer:
                # A merged row stands for several retailers and must survive
                # the filter for each of them.
                wanted = selected_retailer.casefold()
                scoped = [
                    offer
                    for offer in scoped
                    if any(
                        name.casefold() == wanted
                        for name in offer_retailers(offer)
                    )
                ]
            if selected_category:
                scoped = [offer for offer in scoped if offer.category.casefold() == selected_category.casefold()]
            return scoped

        all_scoped = scope(all_comparison.offers)
        best_scoped = scope(best_comparison.offers)
        hidden_count = max(0, len(all_scoped) - len(best_scoped))
        filtered = all_scoped if normalized_view == "all" else best_scoped

        # Chip counts intentionally reflect the current text filter and view,
        # but not the selected retailer chip itself, so switching retailers
        # remains possible without resetting the other filters.
        comparison_for_counts = all_comparison if normalized_view == "all" else best_comparison
        count_scope = filter_offers(comparison_for_counts.offers, filter_text)
        counts: dict[str, int] = {}
        for offer in count_scope:
            # A merged row counts once for every retailer it represents, so a
            # chip still reflects what that retailer actually offers.
            for name in offer_retailers(offer):
                counts[name] = counts.get(name, 0) + 1
        category_scope = [
            offer
            for offer in count_scope
            if not selected_retailer
            or any(
                name.casefold() == selected_retailer.casefold()
                for name in offer_retailers(offer)
            )
        ]
        category_counts: dict[str, int] = {}
        for offer in category_scope:
            category_counts[offer.category] = category_counts.get(offer.category, 0) + 1

        ordered = sorted(filtered, key=lambda offer: offer_sort_key(offer, sort))
        page_size = max(1, min(int(page_size), 100))
        page_count = max(1, (len(ordered) + page_size - 1) // page_size)
        page = max(1, min(int(page), page_count))
        start = (page - 1) * page_size
        selected = ordered[start:start + page_size]

        result = {
            "search_id": snapshot["search_id"],
            "postal_code": snapshot.get("postal_code", ""),
            "resolved_aldi_region": snapshot.get("resolved_aldi_region", "auto"),
            "cache_age_seconds": max(0, int(time.time() - float(snapshot.get("created_at", time.time())))),
            "source_offer_count": len(snapshot.get("offers", [])),
            "compared_offer_count": len(comparison_for_counts.offers),
            "filtered_offer_count": len(ordered),
            "hidden_count": hidden_count,
            "page": page,
            "page_size": page_size,
            "page_count": page_count,
            "has_next": page < page_count,
            "has_previous": page > 1,
            "retailer": selected_retailer,
            "view": normalized_view,
            "retailer_counts": counts,
            "category": selected_category,
            "category_counts": category_counts,
            "selected_loyalty_programs": list(selected_programs),
            "available_loyalty_programs": available_programs(source_retailer_counts, offers),
            "loyalty_note": (
                "Es werden nur öffentlich ausgewiesene Direktpreise und Euro-Guthaben verrechnet. "
                "Personalisierte Coupons oder Punkte ohne konkreten Angebotswert werden nicht geschätzt."
            ),
            "source_states": snapshot.get("source_states", {}),
            "warnings": list(dict.fromkeys([
                *snapshot.get("request_errors", []),
                *snapshot.get("store_warnings", []),
            ]))[:12],
            "offers": [offer_for_response(offer, include_image_urls=include_image_urls) for offer in selected],
        }
        return result
