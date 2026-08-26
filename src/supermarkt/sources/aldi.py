from __future__ import annotations

import html
import json
import logging
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
    parse_deposit_text,
    parse_iso_date,
    parse_number,
    strip_html,
    walk_json,
)
from ..config import TIMEOUT_SECONDS
from ..http import HttpClient
from ..images import is_rejected_image_url, normalize_image_url
from ..models import LoadResult, Offer, ToolError
from .browser import chromium_command

LOGGER = logging.getLogger(__name__)

class AldiSouthWeeklyParser(HTMLParser):
    """Produktkarten der offiziellen ALDI-SÜD-Wochenangebotsseiten."""

    IMAGE_ATTRS = ("data-src", "data-lazy-src", "data-original", "data-srcset", "srcset", "src")

    def __init__(self, source_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.cards: list[dict[str, Any]] = []
        self._current: Optional[dict[str, Any]] = None
        self._heading_tag = ""
        self._heading_parts: list[str] = []
        self._group_label = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = {str(key).casefold(): value or "" for key, value in attrs}
        tag = tag.casefold()
        if tag in {"h1", "h2", "h3", "h4", "h5"} and self._current is None:
            self._heading_tag = tag
            self._heading_parts = []
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
                    "group_label": self._group_label,
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
        if tag.casefold() == self._heading_tag:
            heading = clean_text(" ".join(self._heading_parts))
            if heading:
                self._group_label = heading
            self._heading_tag = ""
            self._heading_parts = []
        if tag.casefold() == "a" and self._current is not None:
            self._finish_current()

    def handle_data(self, data: str) -> None:
        if self._heading_tag and self._current is None:
            value = clean_text(data)
            if value:
                self._heading_parts.append(value)
            return
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

    @staticmethod
    def _south_global_period(text: str) -> tuple[Optional[date], Optional[date]]:
        match = re.search(
            r"Wochenangebote[^\d]{0,30}(?:Mo(?:ntag)?\.?[,]?\s*)?(\d{1,2})\.(\d{1,2})\.\s*[–-]\s*"
            r"(?:So|Sa|Fr|Do|Mi|Di|Mo)(?:ntag|nabend|itag|nnerstag|ttwoch|enstag)?\.?[,]?\s*"
            r"(\d{1,2})\.(\d{1,2})\.",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None, None
        sd, sm, ed, em = map(int, match.groups())
        today = offer_reference_date()
        candidates: list[tuple[date, date]] = []
        for sy in (today.year - 1, today.year, today.year + 1):
            try:
                candidates.append((date(sy, sm, sd), date(sy + (em < sm), em, ed)))
            except ValueError:
                continue
        return min(candidates, key=lambda period: abs((period[0] - today).days)) if candidates else (None, None)

    @staticmethod
    def _south_date_in_period(day: int, month: int, period: tuple[Optional[date], Optional[date]]) -> Optional[date]:
        start, end = period
        years = {offer_reference_date().year}
        if start:
            years.update({start.year, start.year + 1, start.year - 1})
        candidates: list[date] = []
        for year in years:
            try:
                candidates.append(date(year, month, day))
            except ValueError:
                pass
        if start and end:
            inside = [candidate for candidate in candidates if start <= candidate <= end]
            if inside:
                return inside[0]
        return min(candidates, key=lambda candidate: abs((candidate - offer_reference_date()).days)) if candidates else None

    @classmethod
    def _south_card_period(
        cls,
        card: dict[str, Any],
        global_period: tuple[Optional[date], Optional[date]],
    ) -> tuple[Optional[date], Optional[date], str]:
        """Resolve card > group > weekly validity without inventing missing dates."""
        text = clean_text(" ".join(card.get("text_parts") or []))
        group = clean_text(card.get("group_label"))
        start, end = global_period

        day_tokens = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}
        day_labels = {"mo": "Mo.", "di": "Di.", "mi": "Mi.", "do": "Do.", "fr": "Fr.", "sa": "Sa.", "so": "So."}
        special = re.search(
            r"(?:nur\s+)?((?:Mo|Di|Mi|Do|Fr|Sa|So)(?:\s*[/,]|\s+und\s+|\s+)+(?:Mo|Di|Mi|Do|Fr|Sa|So)(?:(?:\s*[/,]|\s+und\s+|\s+)+(?:Mo|Di|Mi|Do|Fr|Sa|So))*)",
            text,
            re.I,
        )
        if special and start:
            names = re.findall(r"Mo|Di|Mi|Do|Fr|Sa|So", special.group(1), re.I)
            dated_names = [(name, date.fromordinal(start.toordinal() + ((day_tokens[name.casefold()] - start.weekday()) % 7))) for name in names]
            if end:
                dated_names = [(name, value) for name, value in dated_names if value <= end]
            if dated_names:
                dates = [value for _name, value in dated_names]
                label = "Nur " + ", ".join(f"{day_labels[name.casefold()]} {value:%d.%m.}" for name, value in dated_names)
                return min(dates), max(dates), label

        explicit = re.search(r"Verfügbar\s+(?:seit|ab)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", text, re.I)
        if explicit:
            card_start = date(int(explicit.group(3)), int(explicit.group(2)), int(explicit.group(1)))
            card_end = end if end and card_start <= end else None
            return card_start, card_end, format_validity(card_start, card_end)

        group_date = re.search(r"(?:ab|zum\s+Wochenende\s+ab)\s+(?:Mo(?:ntag)?|Di(?:enstag)?|Mi(?:ttwoch)?|Do(?:nnerstag)?|Fr(?:eitag)?|Sa(?:mstag)?|So(?:nntag)?)?\s*(\d{1,2})\.(\d{1,2})\.", group, re.I)
        if group_date:
            group_start = cls._south_date_in_period(int(group_date.group(1)), int(group_date.group(2)), global_period)
            if group_start:
                return group_start, end if end and group_start <= end else None, format_validity(group_start, end if end and group_start <= end else None)
        return start, end, format_validity(start, end) if start or end else "Aktuelle Woche"

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
                    deposit=parse_deposit_text(description),
                )
            )
        if not offers:
            raise ToolError("ALDI Nord lieferte keine aktuell gültigen Angebote")
        return deduplicate_offers(offers)

    def _south_get_html(self, url: str) -> str:
        errors: list[str] = []
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.get(
                url,
                impersonate="chrome",
                timeout=TIMEOUT_SECONDS,
                allow_redirects=True,
                headers={"Accept-Language": "de-DE,de;q=0.9"},
            )
            response.raise_for_status()
            payload = response.content
            if len(payload) > 10 * 1024 * 1024:
                raise ToolError("ALDI Süd Antwort überschreitet das Größenlimit")
            if b"<html" in payload.lower():
                return payload.decode("utf-8", errors="replace")
            errors.append("curl_cffi: keine HTML-Antwort")
        except Exception as exc:
            errors.append(f"curl_cffi: {type(exc).__name__}: {exc}")
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
                        chromium_command(), headless, "--no-sandbox", "--disable-gpu",
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
        week_start = date.fromordinal(today.toordinal() - today.weekday())
        week_end = date.fromordinal(week_start.toordinal() + 5)
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
            keep = False
            match = re.fullmatch(r"/angebote/(\d{4}-\d{2}-\d{2})", path)
            if match:
                try:
                    offer_date = date.fromisoformat(match.group(1))
                except ValueError:
                    offer_date = None
                keep = bool(
                    offer_date
                    and week_start <= offer_date <= week_end
                    and (not parsed.query or re.fullmatch(r"page=\d+", parsed.query))
                )
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
            deposit=parse_deposit_text(description),
            valid_from=start.isoformat() if start else None,
            valid_until=end.isoformat() if end else None,
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
        price_matches = list(re.finditer(r"(\d{1,4}[,.]\d{2})\s*€", text))
        price_match = next((match for match in price_matches if not text[match.end():].lstrip().startswith("/")), None)
        # Loose produce commonly writes its selling price as ``1,39 € /1 kg``.
        # It is the price (not a base-price annotation) when no other candidate exists.
        price_match = price_match or (price_matches[0] if len(price_matches) == 1 else None)
        price = parse_number(price_match.group(1)) if price_match else None
        if price is None or price <= 0:
            return None
        resolved_start, resolved_end, validity_label = self._south_card_period(card, (start, end))
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
            pack_signature=pack, validity_label=validity_label,
            match_key=build_match_key("", name, pack, f"aldi-sued:{identifier}"),
            source_url=product_url, image_url=image_url,
            deposit=parse_deposit_text(text),
            valid_from=resolved_start.isoformat() if resolved_start else None,
            valid_until=resolved_end.isoformat() if resolved_end else None,
        )

    def _south_dom_offers(self, page: str, source_url: str) -> list[Offer]:
        parser = AldiSouthWeeklyParser(source_url)
        parser.feed(page)
        parser.close()
        parser.finish()
        text = strip_html(page)
        start, end = self._south_global_period(text)
        if start is None and end is None:
            match = re.fullmatch(r"/angebote/(\d{4}-\d{2}-\d{2})", urlsplit(source_url).path.rstrip("/"))
            if match:
                start = date.fromisoformat(match.group(1))
                week_start = date.fromordinal(start.toordinal() - start.weekday())
                end = date.fromordinal(week_start.toordinal() + 5)
        offers: list[Offer] = []
        for index, card in enumerate(parser.cards, start=1):
            offer = self._south_card_to_offer(card, start, end, index)
            if offer is None:
                path = urlsplit(clean_text(card.get("url"))).path
                LOGGER.warning("ALDI Süd Produktkarte %d konnte nicht verarbeitet werden (%s)", index, path[:240])
                continue
            offers.append(offer)
        return deduplicate_offers(offers)

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
