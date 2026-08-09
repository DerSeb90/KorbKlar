from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from supermarkt import security, ui, web
from supermarkt.asgi import app
from supermarkt.web import SupermarketRequest


class FakeEngine:
    snapshot_data = {
        "search_id": "synthetic-link-test",
        "postal_code": "01067",
        "created_at": 0,
    }

    def snapshot(self, postal_code, aldi_region, refresh):
        assert postal_code == "01067"
        return dict(self.snapshot_data), True

    def by_id(self, search_id):
        assert search_id == "synthetic-link-test"
        return dict(self.snapshot_data)

    def page(self, snapshot, **kwargs):
        return {
            "search_id": snapshot["search_id"],
            "postal_code": "01067",
            "offers": [],
            "page": 1,
            "page_count": 1,
            "has_next": False,
            "retailer_counts": {},
            "available_loyalty_programs": [],
        }


@pytest.fixture(autouse=True)
def fixed_signing_secret(monkeypatch):
    monkeypatch.setattr(security, "_CACHED_SECRET", b"test-signing-secret-0123456789-abcdef")
    monkeypatch.setattr(web, "get_engine", lambda: FakeEngine())
    monkeypatch.delenv("SUPERMARKT_API_KEY", raising=False)
    yield


def test_home_is_the_default_browser_entrypoint():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert '<form method="post" action="/search"' in response.text
    assert 'name="postal_code"' in response.text
    assert "Keine LLM erforderlich" in response.text
    assert 'href="/favicon.svg"' in response.text



