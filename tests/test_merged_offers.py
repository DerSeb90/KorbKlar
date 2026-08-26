"""Folding identical, equally priced offers from several retailers into one row.

Retail groups run one campaign across their brands, so the same product at the
same price appears once per brand. Those rows say the same thing and are
merged. Anything not proven identical stays separate.
"""

from dataclasses import asdict

from supermarkt.compare import OfferComparator
from supermarkt.models import Offer, RetailerContext, offer_retailers, offer_to_dict
from supermarkt.service import SupermarketEngine


def _offer(retailer: str, price: float, *, name: str = "Kerrygold Butter", pack: str = "250g") -> Offer:
    return Offer(
        offer_id=f"{retailer}:{name}:{price}",
        retailer=retailer,
        category="Molkereiprodukte",
        name=name,
        brand="Kerrygold",
        description="",
        price=price,
        base_price=None,
        base_unit="",
        pack_signature=pack,
        validity_label="Aktuell",
        match_key=f"kerrygold butter|{pack}" if pack else f"unique:{retailer}",
        source_url="",
    )


def _compare(offers, view="best_only"):
    return OfferComparator().compare(offers, (), view)


def test_same_product_same_price_becomes_one_row():
    result = _compare([_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)])
    assert len(result.offers) == 1
    assert result.offers[0].merged_retailers == ("Combi", "famila Nordwest")


def test_merged_row_keeps_the_price_untouched():
    result = _compare([_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)])
    assert result.offers[0].price == 1.59
    assert result.offers[0].effective_price == 1.59


def test_more_than_two_retailers_merge_into_one_row():
    result = _compare(
        [_offer("Combi", 1.59), _offer("famila Nordwest", 1.59), _offer("REWE", 1.59)]
    )
    assert len(result.offers) == 1
    assert result.offers[0].merged_retailers == ("Combi", "famila Nordwest", "REWE")


def test_different_prices_are_never_merged():
    result = _compare([_offer("Combi", 1.59), _offer("famila Nordwest", 1.79)], view="all")
    assert len(result.offers) == 2
    assert all(not offer.merged_retailers for offer in result.offers)


def test_a_cent_apart_stays_separate():
    result = _compare([_offer("Combi", 1.59), _offer("famila Nordwest", 1.60)], view="all")
    assert len(result.offers) == 2


def test_rounding_noise_below_half_a_cent_still_merges():
    result = _compare([_offer("Combi", 1.59), _offer("famila Nordwest", 1.592)])
    assert len(result.offers) == 1


def test_unmatched_products_are_never_merged_even_at_the_same_price():
    # Offers without a safe identity carry a unique match key. Merging those
    # would join genuinely different products.
    result = _compare(
        [
            _offer("Combi", 2.49, name="Orangen", pack=""),
            _offer("REWE", 2.49, name="Orangen", pack=""),
        ],
        view="all",
    )
    assert len(result.offers) == 2


def test_two_offers_from_one_retailer_are_not_merged():
    # Nothing to tell the shopper here; this is a duplicate, not a second
    # place to buy it.
    result = _compare([_offer("Combi", 1.59), _offer("Combi", 1.59)], view="all")
    assert all(not offer.merged_retailers for offer in result.offers)


def test_offers_without_a_price_stay_separate():
    result = _compare([_offer("Combi", None), _offer("famila Nordwest", None)], view="all")
    assert len(result.offers) == 2


def test_the_all_view_merges_equal_prices_but_keeps_dearer_ones():
    result = _compare(
        [
            _offer("Combi", 1.59),
            _offer("famila Nordwest", 1.59),
            _offer("REWE", 1.99),
        ],
        view="all",
    )
    assert len(result.offers) == 2
    merged = [offer for offer in result.offers if offer.merged_retailers]
    assert merged[0].merged_retailers == ("Combi", "famila Nordwest")


def test_a_single_offer_reports_its_own_retailer():
    offer = _offer("Combi", 1.59)
    assert offer_retailers(offer) == ("Combi",)


def test_merged_row_reports_every_retailer_it_stands_for():
    result = _compare([_offer("famila Nordwest", 1.59), _offer("Combi", 1.59)])
    assert offer_retailers(result.offers[0]) == ("Combi", "famila Nordwest")


def test_merged_retailers_are_ordered_and_deduplicated():
    result = _compare(
        [_offer("famila Nordwest", 1.59), _offer("Combi", 1.59), _offer("Combi", 1.59)]
    )
    assert result.offers[0].merged_retailers == ("Combi", "famila Nordwest")


# ---------------------------------------------------------------- page level


def _snapshot(offers):
    contexts = {
        name: RetailerContext(
            name=name,
            aliases=(name.casefold(),),
            excluded_aliases=(),
            color="#000",
            market_label=name,
            market_url="",
        )
        for name in {offer.retailer for offer in offers}
    }
    return {
        "search_id": "test",
        "postal_code": "26188",
        "created_at": 0,
        "offers": [offer_to_dict(offer) for offer in offers],
        "retailers": {name: asdict(value) for name, value in contexts.items()},
        "source_states": {},
        "request_errors": [],
        "store_warnings": [],
    }


def _page(offers, **kwargs):
    # page() only needs the comparator, so the SQLite store is not built here.
    engine = SupermarketEngine.__new__(SupermarketEngine)
    engine.comparator = OfferComparator()
    return SupermarketEngine.page(engine, _snapshot(offers), **kwargs)


def test_a_merged_row_is_found_under_every_retailer_it_lists():
    offers = [_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)]
    for name in ("Combi", "famila Nordwest"):
        page = _page(offers, retailer=name)
        assert page["filtered_offer_count"] == 1, name
        assert page["offers"][0]["retailers"] == ["Combi", "famila Nordwest"]


def test_chip_counts_credit_every_retailer_of_a_merged_row():
    page = _page([_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)])
    assert page["retailer_counts"] == {"Combi": 1, "famila Nordwest": 1}


def test_a_retailer_that_only_appears_merged_still_gets_a_chip():
    page = _page([_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)])
    assert "famila Nordwest" in page["retailer_counts"]


def test_response_exposes_a_ready_made_retailer_label():
    page = _page([_offer("Combi", 1.59), _offer("famila Nordwest", 1.59)])
    assert page["offers"][0]["retailer_label"] == "Combi · famila Nordwest"


def test_unmerged_rows_report_a_single_retailer():
    page = _page([_offer("Combi", 1.59)])
    assert page["offers"][0]["retailers"] == ["Combi"]
    assert page["offers"][0]["retailer_label"] == "Combi"
