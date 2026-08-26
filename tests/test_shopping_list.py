from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "src/supermarkt/static/shopping-core.mjs").as_uri()


def js(expression: str):
    source = f"import * as m from {json.dumps(CORE)}; console.log(JSON.stringify({expression}))"
    result = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        check=True,
        capture_output=True,
        text=True,
        # node writes UTF-8. Without this the Windows default codec
        # fails on the checkbox character in the exported list.
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def test_integer_cent_totals_and_required_fixture():
    items = [
        {"name": "Milch", "quantity": 2, "retailer": "ALDI Nord", "price_cents": 129},
        {"name": "Butter", "quantity": 1, "retailer": "ALDI Nord", "price_cents": 149},
        {"name": "Kaffee", "quantity": 1, "retailer": "REWE", "price_cents": 499},
        {"name": "Energy", "quantity": 4, "retailer": "REWE", "price_cents": 79, "deposit_cents": 25},
        {"name": "Bad Pyrmonter", "quantity": 2, "retailer": "HOL’AB!", "price_cents": 555, "deposit_cents": 330},
    ]
    result = js(f"m.totals({json.dumps(items)})")
    assert result["goods_cents"] == 2332
    assert result["deposit_cents"] == 760
    assert result["total_cents"] == 3092
    assert result["unit_count"] == 10


def test_cent_regression_unknown_price_and_checked_stays_in_total():
    result = js("m.totals([{name:'A',quantity:1,price_cents:10,checked:true},{name:'B',quantity:1,price_cents:20},{name:'Brot',quantity:1,price_cents:null}])")
    assert result["goods_cents"] == 30
    assert result["unknown_price_count"] == 1


def test_offer_identity_increments_only_strict_identity():
    result = js("m.mergeItems([{name:'Milch',quantity:1,retailer:'REWE',offer_id:'one'}],[{name:'Milch',quantity:1,retailer:'REWE',offer_id:'one'},{name:'Milch Bio',quantity:1,retailer:'REWE',offer_id:'two'}])")
    assert len(result) == 2
    assert result[0]["quantity"] == 2


def test_buenting_offers_use_the_existing_canonical_shopping_model():
    result = js("""(()=>{
      const combi=m.offerToItem({offer_id:'combi-1',product:'Milch',retailer:'Combi',category:'Molkereiprodukte & Eier',pack:'1 l',regular_price:0.99});
      const famila=m.offerToItem({offer_id:'famila-1',product:'Brot',retailer:'famila Nordwest',category:'Backwaren',regular_price:null});
      const items=m.mergeItems([combi],[combi,famila]);
      return {items,totals:m.totals(items),text:m.exportText(items,new Date('2026-08-26T00:00:00Z'))};
    })()""")
    assert [(item["retailer"], item["quantity"]) for item in result["items"]] == [
        ("Combi", 2),
        ("famila Nordwest", 1),
    ]
    assert result["totals"]["goods_cents"] == 198
    assert result["totals"]["unknown_price_count"] == 1
    assert "Combi" in result["text"] and "famila Nordwest" in result["text"]


def test_text_parser_checkbox_quantity_prices_crlf_and_plain_text():
    sample = "ALDI Nord\r\n☐ 2× Milch 1 l | 1,29 € je\r\n[x] 4x Energy 0,5 l | 0,79 € je | +0,25 € Pfand je\r\n\r\nBrot"
    result = js(f"m.parseText({json.dumps(sample)})")
    assert len(result["valid"]) == 3
    assert result["valid"][0]["quantity"] == 2
    assert result["valid"][0]["price_cents"] == 129
    assert result["valid"][1]["checked"] is True
    assert result["valid"][1]["deposit_cents"] == 25
    assert result["valid"][2]["price_cents"] is None


def test_json_roundtrip_schema_and_separate_ids():
    result = js("m.validateDocument(m.exportDocument([{name:'Milch',quantity:2,unit:'Stück',pack:'1 l',offer_id:'offer-1',source_product_id:'source-2',ean:null,external_ids:{grocy:null}}]))[0]")
    assert result["local_item_id"] != result["offer_id"]
    assert result["offer_id"] == "offer-1"
    assert result["source_product_id"] == "source-2"
    assert result["ean"] is None


def test_import_limits_and_future_schema_are_rejected():
    assert js("(()=>{try{m.parseText('x'.repeat(m.MAX_IMPORT_BYTES+1));return false}catch{return true}})()") is True
    assert js("(()=>{try{m.validateDocument({schema_version:99,items:[]});return false}catch{return true}})()") is True


def test_shopping_frontend_keeps_the_list_local():
    shopping = (ROOT / "src/supermarkt/static/shopping.js").read_text(encoding="utf-8")
    assert "indexedDB.open" in shopping
    assert "XMLHttpRequest" not in shopping
    assert "localStorage" not in shopping
    assert "document.cookie" not in shopping
    assert "navigator.share" in shopping


def test_the_list_only_leaves_the_browser_when_the_user_sends_it():
    shopping = (ROOT / "src/supermarkt/static/shopping.js").read_text(encoding="utf-8")
    # The basket stays local. The only exceptions are reading the available
    # KitchenOwl lists, which carries no list content, and the send the user
    # asks for by clicking.
    calls = [line for line in shopping.splitlines() if "fetch(" in line]
    assert calls and all("koResultPath(" in line for line in calls), calls
    assert '$("kitchenowlSend").onclick=koSend' in shopping


def test_an_offer_reaches_kitchenowl_without_the_local_basket():
    results = (ROOT / "src/supermarkt/static/results-v2.js").read_text(encoding="utf-8")
    # One click from the offer, not a detour through the browser-local list.
    assert 'class="koSend"' in results
    assert "shoppingAdd" not in results
    assert 'koPath("items")' in results
