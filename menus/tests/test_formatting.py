import pytest

from menus.formatting import NBSP, NNBSP, format_price, format_prices, parse_price


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("12,50", 1250),
        ("12.5", 1250),
        ("12", 1200),
        ("12 €", 1200),
        ("12€50", 1250),
        ("12,50 €", 1250),
        ("€ 12,50", 1250),
        ("12,5", 1250),
        ("12.05", 1205),
        ("0,50", 50),
        ("0", 0),
        ("1 200,00", 120000),
        ("1.200,00", 120000),
        ("  8,50€ ", 850),
        ("8,50 EUR", 850),
        (12.5, 1250),
        (12, 1200),
        ("12,50 €".replace(" ", NBSP), 1250),
    ],
)
def test_parse_price_accepts(text, cents):
    assert parse_price(text) == cents


@pytest.mark.parametrize("text", [None, "", "   ", "abc", "12,505", "1,2,3", "12 euros", "--3", "€"])
def test_parse_price_rejects_garbage(text):
    assert parse_price(text) is None


def test_format_price_french():
    assert format_price(1250) == f"12,50{NBSP}€"
    assert format_price(5) == f"0,05{NBSP}€"
    assert format_price(0) == f"0,00{NBSP}€"
    assert format_price(120000) == f"1{NNBSP}200,00{NBSP}€"
    assert format_price(None) == ""


def test_format_price_roundtrip():
    for cents in (0, 5, 99, 100, 1250, 999999):
        assert parse_price(format_price(cents)) == cents


def test_format_prices_two_sizes_and_labels():
    prices = [
        {"label": {"fr": "25 cl", "en": "25 cl"}, "cents": 400},
        {"label": {"fr": "Bouteille", "en": "Bottle"}, "cents": 2800},
    ]
    assert format_prices(prices, "fr") == f"25 cl{NBSP}4,00{NBSP}€ / Bouteille{NBSP}28,00{NBSP}€"
    assert "Bottle" in format_prices(prices, "en")
    assert format_prices([{"cents": 850}]) == f"8,50{NBSP}€"
    assert format_prices([]) == ""
    assert format_prices(None) == ""
    assert format_prices([{"cents": None}, {"cents": 100}]) == f"1,00{NBSP}€"
