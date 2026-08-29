"""Print-ready PDFs (table stickers, table tents) rendered from HTML/CSS with WeasyPrint.

All geometry is computed here in millimetres and passed to the templates in
``templates/printing/pdf/`` so the CSS stays trivial (WeasyPrint has no ``calc()`` for
lengths). Designs are pure vector: inline SVG QR, embedded OFL fonts, logo as image.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from menus.i18n import tr

from .qr import make_qr_svg_inline, normalize_hex, safe_qr_color

FONTS_DIR = Path(__file__).resolve().parent.parent / "static" / "printing" / "fonts"

STICKER_SIZES_MM = (50, 70, 100)
STICKER_SHAPES = ("square", "round")
TENT_FORMATS = ("a5", "a6")
MAX_LINE_LEN = 70
MAX_STICKER_TEXT_LEN = 40

CTA_FR = "Scannez pour voir le menu"
CTA_EN = "Scan for the menu"

# Sticker sheet geometry (mm)
A4_W, A4_H = 210.0, 297.0
STICKER_GAP = 5.0
STICKER_PAGE_MARGIN_X = 10.0
STICKER_PAGE_MARGIN_Y = 12.0


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def clean_text(value: str | None, limit: int = MAX_LINE_LEN) -> str:
    """Single-line optional text from the query string, trimmed and length-limited."""
    return re.sub(r"\s+", " ", (value or "")).strip()[:limit]


def short_url(url: str) -> str:
    """``https://menu.example.fr/m/slug/`` -> ``menu.example.fr/m/slug`` (for humans)."""
    return re.sub(r"^https?://", "", url).rstrip("/")


def mix(color: str, other: str, amount: float) -> str:
    """Blend ``color`` towards ``other`` by ``amount`` (0..1)."""
    a, b = normalize_hex(color), normalize_hex(other)
    out = [
        round(int(a[i : i + 2], 16) * (1 - amount) + int(b[i : i + 2], 16) * amount)
        for i in (1, 3, 5)
    ]
    return "#{:02x}{:02x}{:02x}".format(*out)


def fit_font_pt(text: str, width_mm: float, max_lines: int, max_pt: float, min_pt: float) -> float:
    """Largest font size (pt, DM Serif Display) so ``text`` wraps to <= ``max_lines``."""
    pt = max_pt
    while pt > min_pt:
        char_w_mm = 0.5 * pt * 0.3528  # average advance ~0.5 em
        per_line = max(1, int(width_mm / char_w_mm))
        if math.ceil(len(text) / (per_line * 0.85)) <= max_lines:  # word wrap wastes ~15 %
            return round(pt, 1)
        pt -= 0.5
    return min_pt


def fit_url_pt(text: str, width_mm: float, max_pt: float = 10.0, min_pt: float = 7.0) -> float:
    """Font size (pt, Inter semibold ~0.58 em per character) so the URL fits on one line if possible."""
    pt = width_mm / (max(len(text), 1) * 0.58 * 0.3528)
    return round(max(min_pt, min(max_pt, pt)), 1)


@dataclass
class Brand:
    name: str
    logo_uri: str
    accent: str  # text / lines / fills carrying white text (>= 4.5:1 on white)
    tint: str  # very light wash of the brand colour
    qr_color: str  # >= 7:1 on white
    url: str = ""
    url_short: str = ""
    ink: str = "#1d1d1b"
    muted: str = "#5c5a55"


def _logo_uri(restaurant) -> str:
    if not restaurant.logo:
        return ""
    try:
        path = Path(restaurant.logo.path)
    except (ValueError, NotImplementedError):
        return ""
    return path.resolve().as_uri() if path.is_file() else ""


