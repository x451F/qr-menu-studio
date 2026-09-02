"""Theme palettes and colour safety. See DESIGN.md section 4.

Contract: build_theme_vars(theme, brand_color, accent_color) -> {"light": {...}, "dark": {...}}
mapping CSS custom property names to values. Every colour a template uses as *text* or as a
*UI boundary* is derived here so that it meets WCAG AA against the surfaces it is drawn on:

    text on page/card ........ >= 4.5:1   (--ink, --ink-2, --brand-text, --accent-text)
    text on filled colour .... >= 4.5:1   (--on-brand on --brand, --on-accent on --accent)
    UI boundaries / icons .... >= 3.0:1   (--line-strong, --brand-ui, --accent-ui)

The maths is done in OKLCH (perceptually uniform lightness) and verified with the WCAG 2.x
relative-luminance contrast ratio. Pure Python, no dependencies, deterministic.
"""

from __future__ import annotations

import math
import re

from menus.constants import DEFAULT_THEME, THEMES

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
DARK_INK = "#12100e"

# --- Per-theme neutral bases (verified: ink >= 12.7:1, ink-2 >= 6.1:1, line-strong >= 3.0:1) -----
_N = ("bg", "surface", "ink", "ink2", "line", "line_strong")
PALETTES = {
    "bistro": {
        "light": dict(zip(_N, ("#f6f0e4", "#fbf8f1", "#211a17", "#5c4f47", "#d9cdb8", "#8f8170"), strict=True)),
        "dark": dict(zip(_N, ("#17120f", "#211a16", "#f1e8d8", "#b8aa98", "#3a2f27", "#7a6b5c"), strict=True)),
        "brand": "#7a2e2a", "accent": "#b8893a", "chroma_cap": 0.14, "tint": 0.03,
    },
    "trattoria": {
        "light": dict(zip(_N, ("#fff9ef", "#ffffff", "#2a1b14", "#66524a", "#ecdcc4", "#9a8572"), strict=True)),
        "dark": dict(zip(_N, ("#1c1310", "#281b16", "#fbeedd", "#c4ae9c", "#43312a", "#85705f"), strict=True)),
        "brand": "#b8412a", "accent": "#3d6b3a", "chroma_cap": 0.17, "tint": 0.03,
    },
    "cafe": {
        "light": dict(zip(_N, ("#faf6f0", "#ffffff", "#1f2a27", "#55605c", "#e6dfd2", "#7d8581"), strict=True)),
        "dark": dict(zip(_N, ("#14191a", "#1d2425", "#eef2ee", "#a9b5b0", "#2d3839", "#6f7d79"), strict=True)),
        "brand": "#2f5d50", "accent": "#e0a458", "chroma_cap": 0.15, "tint": 0.03,
    },
    "gastro": {
        "light": dict(zip(_N, ("#fbfaf7", "#fbfaf7", "#14130f", "#5a574f", "#e2ded4", "#8e8a80"), strict=True)),
        "dark": dict(zip(_N, ("#0d0d0c", "#141413", "#ece8df", "#a9a59b", "#2a2925", "#77746b"), strict=True)),
        "brand": "#6b5a3a", "accent": None, "chroma_cap": 0.08, "tint": 0.0,
    },
    "auberge": {
        "light": dict(zip(_N, ("#efe6d2", "#f8f1e1", "#2b2117", "#5e4f3d", "#d3c4a3", "#8a7859"), strict=True)),
        "dark": dict(zip(_N, ("#1b1610", "#251e15", "#efe4cd", "#b9a98c", "#3d3324", "#7d6d52"), strict=True)),
        "brand": "#5b6b3a", "accent": "#b5651d", "chroma_cap": 0.12, "tint": 0.03,
    },
}

