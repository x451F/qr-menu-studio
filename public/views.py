"""Public menu view.

Performance/caching rules (see docs/ARCHITECTURE.md):
* Anonymous, non-preview requests are served from Django's cache, keyed by the restaurant's
  content version (``updated_at``) + language + theme + colour mode. Any edit bumps
  ``updated_at`` (menus/signals.py), so a miss is guaranteed after every change.
* A strong ETag derived from the same key lets browsers/QR-scanner webviews revalidate with
  ``If-None-Match`` and receive an empty 304. ``Cache-Control: no-cache`` forces that
  revalidation on every visit so sold-out toggles show up within seconds.
* Preview (admin only) is never cached: ``Cache-Control: no-store``.
* No session/CSRF cookie is ever set here; the only cookie is the ``menu_lang`` preference.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.template.loader import render_to_string
from django.utils.cache import patch_vary_headers

from menus.cache import make_etag, page_cache_key

from .menu_context import build_menu_context, get_restaurant, prefetch_menu

LANG_COOKIE = "menu_lang"
LANG_COOKIE_AGE = 60 * 60 * 24 * 365
PAGE_CACHE_TTL = 60 * 60 * 24
TEMPLATE = "public/menu.html"


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


def _is_staff(request) -> bool:
    # Avoid touching the session (and its DB query) for visitors without a session cookie.
    if settings.SESSION_COOKIE_NAME not in request.COOKIES:
        return False
    return request.user.is_authenticated and request.user.is_staff


def _etag_matches(request, etag: str) -> bool:
    header = request.headers.get("If-None-Match", "")
    if not header:
        return False
    if header.strip() == "*":
        return True
    candidates = {tag.strip().removeprefix("W/") for tag in header.split(",")}
    return etag in candidates


def _finish(response, request, lang, set_cookie, *, etag=None, preview=False):
    if set_cookie and not preview:
        response.set_cookie(
            LANG_COOKIE, lang, max_age=LANG_COOKIE_AGE, samesite="Lax", secure=request.is_secure()
        )
    patch_vary_headers(response, ("Cookie", "Accept-Language"))
    if preview:
        response["Cache-Control"] = "no-store"
    else:
        response["Cache-Control"] = "no-cache"
    if etag:
        response["ETag"] = etag
    return response


def menu(request, slug):
    restaurant = get_restaurant(slug)
    is_staff = _is_staff(request)
    if restaurant is None or (not restaurant.is_published and not is_staff):
        raise Http404("Menu not found")

    preview = is_staff and request.GET.get("preview") == "1"
    lang, set_cookie = _pick_language(request, restaurant)

    if preview:
        prefetch_menu(restaurant)
        ctx = build_menu_context(
            restaurant,
            lang,
            theme=request.GET.get("theme"),
            mode=request.GET.get("mode"),
            preview=True,
            hide_photos=request.GET.get("photos") == "0",
        )
        html = render_to_string(TEMPLATE, ctx, request=request)
        return _finish(HttpResponse(html), request, lang, set_cookie, preview=True)

    theme, mode = restaurant.theme, restaurant.color_mode
    etag = make_etag(restaurant, lang, theme, mode)
    if not is_staff and _etag_matches(request, etag):
        return _finish(HttpResponseNotModified(), request, lang, set_cookie, etag=etag)

    key = page_cache_key(restaurant, lang, theme, mode)
    html = None if is_staff else cache.get(key)
    if html is None:
        prefetch_menu(restaurant)
        ctx = build_menu_context(restaurant, lang)
        html = render_to_string(TEMPLATE, ctx, request=request)
        if not is_staff:
            cache.set(key, html, PAGE_CACHE_TTL)
    return _finish(HttpResponse(html), request, lang, set_cookie, etag=None if is_staff else etag)
