"""Import drafts: extraction -> editable draft dict -> form parsing -> database rows.

Draft ``data`` shape (JSON-serialisable, stored in ``ImportDraft.data``)::

    {
      "restaurant": {"name", "phone", "address", "hours"},          # detected, French
      "categories": [{"name", "description", "include", "items": [
          {"name", "description", "include", "allergens": [...], "diets": [...],
           "prices": [{"label", "text"}]}]}],
      "specials": [{"kind", "title", "description", "include", "prices": [...]}],
      "options": {"merge_existing", "import_specials", "translate", "info": {"phone", ...}},
    }

Prices stay as *text* in the draft; they are parsed with ``menus.formatting.parse_price`` when
the review screen is rendered (``annotate``) and again when saving (``apply_draft``).
"""

from __future__ import annotations

import copy
import unicodedata

from django.db import transaction

from menus.constants import ALLERGENS, DIETS, SPECIAL_KINDS
from menus.formatting import parse_price
from menus.i18n import tr
from menus.models import Category, DailySpecial, Item

from . import services

MAX_NAME = 200
MAX_TEXT = 1000
INFO_FIELDS = ("phone", "hours", "address")


class InvalidPrices(Exception):
    """Some included prices can't be parsed; the draft must be corrected first."""

    def __init__(self, count: int):
        super().__init__(f"{count} price(s) could not be read")
        self.count = count


def _s(value, limit=MAX_TEXT) -> str:
    return str(value or "").strip()[:limit]


def _prices_from_extraction(prices) -> list[dict]:
    return [
        {"label": _s(p.label, 60), "text": _s(p.price_text, 60)}
        for p in prices
        if _s(p.price_text, 60) or _s(p.label, 60)
    ]


# --------------------------------------------------------------------------------------
# extraction -> draft
# --------------------------------------------------------------------------------------
def menu_to_draft(menu) -> dict:
    """Convert an ``ExtractedMenu`` into the editable draft dict."""
    r = menu.restaurant
    return {
        "restaurant": {
            "name": _s(r.name, MAX_NAME),
            "phone": _s(r.phone, 30),
            "address": _s(r.address),
            "hours": _s(r.hours),
        },
        "categories": [
            {
                "name": _s(c.name, MAX_NAME),
                "description": _s(c.description),
                "include": True,
                "items": [
                    {
                        "name": _s(i.name, MAX_NAME),
                        "description": _s(i.description),
                        "include": True,
                        "allergens": [a for a in i.allergens if a in ALLERGENS],
                        "diets": [d for d in i.diets if d in DIETS],
                        "prices": _prices_from_extraction(i.prices),
                    }
                    for i in c.items
                ],
            }
            for c in menu.categories
        ],
        "specials": [
            {
                "kind": s.kind if s.kind in SPECIAL_KINDS else "plat",
                "title": _s(s.title, MAX_NAME),
                "description": _s(s.description),
                "include": True,
                "prices": _prices_from_extraction(s.prices),
            }
            for s in menu.specials
        ],
        "options": {
            "merge_existing": True,
            "import_specials": True,
            "translate": False,
            "info": {f: True for f in INFO_FIELDS},
        },
    }


def normalize_name(text: str) -> str:
    """Case/accent/whitespace-insensitive key used to match category names."""
    stripped = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in stripped if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())


def annotate(data: dict, restaurant) -> dict:
    """Return a deep copy of ``data`` with view helpers: bad-price flags, existing-category
    matches, counts and which detected info fields are importable."""
    d = copy.deepcopy(data)
    existing = {normalize_name(tr(c.name, "fr")): c for c in restaurant.categories.all()}
    bad_total = 0
    items_total = 0
    for ci, cat in enumerate(d["categories"]):
        match = existing.get(normalize_name(cat["name"]))
        cat["existing"] = bool(match)
        cat["key"] = f"c{ci}"
        for ii, item in enumerate(cat["items"]):
            item["key"] = f"c{ci}i{ii}"
            for p in item["prices"]:
                p["bad"] = bool(p["text"]) and parse_price(p["text"]) is None
                bad_total += p["bad"] and cat["include"] and item["include"]
            item["price_rows"] = item["prices"] + [{"label": "", "text": "", "bad": False}]
            item["chips"] = [ALLERGENS[a]["en"] for a in item["allergens"]] + [
                DIETS[x]["en"] for x in item["diets"]
            ]
            items_total += 1
    for si, sp in enumerate(d["specials"]):
        sp["key"] = f"s{si}"
        for p in sp["prices"]:
            p["bad"] = bool(p["text"]) and parse_price(p["text"]) is None
            bad_total += p["bad"] and sp["include"]
        sp["price_rows"] = sp["prices"] + [{"label": "", "text": "", "bad": False}]
    d["bad_prices"] = bad_total
    d["item_total"] = items_total
    d["info_available"] = importable_info(d["restaurant"], restaurant)
    return d


