from datetime import date

from supermarkt.common import deduplicate_offers
from supermarkt.http import HttpClient
from supermarkt.models import Offer
from supermarkt.sources.aldi import OfficialAldiSource


def source() -> OfficialAldiSource:
    return OfficialAldiSource(HttpClient(5))


def card(text: str, identifier: str = "000000000000123456", group: str = "") -> dict:
    return {
        "url": f"https://www.aldi-sued.de/produkt/test-artikel-{identifier}",
        "label": "Test Artikel 1 kg",
        "text_parts": [text, "1,29 €"],
        "group_label": group,
        "image_url": "",
    }


def test_normal_week_card_uses_global_period(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    offer = source()._south_card_to_offer(card("Test Artikel"), date(2026, 8, 24), date(2026, 8, 29), 1)
    assert offer is not None
    assert (offer.valid_from, offer.valid_until) == ("2026-08-24", "2026-08-29")
    assert offer.validity_label == "24.08. – 29.08.2026"


def test_friday_saturday_card_overrides_week(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    offer = source()._south_card_to_offer(card("Nur Fr/Sa"), date(2026, 8, 24), date(2026, 8, 29), 1)
    assert offer is not None
    assert (offer.valid_from, offer.valid_until) == ("2026-08-28", "2026-08-29")
    assert offer.validity_label == "Nur Fr. 28.08., Sa. 29.08."


def test_individual_action_days_are_preserved(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    offer = source()._south_card_to_offer(card("Mo, Do und Sa"), date(2026, 8, 24), date(2026, 8, 29), 1)
    assert offer is not None
    assert (offer.valid_from, offer.valid_until) == ("2026-08-24", "2026-08-29")
    assert offer.validity_label == "Nur Mo. 24.08., Do. 27.08., Sa. 29.08."


def test_group_period_is_used_before_week_fallback(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    offer = source()._south_card_to_offer(
        card("Test Artikel", group="Angebote ab Donnerstag 27.8."),
        date(2026, 8, 24), date(2026, 8, 29), 1,
    )
    assert offer is not None
    assert (offer.valid_from, offer.valid_until) == ("2026-08-27", "2026-08-29")


def test_loose_produce_price_with_base_unit_is_not_dropped(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    loose = card("Bio Hokkaido, lose")
    loose["text_parts"] = ["Bio Hokkaido, lose", "1,39 €", "/1 kg"]
    offer = source()._south_card_to_offer(
        loose,
        date(2026, 8, 24), date(2026, 8, 29), 1,
    )
    assert offer is not None
    assert offer.price == 1.39


def make_offer(label: str, start: str | None, end: str | None, *, price: float = 1.29, pack: str = "1kg") -> Offer:
    return Offer(
        offer_id="aldi-sued:123456", retailer="ALDI Süd", category="Weitere Angebote",
        name="Test Artikel", brand="", description="", price=price, base_price=None,
        base_unit="", pack_signature=pack, validity_label=label, match_key="test",
        source_url="https://www.aldi-sued.de/angebote", valid_from=start, valid_until=end,
    )


def test_duplicate_parser_find_prefers_precise_period():
    vague = make_offer("Aktuelle Woche", None, None)
    precise = make_offer("28.08. – 29.08.2026", "2026-08-28", "2026-08-29")
    result = deduplicate_offers([vague, precise])
    assert result == [precise]


def test_same_period_prefers_specific_day_label_over_generic_range():
    generic = make_offer("28.08. – 29.08.2026", "2026-08-28", "2026-08-29")
    specific = make_offer("Nur Fr. 28.08., Sa. 29.08.", "2026-08-28", "2026-08-29")
    assert deduplicate_offers([generic, specific]) == [specific]


def test_real_different_actions_prices_and_packs_remain():
    week = make_offer("24.08. – 29.08.2026", "2026-08-24", "2026-08-29")
    weekend = make_offer("28.08. – 29.08.2026", "2026-08-28", "2026-08-29")
    other_price = make_offer("28.08. – 29.08.2026", "2026-08-28", "2026-08-29", price=1.49)
    other_pack = make_offer("28.08. – 29.08.2026", "2026-08-28", "2026-08-29", pack="500g")
    assert deduplicate_offers([week, weekend, other_price, other_pack]) == [week, weekend, other_price, other_pack]


def test_dom_parser_attaches_nearest_offer_group(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    page = """
      <h2>Wochenangebote Mo., 24.8. – Sa., 29.8.</h2>
      <a href="/produkt/test-artikel-000000000000123456">Test Artikel 1 kg 1,29 €</a>
      <h2>Angebote zum Wochenende ab 28.8.</h2>
      <a href="/produkt/test-zwei-000000000000654321">Test Zwei 500 g 0,99 €</a>
    """
    offers = source()._south_dom_offers(page, "https://www.aldi-sued.de/angebote")
    assert [(offer.valid_from, offer.valid_until) for offer in offers] == [
        ("2026-08-24", "2026-08-29"),
        ("2026-08-28", "2026-08-29"),
    ]


def test_offer_crawl_keeps_current_action_days_not_old_or_theme_pages(monkeypatch):
    monkeypatch.setattr("supermarkt.sources.aldi.offer_reference_date", lambda: date(2026, 8, 26))
    page = """
      <a href="/angebote/2026-08-21">alt</a>
      <a href="/angebote/2026-08-24">Montag</a>
      <a href="/angebote/2026-08-27">Donnerstag</a>
      <a href="/angebote/2026-08-28?page=2">Freitag Seite 2</a>
      <a href="/angebote/2026-08-28?theme=Snacks">redundanter Themenfilter</a>
      <a href="/angebote/2026-08-31">nächste Woche</a>
      <a href="/produkte/wochenangebote/k/123">redundanter Parserweg</a>
    """
    assert source()._south_offer_urls(page) == [
        "https://www.aldi-sued.de/angebote/2026-08-24",
        "https://www.aldi-sued.de/angebote/2026-08-27",
        "https://www.aldi-sued.de/angebote/2026-08-28?page=2",
    ]
