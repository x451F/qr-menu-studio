"""Theme palettes (stub).

Contract: build_theme_vars(theme, brand_color, accent_color) -> {"light": {...}, "dark": {...}}
mapping CSS custom property names to values, WCAG AA-safe for the text they are used on.
"""


def build_theme_vars(theme: str, brand_color: str, accent_color: str | None) -> dict:
    return {
        "light": {"--bg": "#fbf8f3", "--text": "#1d1a17", "--muted": "#5f5750", "--brand": brand_color},
        "dark": {"--bg": "#141210", "--text": "#f2ede6", "--muted": "#b3aaa0", "--brand": "#e8b4a8"},
    }
