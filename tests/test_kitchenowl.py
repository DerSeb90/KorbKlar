"""KitchenOwl shopping-list integration."""

import pytest
from fastapi.testclient import TestClient

from supermarkt import runtime
from supermarkt.access import result_token
from supermarkt.asgi import app
from supermarkt.kitchenowl import (
    KitchenOwlShoppingList,
    ShoppingListError,
    build_item_description,
    build_item_text,
    match_existing_item,
    shorten_offer_name,
)

SEARCH_ID = "synthetic-link-test"


class FakeKitchenOwl(KitchenOwlShoppingList):
    """A client whose only fake part is the HTTP call to KitchenOwl."""

    def __init__(self, households=None, lists=None, catalogue=None, **kwargs):
        kwargs.setdefault("base_url", "http://kitchenowl.local:8080")
        kwargs.setdefault("token", "long-lived-token")
        super().__init__(**kwargs)
        self.calls = []
        self.catalogue_items = catalogue if catalogue is not None else []
        self.stored_categories = []
        self.next_item_id = 100
        self.pending = []
        self.households = households if households is not None else [
            {"id": 1, "name": "Zuhause"},
        ]
        self.lists = lists if lists is not None else {
            1: [{"id": 4, "name": "Einkauf"}, {"id": 7, "name": "Getränke"}],
        }

    def _call(self, path, payload=None):
        self.calls.append((path, payload))
        if path == "/api/household":
            return self.households
        if path.endswith("/shoppinglist"):
            return self.lists.get(int(path.split("/")[3]), [])
        if path.endswith("/item"):
            return [{"id": index, "name": name} for index, name in enumerate(self.catalogue_items, 1)]
        if path.endswith("/category"):
            if payload is None:
                return list(self.stored_categories)
            created = {"id": 500 + len(self.stored_categories), "name": payload["name"]}
            self.stored_categories.append(created)
            return created
        if path.endswith("/items"):
            return list(self.pending)
        if path.endswith("add-item-by-name"):
            self.next_item_id += 1
            return {"id": self.next_item_id, "name": payload["name"]}
        return {}

    def written(self):
        """The add-item calls, as (name, description) pairs."""
        return [
            (payload["name"], payload.get("description", ""))
            for path, payload in self.calls
            if path.endswith("add-item-by-name")
        ]

    def category_calls(self):
        return [(path, payload) for path, payload in self.calls if path.startswith("/api/item/")]


@pytest.fixture
def fake_list(monkeypatch):
    service = FakeKitchenOwl()
    monkeypatch.setattr(runtime, "get_shopping_list", lambda: service)
    return service


@pytest.fixture
def client():
    return TestClient(app)


def _token():
    return result_token(SEARCH_ID)


# --------------------------------------------------------------- discovery


def test_every_list_of_every_household_is_offered(fake_list):
    assert [target["entity_id"] for target in fake_list.targets()] == ["4", "7"]


def test_a_single_household_does_not_clutter_the_labels(fake_list):
    assert [target["label"] for target in fake_list.targets()] == ["Einkauf", "Getränke"]


def test_several_households_qualify_their_lists():
    service = FakeKitchenOwl(
        households=[{"id": 1, "name": "Zuhause"}, {"id": 2, "name": "Büro"}],
        lists={1: [{"id": 4, "name": "Einkauf"}], 2: [{"id": 9, "name": "Einkauf"}]},
    )
    labels = [target["label"] for target in service.targets()]
    assert sorted(labels) == ["Büro · Einkauf", "Zuhause · Einkauf"]


def test_lists_are_cached_between_calls(fake_list):
    fake_list.targets()
    fake_list.targets()
    assert [path for path, _ in fake_list.calls].count("/api/household") == 1


def test_cached_targets_do_not_leak_the_household_id(fake_list):
    fake_list.targets()
    assert all(set(target) == {"entity_id", "label"} for target in fake_list.targets())


def test_a_token_without_households_is_reported():
    service = FakeKitchenOwl(households=[])
    with pytest.raises(ShoppingListError):
        service.targets()


