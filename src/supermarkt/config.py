from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .version import __version__

BERLIN = ZoneInfo("Europe/Berlin")


def _default_data_dir() -> Path:
    state_home = os.getenv("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    current = base / "korbklar"
    legacy = base / "supermarkt-preisvergleich"
    if current.exists() or not legacy.exists():
        return current
    return legacy


def _env_text(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_path(name: str, default: Path) -> Path:
    # Resolved to an absolute path: a relative data directory would otherwise
    # be interpreted against the current working directory, and Chromium
    # refuses a relative --user-data-dir outright.
    return Path(_env_text(name, str(default))).expanduser().resolve()


def _env_int(name: str, default: int, minimum: int, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw is not None and raw.strip() else int(default)
    except (TypeError, ValueError):
        value = int(default)
    value = max(int(minimum), value)
    if maximum is not None:
        value = min(value, int(maximum))
    return value


DATA_DIR = _env_path("SUPERMARKT_DATA_DIR", _default_data_dir())
CACHE_DB = _env_path("SUPERMARKT_CACHE_DB", DATA_DIR / "supermarkt-cache.sqlite3")
SIGNING_SECRET_FILE = _env_path("SUPERMARKT_SIGNING_SECRET_FILE", DATA_DIR / ".signing-secret")
IMAGE_CACHE_DIR = _env_path("SUPERMARKT_IMAGE_CACHE_DIR", DATA_DIR / "supermarkt-images")
KAUFLAND_CACHE_DIR = _env_path("SUPERMARKT_KAUFLAND_CACHE_DIR", DATA_DIR / "kaufland")
REWE_CACHE_DIR = _env_path("SUPERMARKT_REWE_CACHE_DIR", DATA_DIR / "rewe")

KAUFLAND_STORE_CACHE_TTL_SECONDS = _env_int(
    "SUPERMARKT_KAUFLAND_STORE_CACHE_TTL_SECONDS", 86400, 300, 7 * 86400
)
REWE_STORE_CACHE_TTL_SECONDS = _env_int(
    "SUPERMARKT_REWE_STORE_CACHE_TTL_SECONDS", 86400, 300, 7 * 86400
)
IMAGE_CACHE_TTL_SECONDS = _env_int(
    "SUPERMARKT_IMAGE_CACHE_TTL_SECONDS", 604800, 3600, 30 * 86400
)
IMAGE_CACHE_MAX_BYTES = _env_int(
    "SUPERMARKT_IMAGE_CACHE_MAX_BYTES", 512 * 1024 * 1024, 16 * 1024 * 1024, 16 * 1024 * 1024 * 1024
)
IMAGE_MAX_FILE_BYTES = _env_int(
    "SUPERMARKT_IMAGE_MAX_FILE_BYTES", 4 * 1024 * 1024, 128 * 1024, 8 * 1024 * 1024
)
CACHE_TTL_MINUTES = _env_int("SUPERMARKT_CACHE_TTL_MINUTES", 30, 1, 1440)
CACHE_MAX_SNAPSHOTS = _env_int("SUPERMARKT_CACHE_MAX_SNAPSHOTS", 100, 4, 500)
RESULT_RETENTION_HOURS = _env_int("SUPERMARKT_RESULT_RETENTION_HOURS", 168, 1, 24 * 30)
TIMEOUT_SECONDS = _env_int("SUPERMARKT_TIMEOUT_SECONDS", 25, 5, 120)
MARKTGURU_PAGE_SIZE = _env_int("SUPERMARKT_MARKTGURU_PAGE_SIZE", 500, 100, 1000)
MAX_WORKERS = _env_int("SUPERMARKT_MAX_WORKERS", 8, 2, 24)

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on", "ja"}


def _env_list(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(item.strip() for item in raw.replace(";", ",").split(",") if item.strip())


# Access control. Both lists are empty by default, which keeps a private
# instance working exactly as before.
#
# TRUSTED_NETWORKS holds the client networks that may use the service without
# a bearer token, typically a VPN subnet. TRUSTED_PROXIES holds the reverse
# proxies whose X-Forwarded-For header may be believed; without it the header
# is ignored entirely, because anyone could otherwise claim a VPN address.
TRUSTED_NETWORKS = _env_list("SUPERMARKT_TRUSTED_NETWORKS")
TRUSTED_PROXIES = _env_list("SUPERMARKT_TRUSTED_PROXIES")

# Path to a Chromium-compatible browser for the Kaufland adapter. Empty means
# the well-known names and install locations are probed.
CHROMIUM_BINARY = _env_text("SUPERMARKT_CHROMIUM_BINARY", "")

# Home Assistant shopping-list integration. Disabled unless a base URL and a
# long-lived access token are configured. The target instance is normally a
# private or VPN address, so this client deliberately does not share the
# SSRF guard used for untrusted product images.
HOMEASSISTANT_URL = _env_text("SUPERMARKT_HA_URL", "").rstrip("/")
HOMEASSISTANT_TOKEN = _env_text("SUPERMARKT_HA_TOKEN", "")
HOMEASSISTANT_TODO_ENTITY = _env_text("SUPERMARKT_HA_TODO_ENTITY", "")
HOMEASSISTANT_VERIFY_TLS = _env_bool("SUPERMARKT_HA_VERIFY_TLS", True)
HOMEASSISTANT_TIMEOUT_SECONDS = _env_int("SUPERMARKT_HA_TIMEOUT_SECONDS", 15, 3, 60)
HOMEASSISTANT_MAX_ITEMS_PER_REQUEST = _env_int("SUPERMARKT_HA_MAX_ITEMS", 50, 1, 200)

MARKTGURU_HOME = "https://www.marktguru.de/"
MARKTGURU_SEARCH_API = "https://api.marktguru.de/api/v1/offers/search"
USER_AGENT = _env_text("SUPERMARKT_USER_AGENT", f"korb-klar/{__version__}")
SEARCH_TERMS = (
    "Obst", "Gemüse", "Fleisch", "Wurst", "Käse", "Milch", "Joghurt", "Butter", "Brot",
    "Backwaren", "Getränke", "Wasser", "Limonade", "Saft", "Bier", "Wein", "Kaffee", "Tee",
    "Tiefkühl", "Pizza", "Eis", "Süßigkeiten", "Schokolade", "Nudeln", "Reis", "Konserven",
    "Frühstück", "Gewürze", "Haushalt", "Waschmittel", "Reiniger", "Drogerie", "Kosmetik",
    "Tiernahrung", "Baby", "Freizeit", "Elektronik", "Garten", "Küche", "Textil", "Werkzeug",
)