# --- Fonts (Fontsource WOFF2 files vendored in static/public/fonts/) -----------------------------
# (family, weight, style, file stem).  `preload` = the faces above the fold (display, body, dish name).
THEME_FONTS = {
    "bistro": {
        "faces": [("Fraunces", 600, "normal", "fraunces-{s}-600-normal"),
                  ("Instrument Sans", 400, "normal", "instrument-sans-{s}-400-normal"),
                  ("Instrument Sans", 600, "normal", "instrument-sans-{s}-600-normal")],
        "preload": ["fraunces-latin-600-normal", "instrument-sans-latin-400-normal",
                    "instrument-sans-latin-600-normal"],
    },
    "trattoria": {
        "faces": [("Young Serif", 400, "normal", "young-serif-{s}-400-normal"),
                  ("Figtree", 400, "normal", "figtree-{s}-400-normal"),
                  ("Figtree", 600, "normal", "figtree-{s}-600-normal"),
                  ("Figtree", 700, "normal", "figtree-{s}-700-normal")],
        "preload": ["young-serif-latin-400-normal", "figtree-latin-400-normal", "figtree-latin-600-normal"],
    },
    "cafe": {
        "faces": [("Bricolage Grotesque", 700, "normal", "bricolage-grotesque-{s}-700-normal"),
                  ("Nunito Sans", 400, "normal", "nunito-sans-{s}-400-normal"),
                  ("Nunito Sans", 700, "normal", "nunito-sans-{s}-700-normal")],
        "preload": ["bricolage-grotesque-latin-700-normal", "nunito-sans-latin-400-normal",
                    "nunito-sans-latin-700-normal"],
    },
    "gastro": {
        "faces": [("Cormorant Garamond", 500, "normal", "cormorant-garamond-{s}-500-normal"),
                  ("Cormorant Garamond", 500, "italic", "cormorant-garamond-{s}-500-italic"),
                  ("Jost", 400, "normal", "jost-{s}-400-normal"),
                  ("Jost", 500, "normal", "jost-{s}-500-normal")],
        "preload": ["cormorant-garamond-latin-500-normal", "jost-latin-400-normal"],
    },
    "auberge": {
        "faces": [("Alegreya", 700, "normal", "alegreya-{s}-700-normal"),
                  ("Alegreya Sans", 400, "normal", "alegreya-sans-{s}-400-normal"),
                  ("Alegreya Sans", 700, "normal", "alegreya-sans-{s}-700-normal")],
        "preload": ["alegreya-latin-700-normal", "alegreya-sans-latin-400-normal"],
    },
}

# Metric-matched local fallbacks so the swap to the web font barely moves the layout.
# family -> (local font name, size-adjust %, ascent %, descent %, line-gap %); measured with fontTools (advance widths of a French sample vs Georgia/Arial).
FALLBACKS = {
    "Fraunces": ("Georgia", 109, 90, 23, 0),
    "Instrument Sans": ("Arial", 101, 96, 25, 0),
    "Young Serif": ("Georgia", 114, 91, 32, 0),
    "Figtree": ("Arial", 99, 96, 25, 0),
    "Bricolage Grotesque": ("Arial", 108, 86, 25, 0),
    "Nunito Sans": ("Arial", 100, 101, 35, 0),
    "Cormorant Garamond": ("Georgia", 88, 105, 33, 0),
    "Jost": ("Arial", 95, 112, 39, 0),
    "Alegreya": ("Georgia", 94, 109, 37, 0),
    "Alegreya Sans": ("Arial", 85, 106, 35, 0),
}


# --- Colour maths ----------------------------------------------------------------------------------
def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02x}" for v in (r, g, b))


