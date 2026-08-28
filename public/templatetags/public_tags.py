"""Template tags for the public menu."""

import re
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from public.theming import FALLBACKS, THEME_FONTS

register = template.Library()

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"\s*([{};])\s*")


def _minify_css(css: str) -> str:
    css = _COMMENT.sub("", css)
    css = _WS.sub(" ", css)
    css = _PUNCT.sub(r"\1", css)
    return css.replace(";}", "}").strip()


def _read_static(path: str) -> str:
    found = finders.find(path)
    if not found:
        raise FileNotFoundError(f"static file not found: {path}")
    with open(found, encoding="utf-8") as fh:
        return fh.read()


@lru_cache(maxsize=32)
def _cached_css(path: str) -> str:
    return _minify_css(_read_static(path))


@register.simple_tag
def inline_css(theme: str) -> str:
    """Base + theme CSS, minified, for an inline <style>. Read from the source tree."""
    parts = []
    for name in ("public/css/base.css", f"public/css/theme-{theme}.css"):
        parts.append(_minify_css(_read_static(name)) if settings.DEBUG else _cached_css(name))
    return mark_safe("".join(parts))  # noqa: S308 - our own static CSS


@register.simple_tag
def theme_vars_css(theme_vars: dict) -> str:
    """:root custom properties for light, and dark via media query / forced mode."""

    def block(d):
        return ";".join(f"{k}:{v}" for k, v in d.items())

    light, dark = theme_vars["light"], theme_vars["dark"]
    css = (
        f":root{{{block(light)}}}"
        f"@media(prefers-color-scheme:dark){{:root[data-mode=auto]{{{block(dark)}}}}}"
        f":root[data-mode=dark]{{{block(dark)}}}"
        ":root[data-mode=auto]{color-scheme:light dark}"
        ":root[data-mode=light]{color-scheme:light}:root[data-mode=dark]{color-scheme:dark}"
    )
    return mark_safe(css)  # noqa: S308 - values are validated hex/rgb from theming.py


@register.simple_tag
def font_css(theme: str) -> str:
    """@font-face rules (hashed static URLs) plus metric-matched fallback faces."""
    spec = THEME_FONTS[theme]
    out, seen = [], set()
    for family, weight, style, stem in spec["faces"]:
        for subset, rng in (
            ("latin", "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"),
            ("latin-ext", "U+0100-02AF,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2C60-2C7F,U+A720-A7FF"),
        ):
            url = static(f"public/fonts/{stem.format(s=subset)}.woff2")
            out.append(
                f'@font-face{{font-family:"{family}";font-style:{style};font-weight:{weight};font-display:swap;'
                f'src:url({url}) format("woff2");unicode-range:{rng}}}'
            )
        if family not in seen:
            seen.add(family)
            local, size, asc, desc, gap = FALLBACKS[family]
            out.append(
                f'@font-face{{font-family:"{family} Fallback";src:local("{local}");font-weight:100 900;'
                f"size-adjust:{size}%;ascent-override:{asc}%;descent-override:{desc}%;line-gap-override:{gap}%}}"
            )
    return mark_safe("".join(out))  # noqa: S308


@register.simple_tag
def font_preloads(theme: str) -> str:
    links = [
        format_html(
            '<link rel="preload" as="font" type="font/woff2" href="{}" crossorigin>',
            static(f"public/fonts/{stem}.woff2"),
        )
        for stem in THEME_FONTS[theme]["preload"]
    ]
    return mark_safe("".join(links))  # noqa: S308


@lru_cache(maxsize=1)
def _symbols() -> dict[str, str]:
    svg = _read_static("public/icons.svg")
    return {m.group(1): m.group(0) for m in re.finditer(r'<symbol id="([^"]+)".*?</symbol>', svg, re.S)}


def _symbols_now() -> dict[str, str]:
    if settings.DEBUG:
        _symbols.cache_clear()
    return _symbols()


UI_ICONS = ("ui-search", "ui-sliders", "ui-close", "ui-pin", "ui-phone", "ui-clock")


@register.simple_tag
def icon_sprite(menu) -> str:
    """Inline <svg> holding only the symbols this page uses (allergens, diets, UI)."""
    used = set(UI_ICONS)
    for t in list(menu.legend_allergens):
        used.add(f"al-{t.code}")
    for t in list(menu.legend_diets):
        used.add(f"diet-{t.code}")
    symbols = _symbols_now()
    body = "".join(symbols[i] for i in sorted(used) if i in symbols)
    return mark_safe(f'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" hidden aria-hidden="true">{body}</svg>')  # noqa: S308


@register.simple_tag
def photo_mode(menu) -> str:
    """none | some | all (>= 60% of dishes have a photo)."""
    total = with_photo = 0
    for cat in menu.categories:
        for it in cat.items:
            total += 1
            with_photo += 1 if it.photo else 0
    if not with_photo:
        return "none"
    return "all" if with_photo / max(total, 1) >= 0.6 else "some"


@register.simple_tag
def density(menu) -> str:
    return "few" if menu.item_count <= 8 else "many"


@register.filter
def codes(tags) -> str:
    return " ".join(t.code for t in tags)


@register.filter
def diet_codes(tags) -> str:
    """Vegan implies vegetarian for filtering."""
    c = [t.code for t in tags]
    if "vegan" in c and "vegetarian" not in c:
        c.append("vegetarian")
    return " ".join(c)


@register.filter
def hours_parts(line: str):
    """'Mardi – Samedi : 12h – 14h' -> ('Mardi – Samedi', '12h – 14h'); no ' : ' -> ('', line)."""
    if " : " in line:
        label, _, value = line.partition(" : ")
        return label.strip(), value.strip()
    return "", line


@register.filter
def has_detail(item) -> bool:
    """Rows with anything beyond name and price open the detail sheet (JS)."""
    return bool(item.description or item.photo or item.allergens or item.diets)


@register.filter
def var(mapping, key):
    return mapping.get(key, "")
