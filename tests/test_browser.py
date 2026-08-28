from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from supermarkt.asgi import app
from supermarkt import access, ui


def test_home_and_static_assets():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert 'name="postal_code"' in response.text
    assert 'name="aldi_region"' in response.text
    assert 'value="both"' in response.text
    assert 'href="/static/home.css"' in response.text
    assert 'src="/static/home-v2.js"' in response.text
    assert '<progress id="statusProgress"' in response.text
    assert "Welche Märkte möchtest du vergleichen?" in response.text
    assert response.text.count('name="retailers"') == 14
    assert 'value="Globus" checked' in response.text
    assert 'name="rewe_market_id"' in response.text
    assert client.get("/static/home.css").status_code == 200
    assert client.get("/static/results-v2.js").status_code == 200


def test_favicon_routes_are_local_and_cacheable():
    client = TestClient(app)
    for path in ("/favicon.svg", "/favicon.ico"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "max-age=86400" in response.headers["cache-control"]


def test_browser_search_and_invalid_postal_code():
    client = TestClient(app)
    response = client.post("/search", data={"postal_code": "01067"}, follow_redirects=False)
    assert response.status_code == 303
    parsed = urlsplit(response.headers["location"])
    assert parsed.path == "/results/synthetic-link-test"
    assert len(parse_qs(parsed.query)["token"][0]) == 32
    bad = client.post("/search", data={"postal_code": "123"})
    assert bad.status_code == 400
    assert 'value="123"' in bad.text


def test_results_page_uses_external_assets_and_data_attributes():
    client = TestClient(app)
    response = client.get(access.build_result_path("synthetic-link-test", ("lidl_plus", "payback")))
    assert response.status_code == 200
    assert 'src="/static/results-v2.js"' in response.text
    assert 'id="category"' in response.text
    assert 'data-search-id="synthetic-link-test"' in response.text
    assert 'data-loyalty="lidl_plus,payback"' in response.text


def test_ui_javascript_keeps_expected_behaviour():
    script = ui.static_text("results-v2.js")
    css = ui.static_text("results.css")
    assert "function syncLoyaltyUrl()" in script
    assert 'history.replaceState(null,"",url)' in script
    assert "Weitere Angebote werden beim Scrollen geladen" in script
    assert 'classList.toggle("single-retailer",Boolean(retailer))' in script
    assert 'category_counts' in script
    assert '.table.single-retailer .retailer{display:none}' in css


def test_home_offers_a_refresh_toggle():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert 'name="refresh"' in response.text
    assert 'type="checkbox"' in response.text


def test_search_job_route_passes_refresh_to_the_job_store(monkeypatch):
    from supermarkt import runtime

    recorded = {}

    class RecordingJobs:
        def start(self, postal_code, aldi_region="auto", refresh=False, retailers=(), rewe_market_id=""):
            recorded["value"] = refresh
            recorded["retailers"] = retailers
            return "job-id"

    monkeypatch.setattr(runtime, "get_jobs", lambda: RecordingJobs())
    client = TestClient(app)

    client.post("/search/jobs", data={"postal_code": "01067"})
    assert recorded["value"] is False

    client.post("/search/jobs", data={"postal_code": "01067", "refresh": "1"})
    assert recorded["value"] is True

    client.post("/search/jobs", data={"postal_code": "01067", "retailers": ["REWE", "Globus"]})
    assert recorded["retailers"] == ("REWE", "Globus")


def test_home_persists_retailer_selection_locally():
    script = ui.static_text("home-v2.js")
    assert "korbklar.selectedRetailers.v1" in script
    assert "localStorage.getItem(retailerStorageKey)" in script
    assert "localStorage.setItem(retailerStorageKey" in script
    assert "/rewe/markets?postal_code=" in script
    assert "korbklar.reweMarket." in script


def test_browser_rewe_market_lookup_returns_all_exact_matches(monkeypatch):
    from supermarkt import runtime

    class Rewe:
        def markets(self, postal_code):
            assert postal_code == "12345"
            return [
                {"market_id": "1", "market_url": "https://www.rewe.de/angebote/a/1/x/", "label": "REWE A"},
                {"market_id": "2", "market_url": "https://www.rewe.de/angebote/a/2/y/", "label": "REWE B"},
            ]

    engine = type("Engine", (), {"loader": type("Loader", (), {"official_rewe": Rewe()})()})()
    monkeypatch.setattr(runtime, "get_engine", lambda: engine)
    response = TestClient(app).get("/rewe/markets", params={"postal_code": "12345"})
    assert response.status_code == 200
    assert [market["market_id"] for market in response.json()["markets"]] == ["1", "2"]
