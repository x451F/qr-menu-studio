"""Price parsing/formatting. Prices are stored as integer cents and shown in French format."""

import re

from .i18n import tr

NBSP = " "
NNBSP = " "  # narrow no-break space, French thousands separator


def format_price(cents: int | None) -> str:
    """1250 -> '12,50 €'; 120000 -> '1 200,00 €'. Empty string for None."""
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    euros, rest = divmod(abs(int(cents)), 100)
    whole = f"{euros:,}".replace(",", NNBSP)
    return f"{sign}{whole},{rest:02d}{NBSP}€"


def format_prices(prices: list[dict] | None, lang: str = "fr") -> str:
    """[{'label': {'fr': '25 cl'}, 'cents': 850}, {'cents': 1400}] -> '25 cl 8,50 € / 14,00 €'."""
    parts = []
    for p in prices or []:
        if p.get("cents") is None:
            continue
        label = tr(p.get("label") or {}, lang)
        amount = format_price(p["cents"])
        parts.append(f"{label}{NBSP}{amount}" if label else amount)
    return " / ".join(parts)


_PRICE_RE = re.compile(r"^(?P<euros>\d{1,6})(?:\s*(?:[.,]|€)\s*(?P<cents>\d{1,2}))?$")


def parse_price(text: str | int | float | None) -> int | None:
    """Parse user input into cents. Accepts '12,50', '12.5', '12 €', '12€50', '12,50 €', 12.5.

    Returns None for empty or unparseable input.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return round(float(text) * 100)
    s = str(text).strip().replace(NBSP, " ").replace(NNBSP, " ").replace("EUR", "€").replace("eur", "€")
    s = s.strip()
    if not s:
        return None
    if s.endswith("€"):
        s = s[:-1].strip()
    if s.startswith("€"):
        s = s[1:].strip()
    # Remove thousands separators like "1 200,00" or "1.200,00".
    s = re.sub(r"(?<=\d)[ .](?=\d{3}(?:\D|$))", "", s)
    m = _PRICE_RE.match(s)
    if not m:
        return None
    euros = int(m.group("euros"))
    cents_str = m.group("cents") or "0"
    cents = int(cents_str) * (10 if len(cents_str) == 1 else 1)
    return euros * 100 + cents
