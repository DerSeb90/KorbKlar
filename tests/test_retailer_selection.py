from supermarkt.service import SupermarketEngine
from supermarkt.models import Offer
from supermarkt.service import SourceLoader


def test_retailer_selection_has_separate_deterministic_cache_keys():
    all_key = SupermarketEngine.cache_key("50677", "auto", ())
    one_key = SupermarketEngine.cache_key("50677", "auto", ("REWE",))
    several_a = SupermarketEngine.cache_key("50677", "auto", ("Globus", "REWE"))
    several_b = SupermarketEngine.cache_key("50677", "auto", ("REWE", "Globus"))
    assert all_key != one_key
    assert one_key != several_a
    assert several_a == several_b
    assert SupermarketEngine.cache_key("50677", "auto", ("REWE",), "123") != one_key


def _offer(retailer: str) -> Offer:
    return Offer(f"{retailer}:1", retailer, "Test", f"{retailer} Produkt", "", "", 1.0, None, "", "", "Aktuell", f"{retailer}:key", "https://example.invalid")


def test_source_loader_executes_only_selected_retailers():
    calls = []
    progress_events = []
    class Source:
        last_market_url = last_market_label = ""
        def __init__(self, retailer): self.retailer = retailer
        def load(self, postal):
            calls.append(self.retailer)
            return [_offer(self.retailer)]
    loader = SourceLoader.__new__(SourceLoader)
    loader.official_rewe = Source("REWE")
    loader.official_globus = Source("Globus")
    loader.aldi_region = type("Region", (), {"last_error": ""})()

    result = loader.load(
        "50677", "auto", retailers=("REWE", "Globus"),
        progress=lambda **event: progress_events.append(event),
    )

    assert set(calls) == {"REWE", "Globus"}
    assert {item["retailer"] for item in result["offers"]} == {"REWE", "Globus"}
    assert set(result["retailers"]) == {"REWE", "Globus"}
    totals = [event for event in progress_events if "total_sources" in event]
    assert totals[0]["total_sources"] == 2
    # Globus can add one image-only aggregator pass after its official
    # catalogue has been inspected.
    assert totals[-1]["total_sources"] == 3
    assert all(
        event.get("processed_sources", 0) <= totals[-1]["total_sources"]
        for event in progress_events
    )