def importable_info(detected: dict, restaurant) -> dict[str, str]:
    """Detected contact fields that are non-empty in the draft and still empty on the restaurant."""
    out = {}
    if detected.get("phone") and not restaurant.phone.strip():
        out["phone"] = detected["phone"]
    if detected.get("address") and not restaurant.address.strip():
        out["address"] = detected["address"]
    if detected.get("hours") and not tr((restaurant.hours or {}), "fr").strip():
        out["hours"] = detected["hours"]
    return out


# --------------------------------------------------------------------------------------
# POST -> draft
# --------------------------------------------------------------------------------------
def _read_prices(post, prefix: str) -> list[dict]:
    prices, k = [], 0
    while f"{prefix}p{k}_text" in post or f"{prefix}p{k}_label" in post:
        label = _s(post.get(f"{prefix}p{k}_label"), 60)
        text = _s(post.get(f"{prefix}p{k}_text"), 60)
        if label or text:
            prices.append({"label": label, "text": text})
        k += 1
    return prices


def parse_post(post, draft: dict) -> dict:
    """Merge the review form into the draft structure (indices come from the stored draft)."""
    data = copy.deepcopy(draft)
    for ci, cat in enumerate(data["categories"]):
        cp = f"c{ci}"
        cat["include"] = f"{cp}_on" in post
        cat["name"] = _s(post.get(f"{cp}_name", cat["name"]), MAX_NAME)
        cat["description"] = _s(post.get(f"{cp}_desc", cat["description"]))
        for ii, item in enumerate(cat["items"]):
            ip = f"{cp}i{ii}"
            item["include"] = f"{ip}_on" in post
            item["name"] = _s(post.get(f"{ip}_name", item["name"]), MAX_NAME)
            item["description"] = _s(post.get(f"{ip}_desc", item["description"]))
            item["allergens"] = [a for a in post.getlist(f"{ip}_al") if a in ALLERGENS]
            item["diets"] = [x for x in post.getlist(f"{ip}_di") if x in DIETS]
            item["prices"] = _read_prices(post, ip)
    for si, sp in enumerate(data["specials"]):
        sp_ = f"s{si}"
        sp["include"] = f"{sp_}_on" in post
        kind = post.get(f"{sp_}_kind", sp["kind"])
        sp["kind"] = kind if kind in SPECIAL_KINDS else sp["kind"]
        sp["title"] = _s(post.get(f"{sp_}_title", sp["title"]), MAX_NAME)
        sp["description"] = _s(post.get(f"{sp_}_desc", sp["description"]))
        sp["prices"] = _read_prices(post, sp_)
    data["options"] = {
        "merge_existing": "opt_merge" in post,
        "import_specials": "opt_specials" in post,
        "translate": "opt_translate" in post,
        "info": {f: f"opt_info_{f}" in post for f in INFO_FIELDS},
    }
    return data


# --------------------------------------------------------------------------------------
# draft -> database
# --------------------------------------------------------------------------------------
def _included_items(cat: dict) -> list[dict]:
    return [i for i in cat["items"] if i["include"] and i["name"]]


def _included_specials(data: dict) -> list[dict]:
    if not data["options"].get("import_specials"):
        return []
    return [s for s in data["specials"] if s["include"] and s["title"]]


def collect_texts(data: dict) -> list[str]:
    """Unique French texts (in first-seen order) that will be imported, for translation."""
    seen: dict[str, None] = {}

    def add(text):
        if text and text.strip():
            seen.setdefault(text.strip(), None)

    for cat in data["categories"]:
        items = _included_items(cat) if cat["include"] else []
        if not items:
            continue
        add(cat["name"])
        add(cat["description"])
        for item in items:
            add(item["name"])
            add(item["description"])
            for p in item["prices"]:
                add(p["label"])
    for sp in _included_specials(data):
        add(sp["title"])
        add(sp["description"])
        for p in sp["prices"]:
            add(p["label"])
    return list(seen)


