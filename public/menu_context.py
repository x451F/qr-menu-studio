"""Builds the template context for the public menu page (templates/public/menu.html).

This module is the contract between the view layer and the theme templates.
Fields may be added freely; renaming or removing one means updating every theme.

Context passed to the template:
    menu: MenuView
    lang: str                      current language code ("fr" | "en")
    s: dict[str, str]              UI strings for `lang` (public/strings.py)
    theme_vars: {"light": {...}, "dark": {...}}   CSS custom properties (public/theming.py)
"""

from dataclasses import dataclass, field

from django.db.models import Prefetch

from menus.constants import ALLERGENS, DIETS, SPECIAL_KINDS, SUPPORTED_LANGUAGES, THEMES
from menus.formatting import format_price
from menus.i18n import tr
from menus.models import Category, Item, Restaurant


@dataclass
class PriceView:
    label: str  # "" when the item has a single unlabeled price; e.g. "25 cl", "Grande"
    amount: str  # "12,50 €"


@dataclass
class TagView:
    code: str  # allergen/diet code, also the icon id suffix: icons.svg#al-<code> / #diet-<code>
    label: str


@dataclass
class PhotoView:
    src: str
    srcset: str  # may be "" when no variants exist
    width: int
    height: int


@dataclass
class ItemView:
    id: int
    anchor: str  # "dish-<id>"
    name: str
    description: str  # may be ""
    prices: list[PriceView]
    photo: PhotoView | None
    allergens: list[TagView]
    diets: list[TagView]
    sold_out: bool


@dataclass
class CategoryView:
    id: int
    anchor: str  # "cat-<id>"
    name: str
    description: str
    items: list[ItemView]


@dataclass
class SpecialView:
    kind: str  # plat | formule | dessert | suggestion
    kind_label: str  # "Plat du jour"
    title: str
    description: str
    prices: list[PriceView]


@dataclass
class LanguageLink:
    code: str
    short: str  # "FR"
    label: str  # "Français"
    url: str  # "?lang=en"
    active: bool


@dataclass
class MenuView:
    name: str
    slug: str
    tagline: str
    logo_url: str  # "" when no logo
    theme: str  # bistro | trattoria | cafe | gastro | auberge
    color_mode: str  # auto | light | dark
    address: str
    maps_url: str
    phone: str
    phone_href: str  # "tel:+33555..." or ""
    hours: list[str]  # one line per row
    footer_note: str
    public_url: str
    languages: list[LanguageLink]
    specials: list[SpecialView]
    categories: list[CategoryView]
    legend_allergens: list[TagView]  # only allergens used on this menu, in canonical order
    legend_diets: list[TagView]  # only diets used on this menu
    has_photos: bool
    item_count: int
    preview: bool = False
    extra: dict = field(default_factory=dict)


def _prices(prices, lang) -> list[PriceView]:
    return [
        PriceView(label=tr(p.get("label") or {}, lang), amount=format_price(p["cents"]))
        for p in (prices or [])
        if p.get("cents") is not None
    ]


def _photo(item) -> PhotoView | None:
    if not item.photo:
        return None
    try:
        from menus.images import photo_view
    except ImportError:
        photo_view = None
    if photo_view:
        data = photo_view(item.photo)
        if data:
            return PhotoView(**data)
    try:
        return PhotoView(src=item.photo.url, srcset="", width=item.photo.width, height=item.photo.height)
    except (OSError, ValueError):
        return None


def load_restaurant(slug: str):
    return (
        Restaurant.objects.filter(slug=slug)
        .prefetch_related(
            Prefetch(
                "categories",
                queryset=Category.objects.filter(is_visible=True).prefetch_related(
                    Prefetch("items", queryset=Item.objects.filter(is_visible=True))
                ),
            ),
            "specials",
        )
        .first()
    )


def build_menu_context(
    restaurant: Restaurant, lang: str, *, theme=None, mode=None, preview=False, hide_photos=False
) -> dict:
    from .strings import strings_for
    from .theming import build_theme_vars

    theme = theme if theme in THEMES else restaurant.theme
    mode = mode if mode in ("auto", "light", "dark") else restaurant.color_mode
    used_allergens: set[str] = set()
    used_diets: set[str] = set()
    has_photos = False
    item_count = 0

    categories = []
    for cat in restaurant.categories.all():
        items = []
        for it in cat.items.all():
            used_allergens.update(it.allergens or [])
            used_diets.update(it.diets or [])
            photo = None if hide_photos else _photo(it)
            has_photos = has_photos or photo is not None
            items.append(
                ItemView(
                    id=it.id,
                    anchor=f"dish-{it.id}",
                    name=tr(it.name, lang),
                    description=tr(it.description, lang),
                    prices=_prices(it.prices, lang),
                    photo=photo,
                    allergens=[TagView(c, ALLERGENS[c][lang]) for c in ALLERGENS if c in (it.allergens or [])],
                    diets=[TagView(c, DIETS[c][lang]) for c in DIETS if c in (it.diets or [])],
                    sold_out=it.is_sold_out,
                )
            )
        if not items:
            continue
        item_count += len(items)
        categories.append(
            CategoryView(id=cat.id, anchor=f"cat-{cat.id}", name=tr(cat.name, lang), description=tr(cat.description, lang), items=items)
        )

    specials = [
        SpecialView(
            kind=sp.kind,
            kind_label=SPECIAL_KINDS[sp.kind][lang],
            title=tr(sp.title, lang),
            description=tr(sp.description, lang),
            prices=_prices(sp.prices, lang),
        )
        for sp in restaurant.specials.all()
        if sp.is_active and tr(sp.title, lang)
    ]

    languages = [
        LanguageLink(code=c, short=SUPPORTED_LANGUAGES[c]["short"], label=SUPPORTED_LANGUAGES[c]["label"], url=f"?lang={c}", active=c == lang)
        for c in restaurant.enabled_languages()
    ]

    menu = MenuView(
        name=restaurant.name,
        slug=restaurant.slug,
        tagline=tr(restaurant.tagline, lang),
        logo_url=restaurant.logo.url if restaurant.logo else "",
        theme=theme,
        color_mode=mode,
        address=restaurant.address,
        maps_url=restaurant.maps_link,
        phone=restaurant.phone,
        phone_href=restaurant.phone_href,
        hours=[line.strip() for line in tr(restaurant.hours, lang).splitlines() if line.strip()],
        footer_note=tr(restaurant.footer_note, lang),
        public_url=restaurant.public_url,
        languages=languages if len(languages) > 1 else [],
        specials=specials,
        categories=categories,
        legend_allergens=[TagView(c, ALLERGENS[c][lang]) for c in ALLERGENS if c in used_allergens],
        legend_diets=[TagView(c, DIETS[c][lang]) for c in DIETS if c in used_diets],
        has_photos=has_photos,
        item_count=item_count,
        preview=preview,
    )
    return {
        "menu": menu,
        "lang": lang,
        "s": strings_for(lang),
        "theme_vars": build_theme_vars(theme, restaurant.brand_color, restaurant.accent_color or None),
    }