def test_a_non_http_url_counts_as_unconfigured():
    # urlopen would happily read file:/ - a mistyped URL must not turn the
    # integration into a local file reader.
    assert KitchenOwlShoppingList(base_url="file:///etc/passwd", token="x").configured is False
    assert KitchenOwlShoppingList(base_url="", token="x").configured is False
    assert KitchenOwlShoppingList(base_url="http://kitchenowl-web", token="").configured is False


# ------------------------------------------------------------------ items


def test_item_uses_product_as_name_and_offer_details_as_note():
    assert build_item_text("Kerrygold Butter", "Combi") == "Kerrygold Butter"
    assert (
        build_item_description("famila Nordwest", "1,59 €", "bis 29.08.", "250 g")
        == "famila Nordwest · 1,59 € · 250 g · bis 29.08."
    )


def test_a_quantity_leads_the_note():
    # KitchenOwl has no amount field; the note is what it shows beside the
    # article, so more than one has to be visible there.
    assert build_item_description("Combi", "1,59 €", "", "", 3) == "3× · Combi · 1,59 €"


def test_a_single_unit_adds_no_quantity():
    assert build_item_description("Combi", "1,59 €", "", "", 1) == "Combi · 1,59 €"


def test_note_omits_details_the_offer_does_not_carry():
    assert build_item_description("Combi", "1,59 €", "", "") == "Combi · 1,59 €"


def test_adding_uses_the_add_item_by_name_endpoint(fake_list):
    result = fake_list.add_items(
        "4",
        [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €", "validity": "bis 29.08."}],
    )
    assert result["status"] == "ok"
    assert result["added_count"] == 1
    assert fake_list.written() == [("Kerrygold Butter", "1,59 € · bis 29.08.")]


def test_unknown_list_is_rejected_before_any_write(fake_list):
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("999", [{"product": "Butter"}])
    assert exc.value.status_code == 400
    assert all("add-item-by-name" not in path for path, _ in fake_list.calls)


def test_a_non_numeric_list_id_is_rejected(fake_list):
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("todo.bring_einkaufsliste", [{"product": "Butter"}])
    assert exc.value.status_code == 400


def test_configured_default_list_is_used_when_none_is_requested(fake_list):
    fake_list.default_list_id = "7"
    assert fake_list.add_items("", [{"product": "Butter"}])["entity_id"] == "7"


def test_quantity_reaches_the_written_note(fake_list):
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi", "quantity": 2}])
    assert fake_list.written() == [("Butter", "2×")]


def test_a_broken_quantity_falls_back_to_one(fake_list):
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi", "quantity": "viele"}])
    assert fake_list.written() == [("Butter", "")]


def test_the_retailer_stays_in_the_note_when_categories_are_off(fake_list):
    fake_list.retailer_categories = False
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi", "price_text": "1,59 €"}])
    assert fake_list.written() == [("Butter", "Combi · 1,59 €")]
    assert fake_list.category_calls() == []


def test_batch_size_is_capped(fake_list):
    fake_list.max_items = 2
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("4", [{"product": f"P{index}"} for index in range(3)])
    assert exc.value.status_code == 400


# ----------------------------------------------------------------- routes


def test_unconfigured_service_reports_disabled_instead_of_failing(monkeypatch, client):
    monkeypatch.setattr(
        runtime, "get_shopping_list", lambda: KitchenOwlShoppingList(base_url="", token="")
    )
    response = client.get(f"/results/{SEARCH_ID}/shopping-list/targets?token={_token()}")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "targets": [], "default_entity": ""}


