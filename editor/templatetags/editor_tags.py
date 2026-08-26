from django import template
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.html import format_html

from editor import services
from menus import images
from menus.formatting import format_price

register = template.Library()


@register.simple_tag
def sprite_href(kind: str, code: str) -> str:
    """URL of an icon inside the public sprite (`al` = allergen, `diet`). '' if the sprite is missing."""
    try:
        base = staticfiles_storage.url("public/icons.svg")
    except ValueError:  # manifest storage and the sprite doesn't exist (yet)
        return ""
    return f"{base}#{kind}-{code}"


@register.simple_tag
def icon(name: str, css: str = "") -> str:
    """Inline reference to the editor icon sprite."""
    base = staticfiles_storage.url("editor/icons.svg")
    return format_html(
        '<svg class="i {}" aria-hidden="true" focusable="false"><use href="{}#i-{}"></use></svg>',
        css,
        base,
        name,
    )


@register.filter
def cents_input(cents):
    """1250 -> '12,50' (value shown inside price inputs)."""
    if cents is None or cents == "":
        return ""
    return format_price(int(cents)).replace(" ", "").replace(" €", "")


@register.filter
def summary_price(prices):
    """Compact price for collapsed rows: '12,50 €' or '8,50 € +1'."""
    prices = [p for p in (prices or []) if p.get("cents") is not None]
    if not prices:
        return ""
    text = format_price(prices[0]["cents"])
    if len(prices) > 1:
        text += f" +{len(prices) - 1}"
    return text


@register.simple_tag
def photo_data(field_file):
    return images.photo_view(field_file)


@register.filter
def price_rows(prices):
    return services.price_rows(prices)


@register.filter
def prices_multi(prices):
    return services.prices_multi(prices)


@register.filter
def allergen_options(item):
    return services.allergen_options(item)


@register.filter
def diet_options(item):
    return services.diet_options(item)
