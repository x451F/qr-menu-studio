from django.http import Http404
from django.shortcuts import render

from .menu_context import build_menu_context, load_restaurant

LANG_COOKIE = "menu_lang"
LANG_COOKIE_AGE = 60 * 60 * 24 * 365


def _pick_language(request, restaurant) -> tuple[str, bool]:
    """Return (lang, should_set_cookie)."""
    enabled = restaurant.enabled_languages()
    requested = request.GET.get("lang")
    if requested in enabled:
        return requested, True
    cookie = request.COOKIES.get(LANG_COOKIE)
    if cookie in enabled:
        return cookie, False
    if "en" in enabled:
        accept = request.headers.get("Accept-Language", "").lower()
        first = accept.split(",")[0].strip()[:2] if accept else ""
        if first and first != "fr":
            return "en", False
    return "fr", False


def menu(request, slug):
    restaurant = load_restaurant(slug)
    is_admin = request.user.is_authenticated and request.user.is_staff
    if restaurant is None or (not restaurant.is_published and not is_admin):
        raise Http404("Menu not found")

    preview = is_admin and request.GET.get("preview") == "1"
    lang, set_cookie = _pick_language(request, restaurant)
    ctx = build_menu_context(
        restaurant,
        lang,
        theme=request.GET.get("theme") if preview else None,
        mode=request.GET.get("mode") if preview else None,
        preview=preview,
        hide_photos=preview and request.GET.get("photos") == "0",
    )
    response = render(request, "public/menu.html", ctx)
    if set_cookie and not preview:
        response.set_cookie(LANG_COOKIE, lang, max_age=LANG_COOKIE_AGE, samesite="Lax", secure=request.is_secure())
    response["Vary"] = "Cookie, Accept-Language"
    if preview:
        response["Cache-Control"] = "no-store"
    return response