def build_brand(restaurant, color_mode: str = "brand") -> Brand:
    base = normalize_hex(restaurant.brand_color, "#7a2e2a")
    accent = safe_qr_color(base, "#ffffff", min_ratio=4.5)
    qr_color = safe_qr_color(base, "#ffffff") if color_mode == "brand" else "#000000"
    return Brand(
        name=restaurant.name,
        logo_uri=_logo_uri(restaurant),
        accent=accent,
        tint=mix(accent, "#ffffff", 0.93),
        qr_color=qr_color,
        url=restaurant.public_url,
        url_short=short_url(restaurant.public_url),
    )


def _base_context(restaurant, color_mode: str) -> dict:
    brand = build_brand(restaurant, color_mode)
    return {
        "brand": brand,
        "restaurant": restaurant,
        "tagline": clean_text(tr(restaurant.tagline, "fr"), 80),
        "qr_svg": make_qr_svg_inline(brand.url, brand.qr_color, "#ffffff"),
        "fonts_uri": FONTS_DIR.resolve().as_uri(),
        "cta_fr": CTA_FR,
        "cta_en": CTA_EN,
        "cta_fr_1": "Scannez pour",
        "cta_fr_2": "voir le menu",
    }


def html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML

    logging.getLogger("weasyprint").setLevel(logging.WARNING)

    return HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()