def luminance(h: str) -> float:
    r, g, b = (_lin(v / 255) for v in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def hex_to_oklab(h: str) -> tuple[float, float, float]:
    r, g, b = (_lin(v / 255) for v in hex_to_rgb(h))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklab_to_lin(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_**3, m_**3, s_**3
    return (
        4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3,
        -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3,
        -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3,
    )


def oklab_to_hex(L: float, a: float, b: float) -> str:
    """Convert, gamut-mapping by reducing chroma at fixed lightness and hue."""
    lo, hi = 0.0, 1.0
    rgb = _oklab_to_lin(L, a, b)
    if any(v < -1e-4 or v > 1 + 1e-4 for v in rgb):
        for _ in range(14):
            mid = (lo + hi) / 2
            rgb = _oklab_to_lin(L, a * mid, b * mid)
            if all(-1e-4 <= v <= 1 + 1e-4 for v in rgb):
                lo = mid
            else:
                hi = mid
        rgb = _oklab_to_lin(L, a * lo, b * lo)
    return rgb_to_hex(*(_gam(max(0.0, min(1.0, v))) for v in rgb))


def hex_to_oklch(h: str) -> tuple[float, float, float]:
    L, a, b = hex_to_oklab(h)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_to_hex(L: float, C: float, h: float) -> str:
    L = max(0.0, min(1.0, L))
    return oklab_to_hex(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))


def mix(a: str, b: str, t: float) -> str:
    """Mix colour a into b by fraction t (OKLab)."""
    la, aa, ba = hex_to_oklab(a)
    lb, ab, bb = hex_to_oklab(b)
    return oklab_to_hex(lb + (la - lb) * t, ab + (aa - ab) * t, bb + (ba - bb) * t)


def distance(a: str, b: str) -> float:
    la, aa, ba = hex_to_oklab(a)
    lb, ab, bb = hex_to_oklab(b)
    return math.sqrt((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)


# --- Sanitising and taming -------------------------------------------------------------------------
def sanitize(value, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    m = HEX_RE.match(value.strip())
    if not m:
        return fallback
    h = m.group(1).lower()
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return "#" + h


def tame(hex_color: str, cap: float) -> tuple[float, float, float]:
    """Return (L, C, h): neon chroma compressed and capped; near-neutral colours stay neutral."""
    L, C, h = hex_to_oklch(hex_color)
    if C < 0.025:
        return L, C, h
    if C > 0.10:
        C = 0.10 + (C - 0.10) * 0.45
    return max(0.28, min(0.80, L)), min(C, cap), h


def _walk(L: float, C: float, h: float, step: int, ok, start: float | None = None) -> str:
    """Move lightness in 0.01 steps (step=-1 darker, +1 lighter) until ok(hex) holds. Bounded: L reaches 0/1."""
    cur = L if start is None else start
    best = oklch_to_hex(cur, C, h)
    for _ in range(101):
        best = oklch_to_hex(cur, C, h)
        if ok(best):
            return best
        if (step < 0 and cur <= 0) or (step > 0 and cur >= 1):
            break
        cur = max(0.0, min(1.0, cur + step * 0.01))
    return best


def _roles(tamed: tuple[float, float, float], pal: dict, dark: bool) -> dict:
    """Derive fill / on-fill / text / ui / soft roles for one colour in one mode."""
    L, C, h = tamed
    bg, surface, ink, ink2 = pal["bg"], pal["surface"], pal["ink"], pal["ink2"]
    lo, hi = (0.55, 0.72) if dark else (0.35, 0.58)
    fill_L = max(lo, min(hi, L))
    fill = oklch_to_hex(fill_L, C, h)

    # on-fill: white or near-black, whichever reads better; nudge the fill until AA holds
    on = "#ffffff" if contrast("#ffffff", fill) >= contrast(DARK_INK, fill) else DARK_INK
    if contrast(on, fill) < 4.5:
        fill = _walk(L, C, h, -1 if on == "#ffffff" else 1, lambda x: contrast(on, x) >= 4.5, start=fill_L)

    # soft tint: brand mixed into the card colour; keep body text AA on it
    amount = 0.16 if dark else 0.09
    soft = mix(fill, surface, amount)
    while amount > 0.01 and (contrast(ink, soft) < 4.5 or contrast(ink2, soft) < 4.5):
        amount -= 0.02
        soft = mix(fill, surface, max(amount, 0.0))

    step = 1 if dark else -1
    text = _walk(
        L, C, h, step,
        lambda x: min(contrast(x, bg), contrast(x, surface), contrast(x, soft)) >= 4.5,
        start=fill_L,
    )
    ui = _walk(L, C, h, step, lambda x: min(contrast(x, bg), contrast(x, surface)) >= 3.0, start=fill_L)
    return {"fill": fill, "on": on, "text": text, "ui": ui, "soft": soft}


def _tint_neutrals(pal: dict, brand_fill: str, tint: float) -> dict:
    """Nudge bg/surface/lines toward the brand so the page feels made for this restaurant."""
    if tint <= 0:
        return dict(pal)
    out = dict(pal)
    _, fa, fb = hex_to_oklab(brand_fill)
    for k in ("bg", "surface", "line", "line_strong"):
        nl, na, nb = hex_to_oklab(pal[k])  # keep lightness, shift hue/chroma only
        out[k] = oklab_to_hex(nl, na + (fa - na) * tint * 2, nb + (fb - nb) * tint * 2)
    ok = (
        contrast(out["ink"], out["bg"]) >= 7
        and contrast(out["ink2"], out["bg"]) >= 4.5
        and contrast(out["ink2"], out["surface"]) >= 4.5
        and contrast(out["line_strong"], out["bg"]) >= 3.0
        and contrast(out["line_strong"], out["surface"]) >= 3.0
    )
    return out if ok else dict(pal)


def build_theme_vars(theme: str, brand_color: str | None, accent_color: str | None) -> dict:
    if theme not in THEMES:
        theme = DEFAULT_THEME
    spec = PALETTES[theme]
    cap = spec["chroma_cap"]
    brand_hex = sanitize(brand_color, spec["brand"])
    brand = tame(brand_hex, cap)

    default_accent = spec["accent"]
    accent_hex = sanitize(accent_color, "") if accent_color else ""
    accent = None
    if accent_hex:
        cand = tame(accent_hex, cap)
        if cand[1] >= 0.025 and distance(oklch_to_hex(*cand), oklch_to_hex(*brand)) >= 0.06:
            accent = cand
    if accent is None:
        accent = tame(default_accent, cap) if default_accent else brand

    result = {}
    for mode in ("light", "dark"):
        dark = mode == "dark"
        pal = spec[mode]
        b = _roles(brand, pal, dark)
        pal = _tint_neutrals(pal, b["fill"], spec["tint"])
        b = _roles(brand, pal, dark)  # recompute against the tinted surfaces
        a = _roles(accent, pal, dark)
        result[mode] = {
            "--bg": pal["bg"],
            "--surface": pal["surface"],
            "--ink": pal["ink"],
            "--ink-2": pal["ink2"],
            "--line": pal["line"],
            "--line-strong": pal["line_strong"],
            "--brand": b["fill"],
            "--on-brand": b["on"],
            "--brand-text": b["text"],
            "--brand-ui": b["ui"],
            "--brand-soft": b["soft"],
            "--accent": a["fill"],
            "--on-accent": a["on"],
            "--accent-text": a["text"],
            "--accent-ui": a["ui"],
            "--accent-soft": a["soft"],
            "--focus": b["ui"],
            "--scrim": "rgb(0 0 0 / .65)" if dark else "rgb(0 0 0 / .5)",
            "--logo-bg": "#f4efe6" if dark else "transparent",
            "--logo-pad": "6px" if dark else "0px",
        }
    return result


# Pairs asserted by tests: (foreground var, background var, minimum ratio)
CONTRAST_RULES = [
    ("--ink", "--bg", 4.5), ("--ink", "--surface", 4.5), ("--ink", "--brand-soft", 4.5),
    ("--ink-2", "--bg", 4.5), ("--ink-2", "--surface", 4.5), ("--ink-2", "--brand-soft", 4.5),
    ("--brand-text", "--bg", 4.5), ("--brand-text", "--surface", 4.5), ("--brand-text", "--brand-soft", 4.5),
    ("--on-brand", "--brand", 4.5),
    ("--accent-text", "--bg", 4.5), ("--accent-text", "--surface", 4.5),
    ("--on-accent", "--accent", 4.5),
    ("--brand-ui", "--bg", 3.0), ("--brand-ui", "--surface", 3.0),
    ("--accent-ui", "--bg", 3.0), ("--accent-ui", "--surface", 3.0),
    ("--line-strong", "--bg", 3.0), ("--line-strong", "--surface", 3.0),
]
