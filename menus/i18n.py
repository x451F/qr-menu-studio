"""Per-field translations are stored as dicts: {"fr": "Magret de canard", "en": "Duck breast"}."""

from .constants import DEFAULT_LANGUAGE


def tr(value, lang: str = DEFAULT_LANGUAGE) -> str:
    """Return the text for `lang`, falling back to French, then to any non-empty translation."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    text = (value.get(lang) or "").strip()
    if text:
        return text
    text = (value.get(DEFAULT_LANGUAGE) or "").strip()
    if text:
        return text
    for v in value.values():
        if v and str(v).strip():
            return str(v).strip()
    return ""


def has_translation(value, lang: str) -> bool:
    return bool(value and isinstance(value, dict) and (value.get(lang) or "").strip())
