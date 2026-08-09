from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import date
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..common import (
    build_match_key,
    clean_brand,
    clean_description,
    clean_text,
    date_is_current,
    deduplicate_offers,
    extract_image_url,
    first_date,
    first_number,
    first_text,
    format_validity,
    normalize_pack,
    offer_reference_date,
    parse_base_price_text,
    parse_iso_date,
    parse_number,
    strip_html,
    walk_json,
)
from ..config import TIMEOUT_SECONDS
from ..http import HttpClient
from ..images import is_rejected_image_url, normalize_image_url
from ..models import LoadResult, Offer, ToolError

class AldiSouthWeeklyParser(HTMLParser):
    """Produktkarten der offiziellen ALDI-SÜD-Wochenangebotsseiten."""

    IMAGE_ATTRS = ("data-src", "data-lazy-src", "data-original", "data-srcset", "srcset", "src")

    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.cards: list[dict[str, Any]] = []
        self._current: Optional[dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = {str(key).casefold(): value or "" for key, value in attrs}
        tag = tag.casefold()
        if tag == "a":
            href = clean_text(attributes.get("href"))
            absolute = urljoin(self.source_url, href) if href else ""
            try:
                path = urlsplit(absolute).path.casefold()
            except ValueError:
                path = ""
            if "/produkt/" in path:
                self._finish_current()
                self._current = {
                    "url": absolute,
                    "label": clean_text(attributes.get("aria-label") or attributes.get("title")),
                    "image_url": "",
                    "text_parts": [],
                }
                return
        if tag != "img" or self._current is None:
            return
        for field in self.IMAGE_ATTRS:
            raw = clean_text(attributes.get(field))
            if not raw:
                continue
            if "srcset" in field:
                candidates = [part.strip().split(" ", 1)[0] for part in raw.split(",") if part.strip()]
                raw = candidates[-1] if candidates else ""
            image_url = normalize_image_url(raw, base_url=self.source_url)
            if image_url and not is_rejected_image_url(image_url):
                self._current["image_url"] = image_url
                break

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._current is not None:
            self._finish_current()

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        value = clean_text(data)
        if value:
            parts = self._current["text_parts"]
            if len(parts) < 100 and sum(len(part) for part in parts) < 6000:
                parts.append(value)

    def finish(self) -> None:
        self._finish_current()

    def _finish_current(self) -> None:
        if self._current is not None:
            if self._current.get("text_parts"):
                self.cards.append(self._current)
            self._current = None

class OfficialAldiSource:
    NORTH_URL = "https://www.aldi-nord.de/angebote.html"
    SOUTH_INDEX_URL = "https://www.aldi-sued.de/angebote"

    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self.last_south_pages: list[dict[str, Any]] = []
        self.last_south_errors: list[str] = []

    def load(self, retailer: str) -> LoadResult:
        if retailer == "ALDI Nord":
            return LoadResult(self._load_north(), [])
        if retailer == "ALDI Süd":
            return LoadResult(self._load_south(), list(self.last_south_errors))
        return LoadResult([], ["ALDI-Region ist nicht eindeutig bestimmt"])

    def _load_north(self) -> list[Offer]:
        page = self.http.get_bytes(self.NORTH_URL).decode("utf-8", errors="replace")
        match = re.search(
            r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            raise ToolError("Die offiziellen ALDI-Nord-Angebotsdaten wurden nicht gefunden")
        next_data = json.loads(html.unescape(match.group(1)))
        page_props = next_data.get("props", {}).get("pageProps", {})
        api_data = page_props.get("apiData")
        if isinstance(api_data, str):
            api_data = json.loads(api_data)
        if not isinstance(api_data, list):
            raise ToolError("ALDI Nord lieferte kein lesbares Angebotsformat")

        response_data: Optional[dict[str, Any]] = None
        for entry in api_data:
            if (
                isinstance(entry, list)
                and len(entry) == 2
                and entry[0] == "OFFER_GET"
                and isinstance(entry[1], dict)
                and isinstance(entry[1].get("res"), dict)
            ):
                response_data = entry[1]["res"]
                break
        if response_data is None:
            raise ToolError("Der offizielle ALDI-Nord-Angebotsblock fehlt")

        product_map = response_data.get("algoliaDataMap") or {}
        categories = response_data.get("categories") or []
        if not isinstance(product_map, dict) or not isinstance(categories, list):
            raise ToolError("Die offiziellen ALDI-Nord-Angebote sind unvollständig")

        placement: dict[str, dict[str, str]] = {}
        for group in categories:
            if not isinstance(group, dict):
                continue
            start = clean_text(group.get("startDate"))
            end = clean_text(group.get("endDate"))
            for category in group.get("content") or []:
                if not isinstance(category, dict):
                    continue
                label = clean_text(category.get("title") or category.get("teaserTitle")) or "Weitere Angebote"
                for product_id in category.get("productIds") or []:
                    placement.setdefault(str(product_id), {"category": label, "start": start, "end": end})

        offers: list[Offer] = []
        for product_id, product in product_map.items():
            if not isinstance(product, dict):
                continue
            prices = product.get("promotionPrices") or []
            price_data = next(
                (item for item in prices if isinstance(item, dict) and item.get("priceValue") is not None),
                product.get("currentPrice") if isinstance(product.get("currentPrice"), dict) else {},
            )
            place = placement.get(str(product_id), {})
            start = parse_iso_date(place.get("start") or price_data.get("validFromLocalDate"))
            end = parse_iso_date(place.get("end") or price_data.get("validUntilLocalDate"))
            if not date_is_current(start, end):
                continue

            name = clean_text(product.get("name"))
            brand = clean_brand(product.get("brandName"))
            if not name:
                continue
            display_name = name if not brand or brand.casefold() in name.casefold() else f"{brand} {name}"
            description = " · ".join(
                dict.fromkeys(
                    value
                    for value in (
                        clean_description(product.get("shortDescription")),
                        clean_text(product.get("salesUnit")),
                    )
                    if value
                )
            )
            price = parse_number(price_data.get("priceValue"))
            if price is None or price <= 0:
                continue
            base_values = price_data.get("basePrice") or []
            if isinstance(base_values, dict):
                base_values = [base_values]
            base_entry = next((item for item in base_values if isinstance(item, dict)), {})
            pack = normalize_pack(f"{name} {description}")
            validity = format_validity(start, end)
            offers.append(
                Offer(
                    offer_id=f"aldi-nord:{product_id}",
                    retailer="ALDI Nord",
                    category=place.get("category") or "Weitere Angebote",
                    name=display_name,
                    brand=brand,
                    description=description,
                    price=price,
                    base_price=parse_number(base_entry.get("basePriceValue")),
                    base_unit=clean_text(base_entry.get("basePriceScale")),
                    pack_signature=pack,
                    validity_label=validity,
                    match_key=build_match_key(brand, name, pack, f"aldi-nord:{product_id}"),
                    source_url=self.NORTH_URL,
                    image_url=extract_image_url(product, base_url=self.NORTH_URL),
                )
            )
        if not offers:
            raise ToolError("ALDI Nord lieferte keine aktuell gültigen Angebote")
        return deduplicate_offers(offers)

    def _south_get_html(self, url: str) -> str:
        errors: list[str] = []
        try:
            return self.http.get_bytes(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            ).decode("utf-8", errors="replace")
        except Exception as exc:
            errors.append(f"HTTP: {type(exc).__name__}: {exc}")

        for headless in ("--headless=new", "--headless"):
            try:
                completed = subprocess.run(
                    [
                        "chromium", headless, "--no-sandbox", "--disable-gpu",
                        "--disable-dev-shm-usage", "--lang=de-DE",
                        "--virtual-time-budget=10000", "--dump-dom", url,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=min(TIMEOUT_SECONDS + 15, 90),
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                errors.append(f"Chromium: {type(exc).__name__}: {exc}")
                continue
            page = completed.stdout or ""
            if completed.returncode == 0 and "<html" in page.casefold():
                return page
            errors.append(f"Chromium rc={completed.returncode}")
        raise ToolError("ALDI Süd Seite nicht abrufbar: " + " | ".join(errors[-3:]))

    @staticmethod
    def _south_offer_urls(page: str) -> list[str]:
        today = offer_reference_date()
        earliest = date.fromordinal(today.toordinal() - 8)
        urls: list[str] = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', page, flags=re.IGNORECASE):
            href = html.unescape(href).strip()
            candidate = urljoin("https://www.aldi-sued.de/", href)
            try:
                parsed = urlsplit(candidate)
            except ValueError:
                continue
            if (parsed.hostname or "").casefold() != "www.aldi-sued.de":
                continue
            path = parsed.path.rstrip("/") or "/"
            keep = path.startswith("/produkte/wochenangebote")
            match = re.fullmatch(r"/angebote/(\d{4}-\d{2}-\d{2})", path)
            if match:
                try:
                    offer_date = date.fromisoformat(match.group(1))
                except ValueError:
                    offer_date = None
                keep = bool(offer_date and earliest <= offer_date <= today)
            if not keep:
                continue
            normalized = urlunsplit(("https", "www.aldi-sued.de", parsed.path, parsed.query, ""))
            if normalized not in urls:
                urls.append(normalized)
        return urls

    def _south_node_to_offer(self, node: dict[str, Any], source_url: str) -> Optional[Offer]:
        name = first_text(node, ("name", "title", "productName", "headline"))
        if not name or len(name) > 220:
            return None
        price = first_number(node, ("price", "priceValue", "currentPrice", "salesPrice", "sellingPrice"))
        offers_node = node.get("offers")
        if price is None and isinstance(offers_node, dict):
            price = first_number(offers_node, ("price", "lowPrice", "highPrice"))
        if price is None or price <= 0:
            return None
        start = first_date(node, ("validFrom", "startDate", "availableFrom", "availabilityStartDate"))
        end = first_date(node, ("validThrough", "endDate", "availableTo", "availabilityEndDate"))
        if isinstance(offers_node, dict):
            start = start or first_date(offers_node, ("validFrom", "startDate"))
            end = end or first_date(offers_node, ("validThrough", "endDate"))
        if (start or end) and not date_is_current(start, end):
            return None
        brand_value = node.get("brand")
        brand = clean_brand(brand_value.get("name")) if isinstance(brand_value, dict) else clean_brand(brand_value)
        description = first_text(node, ("description", "shortDescription", "subtitle", "salesUnit"))
        category = first_text(node, ("category", "categoryName", "sectionTitle")) or "Weitere Angebote"
        identifier = first_text(node, ("sku", "id", "productId", "articleNumber")) or f"{name}:{price}"
        pack = normalize_pack(f"{name} {description}")
        return Offer(
            offer_id=f"aldi-sued:{identifier}", retailer="ALDI Süd", category=category,
            name=name if not brand or brand.casefold() in name.casefold() else f"{brand} {name}",
            brand=brand, description=description, price=price,
            base_price=first_number(node, ("basePrice", "referencePrice", "unitPrice")),
            base_unit=first_text(node, ("basePriceUnit", "referenceUnit", "unit")), pack_signature=pack,
            validity_label=format_validity(start, end) if start or end else "Aktuelle Angebotsseite",
            match_key=build_match_key(brand, name, pack, f"aldi-sued:{identifier}"),
            source_url=source_url, image_url=extract_image_url(node, base_url=source_url),
        )

    def _south_card_to_offer(
        self,
        card: dict[str, Any],
        start: Optional[date],
        end: Optional[date],
        index: int,
        category: str = "Wochenangebote",
    ) -> Optional[Offer]:
        product_url = clean_text(card.get("url"))
        text = clean_text(" ".join(card.get("text_parts") or []))
        label = clean_text(card.get("label"))
        if not product_url or not text:
            return None
        price_match = re.search(r"(\d{1,4}[,.]\d{2})\s*€(?!\s*/)", text)
        price = parse_number(price_match.group(1)) if price_match else None
        if price is None or price <= 0:
            return None
        name = label if label and "€" not in label and len(label) <= 160 else ""
        if not name:
            try:
                slug = urlsplit(product_url).path.rstrip("/").rsplit("/", 1)[-1]
            except ValueError:
                slug = ""
            slug = re.sub(r"-\d{12,}$", "", slug)
            name = clean_text(slug.replace("-", " "))
        if not name:
            return None
        if name == name.casefold():
            name = " ".join(part.upper() if len(part) <= 4 and part.isalpha() else part.capitalize() for part in name.split())
        base_price, base_unit = parse_base_price_text(text)
        pack_text = re.sub(
            r"\(?\s*(?:1\s*)?(?:kg|kilogramm|l|liter|wl|waschladungen?|stück|stueck|stk\.?)\s*=\s*\d+(?:[.,]\d{1,2})\s*€?\s*\)?",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        pack = normalize_pack(f"{name} {pack_text}")
        image_url = normalize_image_url(card.get("image_url"), base_url=product_url)
        if is_rejected_image_url(image_url):
            image_url = ""
        identifier = product_url.rstrip("/").rsplit("-", 1)[-1] or str(index)
        return Offer(
            offer_id=f"aldi-sued:{identifier}", retailer="ALDI Süd",
            category=clean_text(category) or "Wochenangebote", name=name, brand="", description="",
            price=price, base_price=base_price, base_unit=base_unit,
            pack_signature=pack, validity_label=format_validity(start, end) if start or end else "Aktuelle Woche",
            match_key=build_match_key("", name, pack, f"aldi-sued:{identifier}"),
            source_url=product_url, image_url=image_url,
        )

    def _south_dom_offers(self, page: str, source_url: str) -> list[Offer]:
        parser = AldiSouthWeeklyParser(source_url)
        parser.feed(page)
        parser.close()
        parser.finish()
        text = strip_html(page)
        date_match = re.search(
            r"Angebote der aktuellen Woche.*?(\d{1,2})\.(\d{1,2})\.\s*[–-]\s*.*?(\d{1,2})\.(\d{1,2})\.",
            text,
            flags=re.IGNORECASE,
        )
        start: Optional[date] = None
        end: Optional[date] = None
        if date_match:
            sd, sm, ed, em = map(int, date_match.groups())
            today = offer_reference_date()
            candidates: list[tuple[date, date]] = []
            for sy in (today.year - 1, today.year, today.year + 1):
                ey = sy + (1 if em < sm else 0)
                try:
                    candidates.append((date(sy, sm, sd), date(ey, em, ed)))
                except ValueError:
                    pass
            current = next(((a, b) for a, b in candidates if a <= today <= b), None)
            if current:
                start, end = current
        return deduplicate_offers([
            offer
            for index, card in enumerate(parser.cards, start=1)
            if (offer := self._south_card_to_offer(card, start, end, index)) is not None
        ])

    def _south_page_offers(self, page: str, source_url: str) -> list[Offer]:
        payloads: list[Any] = []
        for match in re.finditer(
            r'<script[^>]*(?:type=["\'](?:application/ld\+json|application/json)["\']|id=["\']__NEXT_DATA__["\'])[^>]*>(.*?)</script>',
            page,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            try:
                payloads.append(json.loads(html.unescape(match.group(1))))
            except (json.JSONDecodeError, TypeError):
                continue
        offers: list[Offer] = []
        for payload in payloads:
            for node in walk_json(payload):
                offer = self._south_node_to_offer(node, source_url)
                if offer is not None:
                    offers.append(offer)
        offers.extend(self._south_dom_offers(page, source_url))
        return deduplicate_offers(offers)

    def _load_south(self) -> list[Offer]:
        queue = [self.SOUTH_INDEX_URL]
        seen: set[str] = set()
        collected: list[Offer] = []
        errors: list[str] = []
        pages: list[dict[str, Any]] = []
        while queue and len(seen) < 30:
            source_url = queue.pop(0)
            if source_url in seen:
                continue
            seen.add(source_url)
            try:
                page = self._south_get_html(source_url)
            except Exception as exc:
                errors.append(f"{urlsplit(source_url).path}: {type(exc).__name__}: {exc}")
                continue
            page_offers = self._south_page_offers(page, source_url)
            collected.extend(page_offers)
            pages.append({"url": source_url, "offers": len(page_offers), "bytes": len(page.encode("utf-8"))})
            for candidate in self._south_offer_urls(page):
                if candidate not in seen and candidate not in queue:
                    queue.append(candidate)
        self.last_south_pages = pages
        self.last_south_errors = errors
        offers = deduplicate_offers(collected)
        if not offers:
            raise ToolError("ALDI Süd lieferte keine lesbaren aktuell gültigen Angebote" + (": " + " | ".join(errors[-5:]) if errors else ""))
        return offers