def test_favicon_routes_are_local_and_cacheable():
    client = TestClient(app)
    for path in ("/favicon.svg", "/favicon.ico"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "max-age=86400" in response.headers["cache-control"]
        assert b"<svg" in response.content


def test_browser_search_requires_only_postal_code_and_redirects_to_results():
    client = TestClient(app)
    response = client.post("/search", data={"postal_code": "01067"}, follow_redirects=False)

    assert response.status_code == 303
    location = response.headers["location"]
    parsed = urlsplit(location)
    assert parsed.path == "/results/synthetic-link-test"
    assert len(parse_qs(parsed.query)["token"][0]) == 32


def test_browser_search_rejects_invalid_postal_code():
    client = TestClient(app)
    response = client.post("/search", data={"postal_code": "123"})

    assert response.status_code == 400
    assert "gültige fünfstellige" in response.text
    assert 'value="123"' in response.text


def test_results_page_accepts_signed_result_link():
    client = TestClient(app)
    path = web.build_result_path("synthetic-link-test", ("lidl_plus", "payback"))
    response = client.get(path)

    assert response.status_code == 200
    assert "Supermarkt-Preisvergleich" in response.text
    assert "Neue Suche" in response.text
    assert "/api/results/" in response.text
    assert "lidl_plus" in response.text
    assert "payback" in response.text
    assert 'href="/favicon.svg"' in response.text


def test_api_returns_exactly_one_absolute_result_url():
    client = TestClient(app, base_url="https://offers.example.test")
    response = client.post("/api/v1/compare", json={"postal_code": "01067"})

    assert response.status_code == 200
    result = response.json()
    url = result["result_url"]
    assert url.startswith("https://offers.example.test/results/synthetic-link-test?token=")
    assert "full_offer_list_url" not in result
    assert "ui_url" not in result
    assert "complete_offer_list" not in result
    assert sum(1 for key in result if key.endswith("_url") and key == "result_url") == 1


def test_api_result_url_preserves_multiple_loyalty_programs():
    client = TestClient(app, base_url="https://offers.example.test")
    response = client.post(
        "/api/v1/compare",
        json={
            "postal_code": "01067",
            "loyalty_programs": ["lidl_plus", "kaufland_xtra", "payback"],
        },
    )

    params = parse_qs(urlsplit(response.json()["result_url"]).query)
    assert params["loyalty"] == ["lidl_plus,kaufland_xtra,payback"]


def test_api_key_is_optional_but_enforced_when_configured(monkeypatch):
    client = TestClient(app)
    assert client.post("/api/v1/compare", json={"postal_code": "01067"}).status_code == 200

    monkeypatch.setenv("SUPERMARKT_API_KEY", "correct-key")
    assert client.post("/api/v1/compare", json={"postal_code": "01067"}).status_code == 401
    assert client.post(
        "/api/v1/compare",
        json={"postal_code": "01067"},
        headers={"Authorization": "Bearer correct-key"},
    ).status_code == 200


def test_signed_image_proxy_url():
    offer = {
        "retailer": "Lidl",
        "product": "Testprodukt",
        "image_url": "https://mg2de.b-cdn.net/api/v1/offers/24174643/images/default/0/medium.jpg",
        "source_url": "https://www.marktguru.de/",
    }

    proxy = web.build_image_proxy_url(offer)
    parsed = urlsplit(proxy)
    params = parse_qs(parsed.query)

    assert parsed.path == "/image"
    assert params["src"][0] == offer["image_url"]
    assert params["ref"][0] == "https://www.marktguru.de/"
    assert params["q"][0] == "Testprodukt"
    assert params["retailer"][0] == "Lidl"
    assert len(params["sig"][0]) == 32


def test_image_endpoint_returns_proxy_response(monkeypatch):
    from supermarkt.images import ImageResult

    class FakeImageService:
        def get(self, **kwargs):
            assert kwargs["source_url"].startswith("https://mg2de.b-cdn.net/")
            assert kwargs["referer"] == "https://www.marktguru.de/"
            assert kwargs["product"] == "Testprodukt"
            assert kwargs["retailer"] == "Lidl"
            return ImageResult(b"\xff\xd8\xfftest", "image/jpeg", "source")

    monkeypatch.setattr(web, "_image_service", FakeImageService())
    src = "https://mg2de.b-cdn.net/api/v1/offers/24174643/images/default/0/medium.jpg"
    ref = "https://www.marktguru.de/"
    sig = web.image_proxy_signature(src, ref, "Testprodukt", "Lidl")

    response = web.supermarket_image(src=src, ref=ref, q="Testprodukt", retailer="Lidl", sig=sig)

    assert response.media_type == "image/jpeg"
    assert response.body == b"\xff\xd8\xfftest"
    assert response.headers["x-supermarkt-image-origin"] == "source"


def test_request_rejects_unknown_loyalty_program():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SupermarketRequest(postal_code="01067", loyalty_programs=["nicht_echt"])


def test_openapi_exposes_only_the_optional_compare_api():
    schema = app.openapi()
    operations = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                operations.append((method.lower(), path, operation.get("operationId")))

    assert operations == [("post", "/api/v1/compare", "supermarkt_preisvergleich")]


def test_loyalty_ui_keeps_selection_in_browser_url():
    html = ui.build_results_html("search-id", "signature", ("lidl_plus", "payback"))

    assert "function syncLoyaltyUrl()" in html
    assert 'u.searchParams.set("loyalty",value)' in html
    assert 'u.searchParams.delete("loyalty")' in html
    assert 'history.replaceState(null,"",u)' in html
    assert "syncLoyaltyUrl();query(true)" in html


def test_infinite_scroll_does_not_show_page_counter():
    html = ui.build_results_html("search-id", "signature")
    assert "Weitere Angebote werden beim Scrollen geladen" in html
    assert "Seite ${{data.page}}" not in html
    assert "page_count}}</span>" not in html



def test_single_retailer_selection_hides_redundant_retailer_column():
    html = ui.build_results_html("search-id", "signature")
    assert '.table.single-retailer .retailer{display:none}' in html
    assert '<div class="retailer">Händler</div>' in html
    assert 'classList.toggle("single-retailer",Boolean(retailer))' in html


def test_health_reports_actual_source_priority(monkeypatch):
    class Store:
        def health(self):
            return {}

    class Engine:
        store = Store()

    class Images:
        def health(self):
            return {}

    monkeypatch.setattr(web, "get_engine", lambda: Engine())
    monkeypatch.setattr(web, "_image_service_instance", lambda: Images())
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert sources["REWE"].startswith("official primary")
    assert sources["EDEKA"].startswith("official primary")
    assert sources["Kaufland"].startswith("official primary")
    assert sources["Lidl"] == "Marktguru regional catalogue"
    assert sources["PENNY"] == "Marktguru regional catalogue"
    assert sources["Netto"] == "Marktguru regional catalogue"


def test_results_page_uses_duplicate_tabs_instead_of_view_select():
    client = TestClient(app)
    path = web.build_result_path("synthetic-link-test")
    response = client.get(path)

    assert response.status_code == 200
    assert 'id="viewBest"' in response.text
    assert 'id="viewAll"' in response.text
    assert "Teurere Dubletten einblenden" in response.text
    assert 'id="view"' not in response.text
