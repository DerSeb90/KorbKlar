"""The service identifier is a wire contract with the app, not branding.

The Flutter app in ``app/`` is upstream's, unchanged. It only accepts a server
whose ``/health`` and ``/api/v1/client`` report ``service: korbunio``. Keep
that value when the fork naming (KorbKlar) is applied to a new upstream state.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from supermarkt import runtime
from supermarkt.asgi import app

ROOT = Path(__file__).resolve().parents[1]


def test_server_reports_the_service_identifier_the_app_accepts(monkeypatch):
    class Store:
        def health(self):
            return {}

    class Engine:
        store = Store()

    class Images:
        def health(self):
            return {}

    monkeypatch.setattr(runtime, "get_engine", lambda: Engine())
    monkeypatch.setattr(runtime, "get_image_service", lambda: Images())
    client = TestClient(app)
    assert client.get("/health").json()["service"] == "korbunio"
    assert client.get("/api/v1/client").json()["service"] == "korbunio"


def test_app_still_checks_for_that_identifier():
    source = (ROOT / "app/lib/api/client.dart").read_text(encoding="utf-8")
    assert source.count("['service'] != 'korbunio'") == 1
    assert source.count("['service'] == 'korbunio'") == 1