def translate_draft_texts(data: dict) -> dict[str, str]:
    """{french text: english text} for everything ``apply_draft`` will create. May raise
    ``services.AIUnavailable``."""
    texts = collect_texts(data)
    keyed = {f"t{i}": t for i, t in enumerate(texts)}
    translated = services.translate_texts(keyed, "fr", "en")
    return {t: translated.get(f"t{i}", "") for i, t in enumerate(texts)}


def count_bad_prices(data: dict) -> int:
    bad = 0
    for cat in data["categories"]:
        if not cat["include"]:
            continue
        for item in _included_items(cat):
            bad += sum(1 for p in item["prices"] if p["text"] and parse_price(p["text"]) is None)
    for sp in _included_specials(data):
        bad += sum(1 for p in sp["prices"] if p["text"] and parse_price(p["text"]) is None)
    return bad


def _price_rows(prices: list[dict], en: dict[str, str]) -> list[dict]:
    rows = []
    for p in prices:
        cents = parse_price(p["text"])
        if cents is None:
            continue
        rows.append(
            {"label": {"fr": p["label"], "en": en.get(p["label"], "") if p["label"] else ""}, "cents": cents}
        )
    return rows


def _tr_pair(text: str, en: dict[str, str]) -> dict:
    return {"fr": text, "en": en.get(text.strip(), "") if text.strip() else ""}


@transaction.atomic
def apply_draft(restaurant, data: dict, translations: dict[str, str] | None = None) -> dict:
    """Create categories/items/specials (+ optional info) from the draft. Returns stats.

    Raises ``InvalidPrices`` (nothing written) when an included price can't be parsed.
    """
    bad = count_bad_prices(data)
    if bad:
        raise InvalidPrices(bad)
    en = translations or {}
    opts = data["options"]

    existing = {}
    if opts.get("merge_existing"):
        for c in restaurant.categories.all():
            existing.setdefault(normalize_name(tr(c.name, "fr")), c)
    last_cat = restaurant.categories.order_by("-position").first()
    cat_position = (last_cat.position + 1) if last_cat else 0

    n_items = 0
    touched_categories = set()
    for cat in data["categories"]:
        items = _included_items(cat) if cat["include"] else []
        if not items or not cat["name"]:
            continue
        target = existing.get(normalize_name(cat["name"]))
        if target is None:
            target = Category.objects.create(
                restaurant=restaurant,
                name=_tr_pair(cat["name"], en),
                description=_tr_pair(cat["description"], en),
                position=cat_position,
            )
            cat_position += 1
            if opts.get("merge_existing"):
                existing[normalize_name(cat["name"])] = target
        last_item = target.items.order_by("-position").first()
        position = (last_item.position + 1) if last_item else 0
        for item in items:
            Item.objects.create(
                category=target,
                name=_tr_pair(item["name"], en),
                description=_tr_pair(item["description"], en),
                prices=_price_rows(item["prices"], en),
                allergens=item["allergens"],
                diets=item["diets"],
                position=position,
            )
            position += 1
            n_items += 1
        touched_categories.add(target.pk)

    n_specials = 0
    specials = _included_specials(data)
    if specials:
        last_sp = restaurant.specials.order_by("-position").first()
        sp_position = (last_sp.position + 1) if last_sp else 0
        for sp in specials:
            DailySpecial.objects.create(
                restaurant=restaurant,
                kind=sp["kind"],
                title=_tr_pair(sp["title"], en),
                description=_tr_pair(sp["description"], en),
                prices=_price_rows(sp["prices"], en),
                position=sp_position,
            )
            sp_position += 1
            n_specials += 1

    info_done = apply_info(restaurant, data)
    restaurant.touch()
    return {
        "items": n_items,
        "categories": len(touched_categories),
        "specials": n_specials,
        "info": info_done,
    }


def apply_info(restaurant, data: dict) -> list[str]:
    """Copy detected phone/address/hours into empty restaurant fields (only when ticked)."""
    detected = data["restaurant"]
    wanted = data["options"].get("info", {})
    available = importable_info(detected, restaurant)
    done, fields = [], []
    if wanted.get("phone") and "phone" in available:
        restaurant.phone = available["phone"][:30]
        fields.append("phone")
        done.append("phone")
    if wanted.get("address") and "address" in available:
        restaurant.address = available["address"]
        fields.append("address")
        done.append("address")
    if wanted.get("hours") and "hours" in available:
        current = dict(restaurant.hours or {})
        current["fr"] = available["hours"]
        current.setdefault("en", "")
        restaurant.hours = current
        fields.append("hours")
        done.append("hours")
    if fields:
        restaurant.save(update_fields=fields)
    return done
