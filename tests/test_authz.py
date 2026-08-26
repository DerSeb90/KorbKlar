"""Access control for a publicly reachable instance."""

import pytest
from fastapi.testclient import TestClient

from supermarkt import authz, config
from supermarkt.asgi import app

KEY = "correct-horse-battery-staple"
VPN = "10.8.0.0/24"
PROXY = "172.18.0.0/16"


def _client(peer: str = "203.0.113.9") -> TestClient:
    """A client whose requests appear to come from ``peer``."""
    return TestClient(app, client=(peer, 51000))


def _get(path="/", *, peer="203.0.113.9", forwarded=None, token=None):
    headers = {}
    if forwarded is not None:
        headers["X-Forwarded-For"] = forwarded
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return _client(peer).get(path, headers=headers)


@pytest.fixture
def public(monkeypatch):
    """An instance with a key, a VPN allowlist and a reverse proxy in front."""
    monkeypatch.setenv("SUPERMARKT_API_KEY", KEY)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", (VPN,))
    monkeypatch.setattr(config, "TRUSTED_PROXIES", (PROXY,))


@pytest.fixture
def keyed_only(monkeypatch):
    """A key, a VPN allowlist, but no reverse proxy is trusted."""
    monkeypatch.setenv("SUPERMARKT_API_KEY", KEY)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", (VPN,))
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ())


# ------------------------------------------------------------- open instance


def test_without_an_api_key_nothing_is_restricted(monkeypatch):
    monkeypatch.delenv("SUPERMARKT_API_KEY", raising=False)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", ())
    assert _get("/").status_code == 200


# ----------------------------------------------------------- token or network


def test_stranger_without_token_is_refused(public):
    response = _get("/")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_valid_token_is_accepted_from_anywhere(public):
    assert _get("/", token=KEY).status_code == 200


def test_wrong_token_is_refused(public):
    assert _get("/", token="wrong").status_code == 401


def test_client_inside_the_trusted_network_needs_no_token(public):
    assert _get("/", peer="10.8.0.5").status_code == 200


def test_address_just_outside_the_trusted_network_is_refused(public):
    assert _get("/", peer="10.8.1.5").status_code == 401


def test_every_route_is_gated_not_only_the_rest_api(public):
    for path in ("/", "/static/results.css", "/results/anything", "/image"):
        assert _get(path).status_code == 401, path


def test_rest_api_is_gated_too(public):
    response = _client().post("/api/v1/compare", json={"postal_code": "01067"})
    assert response.status_code == 401


# -------------------------------------------------------------- forwarded-for


def test_forwarded_header_from_a_trusted_proxy_identifies_the_client(public):
    assert _get("/", peer="172.18.0.7", forwarded="10.8.0.5").status_code == 200


def test_forwarded_header_from_an_untrusted_peer_is_ignored(public):
    # A stranger claiming a VPN address must not get in.
    assert _get("/", peer="203.0.113.9", forwarded="10.8.0.5").status_code == 401


def test_client_cannot_prepend_a_forged_hop(public):
    # The right-most entry is the one the trusted proxy itself appended, so a
    # value the client supplied earlier in the chain must not be believed.
    assert _get(
        "/", peer="172.18.0.7", forwarded="10.8.0.5, 203.0.113.9"
    ).status_code == 401


def test_chained_trusted_proxies_are_skipped(public):
    assert _get(
        "/", peer="172.18.0.7", forwarded="10.8.0.5, 172.18.0.9"
    ).status_code == 200


def test_unparsable_hop_breaks_the_chain(public):
    assert _get(
        "/", peer="172.18.0.7", forwarded="10.8.0.5, not-an-ip"
    ).status_code == 401


def test_forwarded_entry_with_a_port_is_still_matched(public):
    assert _get("/", peer="172.18.0.7", forwarded="10.8.0.5:44321").status_code == 200


def test_without_configured_proxies_the_header_is_ignored(keyed_only):
    assert _get("/", peer="172.18.0.7", forwarded="10.8.0.5").status_code == 401


# --------------------------------------------------------------------- health


def test_health_stays_reachable_for_container_checks(public):
    response = _get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "korbklar"}


def test_health_withholds_internals_from_an_unauthorised_caller(public):
    payload = _get("/health").json()
    for leaky in ("path", "sources", "trusted_networks", "snapshots"):
        assert leaky not in payload


def test_health_is_detailed_for_an_authorised_caller(public, monkeypatch):
    class Store:
        def health(self):
            return {}

    class Images:
        def health(self):
            return {}

    class Engine:
        store = Store()

    from supermarkt import runtime

    monkeypatch.setattr(runtime, "get_engine", lambda: Engine())
    monkeypatch.setattr(runtime, "get_image_service", lambda: Images())
    payload = _get("/health", token=KEY).json()
    assert payload["api_auth_configured"] is True
    assert payload["trusted_networks"] == [VPN]
    assert "sources" in payload


# -------------------------------------------------------------- configuration


def test_malformed_network_entry_does_not_widen_access(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_API_KEY", KEY)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", ("not-a-cidr",))
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ())
    assert _get("/", peer="10.8.0.5").status_code == 401


def test_a_single_host_may_be_listed_without_a_prefix(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_API_KEY", KEY)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", ("198.51.100.7",))
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ())
    assert _get("/", peer="198.51.100.7").status_code == 200
    assert _get("/", peer="198.51.100.8").status_code == 401


def test_ipv6_networks_are_supported(monkeypatch):
    monkeypatch.setenv("SUPERMARKT_API_KEY", KEY)
    monkeypatch.setattr(config, "TRUSTED_NETWORKS", ("2001:db8::/32",))
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ())
    assert _get("/", peer="2001:db8::1").status_code == 200
    assert _get("/", peer="2001:dba::1").status_code == 401


def test_token_comparison_does_not_accept_a_prefix_or_suffix(public):
    assert _get("/", token=KEY[:-1]).status_code == 401
    assert _get("/", token=KEY + "x").status_code == 401


def test_authorize_is_open_when_no_key_is_configured(monkeypatch):
    monkeypatch.delenv("SUPERMARKT_API_KEY", raising=False)
    assert authz.authorize("203.0.113.9", "", "") is True
