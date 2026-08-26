"""Pure helpers shared by the editor views (no HTTP concerns)."""

from __future__ import annotations

from django.db.models import Max

from menus.constants import ALLERGENS, DIETS
from menus.formatting import parse_price
from menus.models import Category, DailySpecial, Item, Restaurant

LANGS = ("fr", "en")

DEFAULT_FOOTER_NOTE = {"fr": "Prix nets, service compris.", "en": "Prices include service."}

CATEGORY_PRESETS = {
    "Entrées": "Starters",
    "Plats": "Mains",
    "Desserts": "Desserts",
    "Boissons": "Drinks",
    "Fromages": "Cheese",
    "Vins": "Wine",
}

LIMITS = {"name": 200, "description": 1200, "label": 60, "tagline": 200, "hours": 800, "footer": 400}


def clean_text(value, limit: int = 1200) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()[:limit]


def apply_tr(current, data, field: str, limit: int = 1200) -> dict:
    """Merge posted `<field>_fr` / `<field>_en` values into a translation dict."""
    value = {"fr": "", "en": ""}
    if isinstance(current, dict):
        value.update({k: v for k, v in current.items() if isinstance(v, str)})
    for lang in LANGS:
        key = f"{field}_{lang}"
        if key in data:
            value[lang] = clean_text(data[key], limit)
    return value


def parse_prices(data) -> tuple[list[dict], list[tuple[int, str]]]:
    """Read repeated `price_label_fr/en` + `price_amount` inputs.

    Returns (prices, errors) where errors = [(row_index, raw_text)]. Rows with an empty amount
    are ignored (a half-typed row must not raise errors while autosaving).
    """
    amounts = data.getlist("price_amount")
    labels_fr = data.getlist("price_label_fr")
    labels_en = data.getlist("price_label_en")
    prices, errors = [], []
    for i, raw in enumerate(amounts):
        raw = raw.strip()
        if not raw:
            continue
        cents = parse_price(raw)
        if cents is None:
            errors.append((i, raw))
            continue
        row: dict = {"cents": cents}
        label_fr = clean_text(labels_fr[i] if i < len(labels_fr) else "", LIMITS["label"])
        label_en = clean_text(labels_en[i] if i < len(labels_en) else "", LIMITS["label"])
        if label_fr or label_en:
            row["label"] = {"fr": label_fr, "en": label_en}
        prices.append(row)
    return prices, errors


def price_rows(prices) -> list[dict]:
    """Rows for the prices editor; always at least one (empty) row."""
    return list(prices or []) or [{}]


def prices_multi(prices) -> bool:
    prices = prices or []
    return len(prices) > 1 or any(p.get("label") and any(p["label"].values()) for p in prices)


def next_position(qs) -> int:
    top = qs.aggregate(m=Max("position"))["m"]
    return 0 if top is None else top + 1


def renumber(objs) -> None:
    objs = list(objs)
    for i, obj in enumerate(objs):
        obj.position = i
    if objs:
        type(objs[0]).objects.bulk_update(objs, ["position"])


def choose_codes(values, allowed) -> list[str]:
    seen = []
    for code in values:
        if code in allowed and code not in seen:
            seen.append(code)
    return seen


def chip_options(selected, catalogue) -> list[dict]:
    selected = set(selected or [])
    return [
        {"code": code, "label": names["en"], "selected": code in selected}
        for code, names in catalogue.items()
    ]


def allergen_options(item) -> list[dict]:
    return chip_options(item.allergens, ALLERGENS)


def diet_options(item) -> list[dict]:
    return chip_options(item.diets, DIETS)


def _missing(value) -> bool:
    if not isinstance(value, dict):
        return False
    return bool((value.get("fr") or "").strip()) and not (value.get("en") or "").strip()


def entry_missing_english(obj) -> bool:
    if isinstance(obj, DailySpecial):
        return _missing(obj.title) or _missing(obj.description)
    return _missing(obj.name) or _missing(obj.description)


def missing_english_count(restaurant: Restaurant) -> int:
    n = 0
    for cat in Category.objects.filter(restaurant=restaurant):
        n += entry_missing_english(cat)
    for item in Item.objects.filter(category__restaurant=restaurant).only("name", "description"):
        n += entry_missing_english(item)
    for sp in DailySpecial.objects.filter(restaurant=restaurant):
        n += entry_missing_english(sp)
    return n
