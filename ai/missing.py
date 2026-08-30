"""Fill every empty English field of a restaurant from its French text (batched)."""

from __future__ import annotations

from . import services

RESTAURANT_FIELDS = ("tagline", "hours", "footer_note")


def _tr_slots(restaurant):
    """Yield (obj, field, price_index) for every translatable slot of the restaurant."""
    for field in RESTAURANT_FIELDS:
        yield restaurant, field, None
    for cat in restaurant.categories.all():
        yield cat, "name", None
        yield cat, "description", None
        for item in cat.items.all():
            yield item, "name", None
            yield item, "description", None
            for idx in range(len(item.prices or [])):
                yield item, "prices", idx
    for sp in restaurant.specials.all():
        yield sp, "title", None
        yield sp, "description", None
        for idx in range(len(sp.prices or [])):
            yield sp, "prices", idx


def _value(obj, field, idx):
    if idx is None:
        value = getattr(obj, field)
    else:
        value = (getattr(obj, field)[idx] or {}).get("label")
    return value if isinstance(value, dict) else {}


def _store(obj, field, idx, value: dict):
    if idx is None:
        setattr(obj, field, value)
    else:
        getattr(obj, field)[idx]["label"] = value


def fill_missing_translations(restaurant) -> int:
    """Translate empty ``en`` fields from ``fr``; returns the number of fields filled.

    Raises ``services.AIUnavailable`` (nothing written) if the AI call fails.
    """
    pending = []
    for obj, field, idx in _tr_slots(restaurant):
        value = _value(obj, field, idx)
        fr = (value.get("fr") or "").strip()
        if fr and not (value.get("en") or "").strip():
            pending.append((obj, field, idx, fr))
    if not pending:
        return 0

    unique = list(dict.fromkeys(fr for *_, fr in pending))
    keyed = {f"t{i}": t for i, t in enumerate(unique)}
    translated = services.translate_texts(keyed, "fr", "en")
    by_text = {t: translated.get(f"t{i}", "") for i, t in enumerate(unique)}

    changed: dict[tuple, tuple] = {}
    filled = 0
    for obj, field, idx, fr in pending:
        en = by_text.get(fr, "").strip()
        if not en:
            continue
        value = dict(_value(obj, field, idx))
        value["fr"] = value.get("fr") or fr
        value["en"] = en
        _store(obj, field, idx, value)
        changed.setdefault((type(obj), obj.pk), (obj, set()))[1].add(field)
        filled += 1

    for obj, fields in changed.values():
        obj.save(update_fields=sorted(fields))
    restaurant.touch()
    return filled
