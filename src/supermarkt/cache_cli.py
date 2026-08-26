"""Inspect and clear the local caches.

KorbKlar keeps several caches with different lifetimes, and only the offer
snapshots expire quickly. This command makes the state visible and lets an
operator drop any of them:

```bash
python -m supermarkt.cache_cli status
python -m supermarkt.cache_cli purge --postal-code 26188
python -m supermarkt.cache_cli purge --all
```

Nothing here touches the signing secret: deleting that would invalidate every
result link that is still in circulation.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import time
from pathlib import Path

from .config import (
    CACHE_DB,
    CACHE_TTL_MINUTES,
    IMAGE_CACHE_DIR,
    KAUFLAND_CACHE_DIR,
    RESULT_RETENTION_HOURS,
    REWE_CACHE_DIR,
)

TABLE = "supermarket_snapshots"


def _connect(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    connection = sqlite3.connect(path, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection


def _directory_size(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    files = [item for item in path.rglob("*") if item.is_file()]
    return len(files), sum(item.stat().st_size for item in files)


def _drop_directory(path: Path, label: str) -> None:
    count, size = _directory_size(path)
    if not count:
        print(f"{label}: nichts zu löschen")
        return
    shutil.rmtree(path, ignore_errors=True)
    print(f"{label}: {count} Dateien entfernt ({size / 1024 / 1024:.1f} MiB)")


def status() -> int:
    print(f"Snapshot-Datenbank: {CACHE_DB}")
    connection = _connect(CACHE_DB)
    if connection is None:
        print("  (noch nicht angelegt)")
    else:
        now = time.time()
        with connection:
            rows = connection.execute(
                f"SELECT cache_key, created_at, fresh_until, expires_at FROM {TABLE} "
                "ORDER BY created_at DESC"
            ).fetchall()
        print(f"  {len(rows)} Snapshots")
        for row in rows:
            fresh = row["fresh_until"] > now
            age = int((now - row["created_at"]) / 60)
            state = "frisch" if fresh else "veraltet, wird neu geladen"
            print(f"    {row['cache_key']:>18}  {age:>4} Min alt  {state}")
        connection.close()

    print(f"\nFrische: {CACHE_TTL_MINUTES} Minuten")
    print(f"Ergebnislinks bleiben: {RESULT_RETENTION_HOURS} Stunden gültig")

    for label, path in (
        ("Bildcache", IMAGE_CACHE_DIR),
        ("REWE-Filialen", REWE_CACHE_DIR),
        ("Kaufland-Filialen", KAUFLAND_CACHE_DIR),
    ):
        count, size = _directory_size(path)
        print(f"{label}: {count} Dateien, {size / 1024 / 1024:.1f} MiB  ({path})")
    return 0


def purge(postal_code: str, images: bool, stores: bool, everything: bool) -> int:
    if everything:
        images = stores = True

    connection = _connect(CACHE_DB)
    if connection is None:
        print("Snapshot-Datenbank: nicht vorhanden")
    else:
        with connection:
            if postal_code:
                # The cache key is "<postal code>:<aldi region>".
                cursor = connection.execute(
                    f"DELETE FROM {TABLE} WHERE cache_key LIKE ?", (f"{postal_code}:%",)
                )
                scope = f"PLZ {postal_code}"
            else:
                cursor = connection.execute(f"DELETE FROM {TABLE}")
                scope = "alle PLZ"
            print(f"Snapshots gelöscht ({scope}): {cursor.rowcount}")
        # VACUUM cannot run inside the transaction the context manager opens.
        connection.isolation_level = None
        connection.execute("VACUUM")
        connection.close()

    if images:
        _drop_directory(IMAGE_CACHE_DIR, "Bildcache")
    if stores:
        _drop_directory(REWE_CACHE_DIR, "REWE-Filialen")
        _drop_directory(KAUFLAND_CACHE_DIR, "Kaufland-Filialen")

    print(
        "\nDer nächste Abruf lädt die betroffenen Quellen neu. "
        "Bereits verschickte Ergebnislinks der gelöschten Snapshots sind ungültig."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m supermarkt.cache_cli",
        description="Zeigt den Cache-Zustand oder leert ihn.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="zeigt Snapshots, Frische und Cachegrößen")

    clear = sub.add_parser("purge", help="löscht Snapshots und optional weitere Caches")
    clear.add_argument(
        "--postal-code",
        default="",
        help="nur diese PLZ; ohne Angabe werden alle Snapshots gelöscht",
    )
    clear.add_argument("--images", action="store_true", help="auch den Bildcache")
    clear.add_argument(
        "--stores", action="store_true", help="auch die REWE- und Kaufland-Filialzuordnungen"
    )
    clear.add_argument("--all", action="store_true", dest="everything", help="alles davon")

    args = parser.parse_args(argv)
    if args.command == "purge":
        postal_code = args.postal_code.strip()
        if postal_code and (len(postal_code) != 5 or not postal_code.isdigit()):
            parser.error("--postal-code muss aus genau fünf Ziffern bestehen")
        return purge(postal_code, args.images, args.stores, args.everything)
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
