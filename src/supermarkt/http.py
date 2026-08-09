from __future__ import annotations

import json
import threading
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .common import clean_text
from .config import USER_AGENT
from .models import ToolError

class HttpClient:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = max(3, timeout_seconds)

    def get_bytes(self, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
        }
        request_headers.update(headers or {})
        request = Request(url, headers=request_headers)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            raise ToolError(f"HTTP {exc.code} bei {urlsplit(url).netloc}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ToolError(f"Abruf von {urlsplit(url).netloc} fehlgeschlagen: {exc}") from exc

    def get_json(self, url: str, headers: Optional[dict[str, str]] = None) -> dict[str, Any]:
        try:
            payload = json.loads(self.get_bytes(url, headers).decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise ToolError(f"Ungültige JSON-Antwort von {urlsplit(url).netloc}") from exc
        if not isinstance(payload, dict):
            raise ToolError(f"Unerwartete JSON-Antwort von {urlsplit(url).netloc}")
        return payload

class PostalCodeLocator:
    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def locality(self, postal_code: str) -> str:
        with self._lock:
            cached = self._cache.get(postal_code)
        if cached is not None:
            return cached

        query = urlencode(
            {
                "postalcode": postal_code,
                "country": "Germany",
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
            }
        )
        locality = ""
        try:
            payload = json.loads(
                self.http.get_bytes(
                    f"https://nominatim.openstreetmap.org/search?{query}",
                    {"Accept": "application/json"},
                ).decode("utf-8", errors="replace")
            )
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                address = payload[0].get("address")
                if isinstance(address, dict):
                    for field in ("city", "town", "municipality", "village", "county"):
                        locality = clean_text(address.get(field))
                        if locality:
                            break
        except Exception:
            locality = ""

        with self._lock:
            self._cache[postal_code] = locality
        return locality
