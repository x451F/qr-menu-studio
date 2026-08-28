import random
import re

import pytest

from menus.constants import THEMES
from public.theming import (
    CONTRAST_RULES,
    PALETTES,
    THEME_FONTS,
    build_theme_vars,
    contrast,
    hex_to_oklch,
    oklch_to_hex,
    sanitize,
)

HEX = re.compile(r"^#[0-9a-f]{6}$")
FIXED = [
    "#7a2e2a", "#2f5d50", "#000000", "#ffffff", "#ffff00", "#00ff00", "#ff00ff", "#0000ff", "#ff0000",
    "#808080", "#fafafa", "#050505", "#00ffff", "#ff8800", "#123", "#ABCDEF",
]
INVALID = ["", "red", "#12", "#gggggg", None, 42, "rgb(1,2,3)"]
RANDOM = [f"#{random.Random(i).randrange(0x1000000):06x}" for i in range(300)]
COLOR_KEYS = None


def _check(vars_):
    global COLOR_KEYS
    assert set(vars_) == {"light", "dark"}
    assert set(vars_["light"]) == set(vars_["dark"])
    for mode, d in vars_.items():
        for k, v in d.items():
            if k in ("--scrim", "--logo-bg", "--logo-pad"):
                continue
            assert HEX.match(v), (mode, k, v)
        for fg, bg, minimum in CONTRAST_RULES:
            ratio = contrast(d[fg], d[bg])
            assert ratio >= minimum, f"{mode} {fg} on {bg}: {ratio:.2f} < {minimum} ({d[fg]} / {d[bg]})"


@pytest.mark.parametrize("theme", list(THEMES))
def test_all_fixed_colors_are_aa(theme):
    for c in FIXED + INVALID:
        for accent in (None, "#e0a458", "#3366ff", c):
            _check(build_theme_vars(theme, c, accent))


@pytest.mark.parametrize("theme", list(THEMES))
def test_random_colors_are_aa(theme):
    for i, c in enumerate(RANDOM):
        _check(build_theme_vars(theme, c, RANDOM[-1 - i]))


@pytest.mark.parametrize("theme", list(THEMES))
def test_theme_defaults_are_aa(theme):
    _check(build_theme_vars(theme, PALETTES[theme]["brand"], PALETTES[theme]["accent"]))


def test_deterministic_and_unknown_theme_falls_back():
    assert build_theme_vars("bistro", "#7a2e2a", None) == build_theme_vars("bistro", "#7a2e2a", None)
    assert build_theme_vars("nope", "#7a2e2a", None) == build_theme_vars("bistro", "#7a2e2a", None)


def test_neon_is_tamed():
    for theme in THEMES:
        d = build_theme_vars(theme, "#00ff00", None)
        for mode in ("light", "dark"):
            assert hex_to_oklch(d[mode]["--brand"])[1] <= PALETTES[theme]["chroma_cap"] + 0.005


def test_accent_too_close_to_brand_uses_default():
    same = build_theme_vars("bistro", "#7a2e2a", "#7a2e2a")
    default = build_theme_vars("bistro", "#7a2e2a", None)
    assert same == default


def test_brand_hue_is_preserved():
    d = build_theme_vars("trattoria", "#2255cc", None)
    h_in = hex_to_oklch("#2255cc")[2]
    h_out = hex_to_oklch(d["light"]["--brand"])[2]
    assert abs(h_in - h_out) < 6


def test_sanitize_and_roundtrip():
    assert sanitize("ABC", "#000000") == "#aabbcc"
    assert sanitize("nope", "#111111") == "#111111"
    assert oklch_to_hex(*hex_to_oklch("#336699")) == "#336699"


def test_fonts_cover_all_themes():
    assert set(THEME_FONTS) == set(THEMES)
    for spec in THEME_FONTS.values():
        assert len({f[0] for f in spec["faces"]}) <= 2
