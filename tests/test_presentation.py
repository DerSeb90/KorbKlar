from supermarkt.models import Offer
from supermarkt.presentation import offer_for_response


def _offer(*, name="BLACK CAT Energy Drink", pack="4x250ml", deposit=1.0):
    return Offer(
        offer_id="black-cat", retailer="Netto Marken-Discount", category="Getränke",
        name=name, brand="BLACK CAT", description="4 x 0,25 Liter", price=1.99,
        base_price=None, base_unit="", pack_signature=pack, validity_label="Aktuell",
        match_key="black-cat|4x250ml", source_url="https://example.invalid/", deposit=deposit,
    )


def test_black_cat_four_pack_shows_deposit_per_can_and_pack_total():
    result = offer_for_response(_offer(), include_image_urls=False)
    assert result["deposit"] == 1.0
    assert result["deposit_text"] == "1,00 €"
    assert result["deposit_note"] == "Pfand: 0,25 € je Dose · 1,00 € gesamt für 4"


def test_single_container_keeps_simple_deposit_note():
    result = offer_for_response(_offer(pack="500ml", deposit=0.25), include_image_urls=False)
    assert result["deposit_note"] == "zzgl. 0,25 € Pfand"