# --------------------------------------------------------------------------------------
# stickers
# --------------------------------------------------------------------------------------
def sticker_grid(size_mm: float) -> list[tuple[float, float]]:
    """Top-left corner (mm) of every sticker, centred on the A4 page."""
    usable_w = A4_W - 2 * STICKER_PAGE_MARGIN_X
    usable_h = A4_H - 2 * STICKER_PAGE_MARGIN_Y
    cols = max(1, int((usable_w + STICKER_GAP) // (size_mm + STICKER_GAP)))
    rows = max(1, int((usable_h + STICKER_GAP) // (size_mm + STICKER_GAP)))
    grid_w = cols * size_mm + (cols - 1) * STICKER_GAP
    grid_h = rows * size_mm + (rows - 1) * STICKER_GAP
    x0 = (A4_W - grid_w) / 2
    y0 = (A4_H - grid_h) / 2
    return [
        (x0 + c * (size_mm + STICKER_GAP), y0 + r * (size_mm + STICKER_GAP))
        for r in range(rows)
        for c in range(cols)
    ]


def _wrapped_lines(text: str, width_mm: float, pt: float) -> int:
    per_line = max(1, int(width_mm / (0.5 * pt * 0.3528)))
    return max(1, math.ceil(len(text) / (per_line * 0.85)))


def sticker_metrics(size_mm: float, shape: str, brand: Brand, text: str) -> dict:
    """All lengths in mm, font sizes in pt. The QR takes whatever height the stack leaves."""
    s = float(size_mm)
    round_ = shape == "round"
    pad = (0.10 if round_ else 0.07) * s
    gap = 0.022 * s
    inner_w = 0.56 * s if round_ else s - 2 * pad
    cta_w = 0.64 * s if round_ else s - 2 * pad
    cta_fr_pt = (0.115 if round_ else 0.13) * s
    cta_en_pt = (0.098 if round_ else 0.11) * s
    text_pt = (0.095 if round_ else 0.105) * s

    name_pt = fit_font_pt(brand.name, inner_w, 2, 0.24 * s, 0.10 * s)
    logo_h = (0.13 if round_ else 0.17) * s
    if brand.logo_uri:
        head_h = logo_h
    else:
        head_h = _wrapped_lines(brand.name, inner_w, name_pt) * name_pt * 0.3528 * 1.08
    cta_h = (cta_fr_pt + cta_en_pt) * 0.3528 * 1.2
    extra_h = (text_pt * 0.3528 * 1.15 * _wrapped_lines(text, cta_w, text_pt) + gap) if text else 0
    avail = s - 2 * pad - head_h - cta_h - extra_h - 2 * gap
    qr = min((0.56 if round_ else 0.64) * s, avail)
    return {
        "size": s,
        "pad": round(pad, 2),
        "qr": round(qr, 2),
        "logo_h": round(logo_h, 2),
        "inner_w": round(inner_w, 2),
        "cta_w": round(cta_w, 2),
        "name_pt": name_pt,
        "cta_fr_pt": round(cta_fr_pt, 1),
        "cta_en_pt": round(cta_en_pt, 1),
        "text_pt": round(text_pt, 1),
        "gap": round(gap, 2),
        "ring_inset": round(0.03 * s, 2),
        "ring_size": round(s - 0.06 * s, 2),
        "ring_radius": round(0.035 * s, 2),
        "guide": round(s + 1.2, 2),
        "far": round(s + 0.8, 2),
        "ring_w": round(max(0.3, 0.008 * s), 2),
        "radius": round(0.06 * s, 2),
        "round": round_,
    }


def render_stickers(
    restaurant,
    *,
    size_mm: int = 70,
    shape: str = "square",
    color_mode: str = "brand",
    text: str = "",
) -> bytes:
    if size_mm not in STICKER_SIZES_MM:
        size_mm = 70
    if shape not in STICKER_SHAPES:
        shape = "square"
    text = clean_text(text, MAX_STICKER_TEXT_LEN)
    ctx = _base_context(restaurant, color_mode)
    ctx.update(
        {
            "cells": [{"x": round(x, 2), "y": round(y, 2)} for x, y in sticker_grid(size_mm)],
            "m": sticker_metrics(size_mm, shape, ctx["brand"], text),
            "text": text,
            "size_cm": f"{size_mm / 10:g}",
            "shape": shape,
            "gap": STICKER_GAP,
        }
    )
    return html_to_pdf(render_to_string("printing/pdf/stickers.html", ctx))


# --------------------------------------------------------------------------------------
# table tents
# --------------------------------------------------------------------------------------
A6_SCALE = 0.70711  # A6 face = A5 face / sqrt(2)


def tent_metrics(brand: Brand, scale: float = 1.0) -> dict:
    """Metrics (mm / pt) for one face. Designed on A5 landscape (210 x 148.5 mm) and scaled
    for the A6 variant (148.5 x 105 mm) by multiplying every length instead of using CSS
    transforms (which WeasyPrint lays out unreliably inside flex boxes)."""
    k = scale

    def mm(v: float) -> float:
        return round(v * k, 2)

    left_w = 84.0
    qr = 74.0
    return {
        "w": mm(210),
        "h": mm(148.5),
        "top": mm(15),  # distance from the fold (the peak of the tent)
        "side": mm(12),
        "bottom": mm(12),
        "pad": mm(9.5),
        "radius": mm(7),
        "frame_w": round(0.7 * k, 2),
        "left_w": mm(left_w),
        "qr": mm(qr),
        "qr_radius": mm(4),
        "name_pt": round(fit_font_pt(brand.name, left_w, 4, 34, 18) * k, 1),
        "logo_h": mm(32),
        "logo_w": mm(left_w),
        "tag_pt": round(14 * k, 1),
        "tag_gap": mm(3.5),
        "rule_w": mm(16),
        "rule_h": mm(1.1),
        "rule_gap": mm(6),
        "cta_fr_pt": round(22 * k, 1),
        "cta_en_pt": round(14 * k, 1),
        "cta_en_gap": mm(1.5),
        "line_pt": round(14 * k, 1),
        "line_gap": mm(5),
        "url_pt": round(fit_url_pt(brand.url_short, qr) * k, 1),
        "url_gap": mm(3),
    }


def render_tent(
    restaurant,
    *,
    fmt: str = "a5",
    color_mode: str = "brand",
    line: str = "",
) -> bytes:
    if fmt not in TENT_FORMATS:
        fmt = "a5"
    ctx = _base_context(restaurant, color_mode)
    scale = A6_SCALE if fmt == "a6" else 1.0
    ctx.update({"m": tent_metrics(ctx["brand"], scale), "line": clean_text(line), "fmt": fmt})
    template = "printing/pdf/tent_a5.html" if fmt == "a5" else "printing/pdf/tent_a6.html"
    return html_to_pdf(render_to_string(template, ctx))
