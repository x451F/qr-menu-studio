"""Rendering and budget tests for the public menu templates."""

import gzip
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string

from menus.constants import ALLERGENS, DIETS, THEMES
from menus.models import Category, DailySpecial, Item, Restaurant
from public.menu_context import build_menu_context, load_restaurant
from public.templatetags.public_tags import _minify_css, hours_parts
from public.theming import THEME_FONTS

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def restaurant(db):
    r = Restaurant.objects.create(
        name="Chez Œuf", slug="chez-oeuf", tagline={"fr": "Cuisine de Œ", "en": "Cooking"},
        hours={"fr": "Mardi – Samedi : 12h – 14h\nFermé le lundi", "en": ""}, address="1 rue X\n19000 Tulle",
        phone="05 55 26 12 34", is_published=True, footer_note={"fr": "Prix nets", "en": ""},
    )
    DailySpecial.objects.create(restaurant=r, kind="plat", title={"fr": "Blanquette"}, prices=[{"cents": 1550}])
    c1 = Category.objects.create(restaurant=r, name={"fr": "Entrées", "en": "Starters"}, position=0)
    c2 = Category.objects.create(restaurant=r, name={"fr": "Vins", "en": "Wine"}, position=1)
    Item.objects.create(category=c1, name={"fr": "Œuf parfait"}, description={"fr": "Cèpes"}, prices=[{"cents": 1150}],
                        allergens=["eggs", "milk"], diets=["vegan"], position=0)
    Item.objects.create(category=c1, name={"fr": "Pâté"}, prices=[{"cents": 900}], position=1)
    Item.objects.create(category=c2, name={"fr": "Cahors"}, is_sold_out=True, position=0,
                        prices=[{"label": {"fr": "Verre"}, "cents": 550}, {"label": {"fr": "Bouteille"}, "cents": 2800}])
    return r


def _render(r, lang="fr", **kw):
    ctx = build_menu_context(load_restaurant(r.slug), lang, **kw)
    return render_to_string("public/menu.html", ctx)


@pytest.mark.parametrize("theme", list(THEMES))
@pytest.mark.parametrize("mode", ["auto", "light", "dark"])
def test_menu_renders_every_theme_and_mode(restaurant, theme, mode):
    html = _render(restaurant, theme=theme, mode=mode)
    assert f'data-theme="{theme}"' in html and f'data-mode="{mode}"' in html
    assert "{{" not in html and "{%" not in html
    assert html.count("<h1") == 1 and 'lang="fr"' in html
    assert "Œuf parfait" in html and "05 55 26 12 34" in html and 'href="tel:' in html
    assert 'id="dish-' in html and 'href="#cat-' in html and 'data-sold="1"' in html
    assert '<symbol id="al-eggs"' in html and '<symbol id="diet-vegan"' in html
    assert '<symbol id="al-gluten"' not in html  # only symbols in use are inlined
    assert "<dt>Mardi – Samedi</dt>" in html and "Fermé le lundi" in html
    assert 'name="robots"' not in html
    assert 'data-diet="vegan vegetarian"' in html  # vegan implies vegetarian for filtering


def test_preview_is_noindex_and_english(restaurant):
    assert 'content="noindex, nofollow"' in _render(restaurant, preview=True)
    en = _render(restaurant, "en")
    assert 'lang="en"' in en and "Sold out" in en


def test_rows_link_only_when_they_have_detail(restaurant):
    html = _render(restaurant)
    assert html.count('class="dish-link"') == 1  # only the row with a description/allergens
    assert 'data-photos="none"' in html and "dish-thumb" not in html.split("</style>")[-1]


def test_hours_parts():
    assert hours_parts("Mardi : 12h") == ("Mardi", "12h")
    assert hours_parts("Fermé le lundi") == ("", "Fermé le lundi")


def test_inline_css_and_js_budgets():
    for theme in THEMES:
        css = _minify_css(
            Path(finders.find("public/css/base.css")).read_text()
            + Path(finders.find(f"public/css/theme-{theme}.css")).read_text()
        )
        assert len(css.encode()) <= 16 * 1024, (theme, len(css))
        assert len(gzip.compress(css.encode())) <= 5 * 1024, theme
    assert len((ROOT / "static/public/js/menu.js").read_bytes()) <= 6 * 1024


def test_icon_sprite_covers_every_code():
    svg = (ROOT / "static/public/icons.svg").read_text()
    for code in ALLERGENS:
        assert f'id="al-{code}"' in svg
    for code in DIETS:
        assert f'id="diet-{code}"' in svg
    for name in ("search", "sliders", "close", "pin", "phone", "clock", "check"):
        assert f'id="ui-{name}"' in svg
    assert len(svg) < 9000


def test_font_files_exist_for_every_theme():
    fonts = ROOT / "static/public/fonts"
    for spec in THEME_FONTS.values():
        for _family, _w, _style, stem in spec["faces"]:
            for subset in ("latin", "latin-ext"):
                assert (fonts / f"{stem.format(s=subset)}.woff2").exists(), stem