def test_targets_route_answers_for_a_configured_service(fake_list, client):
    response = client.get(f"/results/{SEARCH_ID}/shopping-list/targets?token={_token()}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert [target["entity_id"] for target in payload["targets"]] == ["4", "7"]
    assert payload["default_entity"] == ""


def test_targets_route_reports_the_preselected_list(fake_list, client):
    fake_list.default_list_id = "7"
    payload = client.get(f"/results/{SEARCH_ID}/shopping-list/targets?token={_token()}").json()
    assert payload["default_entity"] == "7"


def test_browser_route_requires_a_valid_result_token(fake_list, client):
    response = client.post(
        f"/results/{SEARCH_ID}/shopping-list/items?token=wrong",
        json={"entity_id": "4", "items": [{"product": "Butter"}]},
    )
    assert response.status_code == 403
    assert all("add-item-by-name" not in path for path, _ in fake_list.calls)


def test_browser_route_adds_items_with_a_valid_result_token(fake_list, client):
    response = client.post(
        f"/results/{SEARCH_ID}/shopping-list/items?token={_token()}",
        json={
            "entity_id": "4",
            "items": [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["added"] == ["Kerrygold Butter"]


def test_rest_route_honours_the_optional_api_key(monkeypatch, fake_list, client):
    monkeypatch.setenv("SUPERMARKT_API_KEY", "secret-token")
    payload = {"entity_id": "4", "items": [{"product": "Butter"}]}
    assert client.post("/api/v1/shopping-list/items", json=payload).status_code == 401
    assert client.get("/api/v1/shopping-list/targets").status_code == 401
    assert client.get("/api/v1/shopping-list/entries?entity_id=4").status_code == 401

    authorized = client.post(
        "/api/v1/shopping-list/items",
        json=payload,
        headers={"Authorization": "Bearer secret-token"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["added_count"] == 1


def test_empty_item_list_is_rejected(fake_list, client):
    response = client.post(
        f"/results/{SEARCH_ID}/shopping-list/items?token={_token()}",
        json={"entity_id": "4", "items": []},
    )
    assert response.status_code == 400


def test_token_is_never_exposed_through_the_health_endpoint(monkeypatch, fake_list, client):
    class Store:
        def health(self):
            return {}

    class Images:
        def health(self):
            return {}

    class Engine:
        store = Store()

    monkeypatch.setattr(runtime, "get_engine", lambda: Engine())
    monkeypatch.setattr(runtime, "get_image_service", lambda: Images())
    payload = client.get("/health").json()["shopping_list"]
    assert payload["configured"] is True
    assert "long-lived-token" not in str(payload)
    assert payload["host"] == "kitchenowl.local:8080"


# ------------------------------------------------- matching and categories


CATALOGUE = ["Brötchen", "Butter", "Bio Butter", "Milch", "Joghurt", "Ei"]


def test_an_offer_lands_on_the_article_the_household_already_keeps():
    # German puts the head noun last, so this is what Brötchen is.
    assert match_existing_item("GUT&GÜNSTIG Weizenbrötchen / Schrippen", CATALOGUE) == "Brötchen"
    assert match_existing_item("Müller Joghurt mit der Ecke", CATALOGUE) == "Joghurt"


def test_the_more_specific_article_wins():
    assert match_existing_item("Kerrygold Bio Butter 250g", CATALOGUE) == "Bio Butter"


def test_a_compound_is_not_matched_by_its_first_half():
    # Buttermilch is milk, not butter; only the head noun may match.
    assert match_existing_item("Buttermilch 500g", CATALOGUE) == "Milch"


def test_very_short_articles_never_match():
    # "Ei" would otherwise swallow half a catalogue.
    assert match_existing_item("Eis am Stiel", CATALOGUE) == ""


def test_an_unknown_product_keeps_its_own_name():
    assert match_existing_item("Nektarinen", CATALOGUE) == ""


def test_a_matched_article_keeps_the_offer_name_in_the_note(monkeypatch):
    service = FakeKitchenOwl(catalogue=["Brötchen"])
    monkeypatch.setattr(runtime, "get_shopping_list", lambda: service)
    service.add_items("4", [{"product": "GUT&GÜNSTIG Weizenbrötchen", "retailer": "EDEKA", "price_text": "0,11 €"}])
    assert service.written() == [("Brötchen", "GUT&GÜNSTIG Weizenbrötchen · 0,11 €")]


def test_matching_can_be_switched_off(fake_list):
    """Without matching the article is still the staple, not the headline."""
    fake_list.catalogue_items = ["Brötchen"]
    fake_list.match_items = False
    fake_list.add_items("4", [{"product": "GUT&GÜNSTIG Weizenbrötchen", "retailer": "EDEKA"}])
    assert fake_list.written() == [("Weizenbrötchen", "GUT&GÜNSTIG Weizenbrötchen")]


@pytest.mark.parametrize(
    ("product", "expected"),
    [
        ("GUT&GÜNSTIG Weizenbrötchen / Schrippen", "Weizenbrötchen"),
        ("REWE Beste Wahl Orangen 1,5 kg", "Beste Wahl Orangen"),
        ("Bio Rinderhackfleisch aus der Region 400 g", "Bio Rinderhackfleisch"),
        ("Joghurt mild versch. Sorten 500 g", "Joghurt mild"),
        ("Coca-Cola 1,25 l", "Coca-Cola"),
        # Two plain words are already an article name.
        ("Kerrygold Butter", "Kerrygold Butter"),
        ("Eier", "Eier"),
    ],
)
def test_the_article_name_is_the_staple_not_the_leaflet_wording(product, expected):
    assert shorten_offer_name(product) == expected


def test_the_full_offer_wording_is_kept_in_the_note(fake_list):
    fake_list.catalogue_items = ["Brötchen"]
    fake_list.add_items(
        "4",
        [{
            "product": "GUT&GÜNSTIG Weizenbrötchen / Schrippen",
            "retailer": "EDEKA",
            "price_text": "0,11 €",
            "validity": "24.08. – 29.08.2026",
        }],
    )
    name, description = fake_list.written()[0]
    assert name == "Brötchen"
    assert "GUT&GÜNSTIG Weizenbrötchen / Schrippen" in description
    assert "0,11 €" in description and "24.08. – 29.08.2026" in description


def test_an_earlier_headline_in_the_catalogue_does_not_win(fake_list):
    """Offers filed under their full name must not capture matching.

    Being the longest match for the very offer that created them, they would
    beat the household's own article every time.
    """
    fake_list.catalogue_items = ["Brötchen", "GUT&GÜNSTIG Weizenbrötchen / Schrippen"]
    fake_list.add_items(
        "4", [{"product": "GUT&GÜNSTIG Weizenbrötchen / Schrippen", "retailer": "EDEKA"}]
    )
    assert fake_list.written()[0][0] == "Brötchen"


def test_a_compound_still_beats_its_head_noun():
    assert match_existing_item("ja! Buttermilch 1 l", ["Milch", "Buttermilch"]) == "Buttermilch"


def test_the_retailer_becomes_a_category_with_an_icon(fake_list):
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi"}])
    assert [entry["name"] for entry in fake_list.stored_categories] == ["🛒 Combi"]
    assert fake_list.category_calls() == [("/api/item/101", {"category": {"id": 500}})]


def test_an_existing_category_is_reused(fake_list):
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi"}])
    fake_list.add_items("4", [{"product": "Milch", "retailer": "Combi"}])
    assert len(fake_list.stored_categories) == 1


def test_an_offer_without_a_retailer_gets_no_category(fake_list):
    fake_list.add_items("4", [{"product": "Butter"}])
    assert fake_list.stored_categories == []


def test_a_failing_category_still_leaves_the_article_on_the_list(fake_list, monkeypatch):
    original = fake_list._call

    def flaky(path, payload=None):
        if path.startswith("/api/item/"):
            raise ShoppingListError("Kategorie abgelehnt")
        return original(path, payload)

    monkeypatch.setattr(fake_list, "_call", flaky)
    result = fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi"}])
    assert result["added_count"] == 1


def test_a_matched_article_is_not_repeated_in_its_own_note(fake_list):
    # A previous send may have created the article under this very name;
    # matching it then would print it twice.
    fake_list.catalogue_items = ["Ehrmann Almighurt"]
    fake_list.add_items("4", [{"product": "Ehrmann Almighurt", "retailer": "EDEKA", "price_text": "0,39 €"}])
    assert fake_list.written() == [("Ehrmann Almighurt", "0,39 €")]


def test_entries_report_what_is_currently_on_the_list(fake_list):
    fake_list.pending = [{"name": "Brötchen"}, {"name": "Milch"}]
    assert fake_list.entries("4") == ["Brötchen", "Milch"]


def test_entries_read_a_nested_item_name(fake_list):
    # The endpoint returns list entries, whose article may be nested.
    fake_list.pending = [{"item": {"name": "Butter"}}]
    assert fake_list.entries("4") == ["Butter"]


def test_the_entries_route_answers_for_the_browser(fake_list, client):
    fake_list.pending = [{"name": "Brötchen"}]
    response = client.get(
        f"/results/{SEARCH_ID}/shopping-list/entries?token={_token()}&entity_id=4"
    )
    assert response.status_code == 200
    assert response.json() == {"configured": True, "items": ["Brötchen"]}
