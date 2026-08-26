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
)

SEARCH_ID = "synthetic-link-test"


class FakeKitchenOwl(KitchenOwlShoppingList):
    """A client whose only fake part is the HTTP call to KitchenOwl."""

    def __init__(self, households=None, lists=None, **kwargs):
        kwargs.setdefault("base_url", "http://kitchenowl.local:8080")
        kwargs.setdefault("token", "long-lived-token")
        super().__init__(**kwargs)
        self.calls = []
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
            household_id = int(path.split("/")[3])
            return self.lists.get(household_id, [])
        return {}


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


def test_several_households_qualify_their_lists(monkeypatch):
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


def test_a_token_without_households_is_reported(monkeypatch):
    service = FakeKitchenOwl(households=[])
    with pytest.raises(ShoppingListError):
        service.targets()


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
    assert ("/api/shoppinglist/4/add-item-by-name", {
        "name": "Kerrygold Butter",
        "description": "Combi · 1,59 € · bis 29.08.",
    }) in fake_list.calls


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
    assert ("/api/shoppinglist/4/add-item-by-name", {
        "name": "Butter",
        "description": "2× · Combi",
    }) in fake_list.calls


def test_a_broken_quantity_falls_back_to_one(fake_list):
    fake_list.add_items("4", [{"product": "Butter", "retailer": "Combi", "quantity": "viele"}])
    assert ("/api/shoppinglist/4/add-item-by-name", {
        "name": "Butter",
        "description": "Combi",
    }) in fake_list.calls


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
    # The unconfigured branch alone left the configured one untested, which is
    # how a renamed attribute reached the route unnoticed.
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
