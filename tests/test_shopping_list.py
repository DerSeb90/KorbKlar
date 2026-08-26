"""Home Assistant todo-list integration used for Bring shopping lists."""

import pytest
from fastapi.testclient import TestClient

from supermarkt import runtime
from supermarkt.access import result_token
from supermarkt.asgi import app
from supermarkt.homeassistant import (
    HomeAssistantShoppingList,
    ShoppingListError,
    build_item_description,
    build_item_text,
)

SEARCH_ID = "synthetic-link-test"


class FakeShoppingList(HomeAssistantShoppingList):
    """A client whose only fake part is the HTTP call to Home Assistant."""

    def __init__(self, states=None, **kwargs):
        kwargs.setdefault("base_url", "http://homeassistant.local:8123")
        kwargs.setdefault("token", "long-lived-token")
        super().__init__(**kwargs)
        self.calls = []
        self.states = states if states is not None else [
            {"entity_id": "todo.bring_einkaufsliste", "attributes": {"friendly_name": "Bring Einkaufsliste"}},
            {"entity_id": "todo.wocheneinkauf", "attributes": {"friendly_name": "Wocheneinkauf"}},
            {"entity_id": "light.kueche", "attributes": {"friendly_name": "Küche"}},
        ]

    def _call(self, path, payload=None):
        self.calls.append((path, payload))
        if path == "/api/states":
            return self.states
        return []


@pytest.fixture
def fake_list(monkeypatch):
    service = FakeShoppingList()
    monkeypatch.setattr(runtime, "get_shopping_list", lambda: service)
    return service


@pytest.fixture
def client():
    return TestClient(app)


def _token():
    return result_token(SEARCH_ID)


def test_only_todo_entities_are_offered_as_targets(fake_list):
    targets = fake_list.targets()
    assert [target["entity_id"] for target in targets] == [
        "todo.bring_einkaufsliste",
        "todo.wocheneinkauf",
    ]


def test_targets_are_cached_between_calls(fake_list):
    fake_list.targets()
    fake_list.targets()
    assert [path for path, _ in fake_list.calls].count("/api/states") == 1


def test_item_uses_product_as_name_and_offer_details_as_note():
    assert build_item_text("Kerrygold Butter", "Combi") == "Kerrygold Butter"
    assert (
        build_item_description("famila Nordwest", "1,59 €", "bis 29.08.", "250 g")
        == "famila Nordwest · 1,59 € · 250 g · bis 29.08."
    )


def test_note_omits_details_the_offer_does_not_carry():
    assert build_item_description("Combi", "1,59 €", "", "") == "Combi · 1,59 €"


def test_add_item_calls_the_home_assistant_todo_service(fake_list):
    result = fake_list.add_items(
        "todo.bring_einkaufsliste",
        [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €", "validity": "bis 29.08."}],
    )
    assert result["status"] == "ok"
    assert result["added_count"] == 1
    assert ("/api/services/todo/add_item", {
        "entity_id": "todo.bring_einkaufsliste",
        "item": "Kerrygold Butter",
        "description": "Combi · 1,59 € · bis 29.08.",
    }) in fake_list.calls


def test_unknown_entity_is_rejected_before_any_write(fake_list):
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("todo.does_not_exist", [{"product": "Butter"}])
    assert exc.value.status_code == 400
    assert all(path != "/api/services/todo/add_item" for path, _ in fake_list.calls)


def test_entity_id_from_another_domain_is_rejected(fake_list):
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("light.kueche", [{"product": "Butter"}])
    assert exc.value.status_code == 400


def test_configured_default_entity_is_used_when_none_is_requested(fake_list):
    fake_list.default_entity = "todo.wocheneinkauf"
    result = fake_list.add_items("", [{"product": "Butter"}])
    assert result["entity_id"] == "todo.wocheneinkauf"


def test_batch_size_is_capped(fake_list):
    fake_list.max_items = 2
    with pytest.raises(ShoppingListError) as exc:
        fake_list.add_items("todo.wocheneinkauf", [{"product": f"P{index}"} for index in range(3)])
    assert exc.value.status_code == 400


def test_unconfigured_service_reports_disabled_instead_of_failing(monkeypatch, client):
    monkeypatch.setattr(
        runtime, "get_shopping_list", lambda: HomeAssistantShoppingList(base_url="", token="")
    )
    response = client.get(f"/results/{SEARCH_ID}/shopping-list/targets?token={_token()}")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "targets": [], "default_entity": ""}


def test_browser_route_requires_a_valid_result_token(fake_list, client):
    response = client.post(
        f"/results/{SEARCH_ID}/shopping-list/items?token=wrong",
        json={"entity_id": "todo.wocheneinkauf", "items": [{"product": "Butter"}]},
    )
    assert response.status_code == 403
    assert all(path != "/api/services/todo/add_item" for path, _ in fake_list.calls)


def test_browser_route_adds_items_with_a_valid_result_token(fake_list, client):
    response = client.post(
        f"/results/{SEARCH_ID}/shopping-list/items?token={_token()}",
        json={
            "entity_id": "todo.bring_einkaufsliste",
            "items": [{"product": "Kerrygold Butter", "retailer": "Combi", "price_text": "1,59 €"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["added"] == ["Kerrygold Butter"]


def test_rest_route_honours_the_optional_api_key(monkeypatch, fake_list, client):
    monkeypatch.setenv("SUPERMARKT_API_KEY", "secret-token")
    payload = {"entity_id": "todo.wocheneinkauf", "items": [{"product": "Butter"}]}
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
        json={"entity_id": "todo.wocheneinkauf", "items": []},
    )
    assert response.status_code == 400


def test_token_is_never_exposed_through_the_health_endpoint(monkeypatch, fake_list, client):
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
    payload = client.get("/health").json()["shopping_list"]
    assert payload["configured"] is True
    assert "long-lived-token" not in str(payload)
    assert payload["host"] == "homeassistant.local:8123"
