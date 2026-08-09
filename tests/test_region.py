import json

from supermarkt.http import HttpClient
from supermarkt.region import AldiRegionResolver


class FakeHttp(HttpClient):
    def __init__(self):
        super().__init__(5)
        self.calls = 0

    def get_bytes(self, url, headers=None):
        self.calls += 1
        if "postalcode=" in url:
            return json.dumps([{"lat": "51.05", "lon": "13.74"}]).encode()
        return json.dumps(
            [
                {
                    "lat": "51.051",
                    "lon": "13.741",
                    "display_name": "ALDI Nord",
                    "address": {"postcode": "01067"},
                    "namedetails": {"name": "ALDI Nord"},
                    "extratags": {"website": "https://www.aldi-nord.de/"},
                }
            ]
        ).encode()


def test_region_resolver_uses_single_bounded_path_and_cache():
    http = FakeHttp()
    resolver = AldiRegionResolver(http)
    # Resolver creates its own short-timeout HttpClient; replace it for deterministic fixture use.
    resolver.http = http
    assert resolver.detect("01067") == "nord"
    assert http.calls == 2
    assert resolver.detect("01067") == "nord"
    assert http.calls == 2
