from __future__ import annotations

import re
import unicodedata

from .common import clean_text

CATEGORIES = (
    "Obst & Gemüse", "Fleisch & Wurst", "Fisch & Meeresfrüchte",
    "Molkereiprodukte & Eier", "Backwaren", "Kühlprodukte", "Tiefkühlkost",
    "Vorräte & Grundnahrungsmittel", "Konserven & Fertiggerichte",
    "Frühstück & Brotaufstriche", "Getränke", "Süßwaren & Snacks",
    "Drogerie & Körperpflege", "Haushalt & Reinigung", "Tierbedarf",
    "Baby & Kind", "Wohnen, Freizeit & Non-Food", "Weitere Angebote",
)

_RULES = (
    ("Obst & Gemüse", r"obst|gemuese|gemüse|salat|kartoffel|tomat|apfel|banan"),
    ("Fleisch & Wurst", r"fleisch|wurst|schinken|salami|gefluegel|geflügel|hack"),
    ("Fisch & Meeresfrüchte", r"fisch|lachs|thunfisch|meeresfr|garnele"),
    ("Molkereiprodukte & Eier", r"molkerei|milch|kaese|käse|joghurt|quark|butter|eier"),
    ("Backwaren", r"backwaren|brot|broetchen|brötchen|kuchen|baeck|bäck"),
    ("Tiefkühlkost", r"tiefkuehl|tiefkühl|tk\b|eiscreme|speiseeis"),
    ("Kühlprodukte", r"kuehl|kühl|frische convenience|feinkost"),
    ("Konserven & Fertiggerichte", r"konserve|fertiggericht|instant|suppe|dose"),
    ("Frühstück & Brotaufstriche", r"fruehst|frühst|brotaufstrich|marmelade|honig|muesli|müsli|cerealien"),
    ("Getränke", r"getraenk|getränk|bier|wein|spirituose|wasser|saft|limonade|cola|kaffee|tee"),
    ("Süßwaren & Snacks", r"suess|süss|snack|schokolade|chips|keks|bonbon"),
    ("Drogerie & Körperpflege", r"drogerie|koerper|körper|pflege|hygiene|kosmetik|shampoo"),
    ("Haushalt & Reinigung", r"haushalt|reinigung|waschmittel|spuel|spül|papier|putz"),
    ("Tierbedarf", r"tier|hund|katze|haustier"),
    ("Baby & Kind", r"baby|kind|windel"),
    ("Wohnen, Freizeit & Non-Food", r"non.?food|wohnen|freizeit|garten|textil|mode|technik|werkzeug|spielzeug"),
    ("Vorräte & Grundnahrungsmittel", r"vorrat|grundnahr|nudel|reis|mehl|zucker|oel|öl|gewuerz|gewürz|sauce|backzutat"),
)

def _fold(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean_text(value)).casefold()
    return re.sub(r"[^\wäöüß]+", " ", value).strip()

def normalize_category(source_category: str, retailer: str = "", name: str = "", description: str = "") -> str:
    source = _fold(source_category)
    for canonical in CATEGORIES:
        if source == _fold(canonical):
            return canonical
    for canonical, pattern in _RULES:
        if re.search(pattern, source):
            return canonical
    # Product text is deliberately only a conservative fallback.
    fallback = _fold(f"{name} {description}")
    matches = [canonical for canonical, pattern in _RULES if re.search(pattern, fallback)]
    return matches[0] if len(set(matches)) == 1 else "Weitere Angebote"
