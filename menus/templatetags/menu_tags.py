from django import template

from menus.formatting import format_price, format_prices
from menus.i18n import tr as _tr

register = template.Library()


@register.filter
def tr(value, lang="fr"):
    """{{ item.name|tr:lang }}"""
    return _tr(value, lang)


@register.filter
def price(cents):
    """{{ 1250|price }} -> 12,50 €"""
    return format_price(cents)


@register.filter
def prices(value, lang="fr"):
    """{{ item.prices|prices:lang }} -> 8,50 € / 14,00 €"""
    return format_prices(value, lang)
