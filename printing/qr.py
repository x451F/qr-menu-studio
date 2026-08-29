"""QR code generation (segno) with a scannability guard for branded colours.

The QR always encodes the permanent public URL. Colour is only customisable within
limits: the foreground must keep a WCAG-style luminance contrast of at least
``MIN_CONTRAST`` (7:1) against the background, otherwise it is darkened (keeping the hue
as far as possible) so codes still scan reliably on cheap printers and in dim restaurants.
"""

from __future__ import annotations

import io
import re

import segno

MIN_CONTRAST = 7.0
QUIET_ZONE = 4  # modules; the QR spec minimum
ERROR_LEVEL = "q"  # ~25 % recovery; short URLs stay at a low version number
FALLBACK_DARK = "#111111"
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex(value: str | None, default: str = "#000000") -> str:
    """Return ``#rrggbb`` (lowercase); expands ``#rgb`` and falls back to ``default``."""
    value = (value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", value):
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value.lower() if HEX_RE.match(value) else default


def _to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = normalize_hex(hex_color)
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def relative_luminance(hex_color: str) -> float:
    def lin(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in _to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def safe_qr_color(
    color: str | None, background: str = "#ffffff", min_ratio: float = MIN_CONTRAST
) -> str:
    """Return a foreground colour that scans reliably on ``background``.

    - invalid / missing colour -> near-black
    - colour lighter than the background (inverted code) -> near-black
    - insufficient contrast -> blend towards black in small steps until ``min_ratio`` is met
    """
    color = normalize_hex(color, FALLBACK_DARK)
    background = normalize_hex(background, "#ffffff")
    if relative_luminance(color) >= relative_luminance(background):
        return FALLBACK_DARK if contrast_ratio(FALLBACK_DARK, background) >= min_ratio else "#000000"
    if contrast_ratio(color, background) >= min_ratio:
        return color
    r, g, b = _to_rgb(color)
    for step in range(1, 101):
        f = 1 - step / 100
        candidate = _to_hex((r * f, g * f, b * f))
        if contrast_ratio(candidate, background) >= min_ratio:
            return candidate
    return "#000000"


def resolve_color(mode: str | None, brand_color: str | None) -> str:
    """``mode`` is ``brand`` or ``black`` (query-string values)."""
    if mode == "brand":
        return safe_qr_color(brand_color)
    return "#000000"


def _make(url: str):
    return segno.make(url, error=ERROR_LEVEL, micro=False)


def make_qr_svg(
    url: str, color: str = "#000000", background: str = "#ffffff", *, border: int = QUIET_ZONE
) -> str:
    """Standalone SVG document (with XML declaration) for download."""
    color = safe_qr_color(color, background)
    buf = io.BytesIO()
    _make(url).save(
        buf,
        kind="svg",
        scale=10,
        border=max(border, QUIET_ZONE),
        dark=color,
        light=normalize_hex(background, "#ffffff"),
        xmldecl=True,
        svgns=True,
        nl=False,
    )
    return buf.getvalue().decode("utf-8")


def make_qr_svg_inline(
    url: str, color: str = "#000000", background: str | None = "#ffffff"
) -> str:
    """``<svg>`` element without a fixed size, ready to inline in HTML (scales with its box).

    ``background=None`` leaves the quiet zone transparent (use only on white paper/cards).
    """
    bg = normalize_hex(background, "#ffffff") if background else "#ffffff"
    color = safe_qr_color(color, bg)
    svg = _make(url).svg_inline(
        border=QUIET_ZONE,
        dark=color,
        light=bg if background else None,
        omitsize=True,
        scale=10,
    )
    return svg.replace("<svg ", '<svg shape-rendering="crispEdges" ', 1)


def make_qr_png(
    url: str,
    scale: int = 10,
    color: str = "#000000",
    background: str = "#ffffff",
    *,
    size_px: int | None = None,
) -> bytes:
    """PNG bytes. With ``size_px`` the integer module scale is chosen so the image is at least
    that many pixels wide (whole pixels per module keeps edges perfectly sharp)."""
    background = normalize_hex(background, "#ffffff")
    color = safe_qr_color(color, background)
    qr = _make(url)
    if size_px:
        modules = qr.symbol_size(border=QUIET_ZONE)[0]
        scale = max(1, -(-size_px // modules))
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=QUIET_ZONE, dark=color, light=background)
    return buf.getvalue()
