"""Dashboard, restaurant creation, settings (autosave), publishing, logo."""

from __future__ import annotations

import json
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from menus import images
from menus.constants import COLOR_MODES, DEFAULT_THEME, THEMES
from menus.models import Restaurant

from .auth import staff_required
from .services import DEFAULT_FOOTER_NOTE, LIMITS, apply_tr, clean_text

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

BRAND_PRESETS = [
    ("#7a2e2a", "Burgundy"),
    ("#b5532f", "Terracotta"),
    ("#b8862b", "Ochre"),
    ("#6b7a3a", "Olive"),
    ("#2f5d50", "Forest"),
    ("#24405c", "Navy"),
    ("#6a3550", "Plum"),
    ("#2b2b2b", "Charcoal"),
]

MAX_UPLOAD = 15 * 1024 * 1024


@staff_required
def dashboard(request):
    restaurants = (
        Restaurant.objects.annotate(item_count=Count("categories__items", distinct=True))
        .order_by("-updated_at")
    )
    return render(request, "editor/dashboard.html", {"restaurants": restaurants})


@staff_required
def restaurant_new(request):
    error = ""
    name = ""
    theme = DEFAULT_THEME
    if request.method == "POST":
        name = clean_text(request.POST.get("name"), 120)
        theme = request.POST.get("theme") if request.POST.get("theme") in THEMES else DEFAULT_THEME
        if not name:
            error = "Give the restaurant a name."
        else:
            restaurant = Restaurant.objects.create(
                name=name,
                theme=theme,
                languages=["fr", "en"],
                footer_note=dict(DEFAULT_FOOTER_NOTE),
            )
            if request.POST.get("then") == "import" and settings.AI_ENABLED:
                return redirect("ai:import", pk=restaurant.pk)
            return redirect("editor:restaurant_edit", pk=restaurant.pk)
    return render(
        request,
        "editor/restaurant_new.html",
        {"error": error, "name": name, "theme": theme, "themes": THEMES},
    )


def get_restaurant(pk: int) -> Restaurant:
    return get_object_or_404(Restaurant, pk=pk)


def _settings_context(restaurant: Restaurant, **extra):
    ctx = {
        "restaurant": restaurant,
        "themes": THEMES,
        "color_modes": COLOR_MODES,
        "brand_presets": BRAND_PRESETS,
        "slug_locked": restaurant.slug_is_locked(),
        "english_on": "en" in restaurant.enabled_languages(),
        "preview_base": restaurant.public_path + "?preview=1",
    }
    ctx.update(extra)
    return ctx


@staff_required
def restaurant_settings(request, pk):
    restaurant = get_restaurant(pk)
    if request.method == "POST":
        return _save_settings(request, restaurant)
    return render(request, "editor/settings.html", _settings_context(restaurant))


def _save_settings(request, restaurant: Restaurant):
    data = request.POST
    errors: dict[str, str] = {}
    changed: list[str] = []

    def take(key):
        return key in data

    if take("name"):
        name = clean_text(data["name"], 120)
        if name:
            restaurant.name = name
            changed.append("name")
        else:
            errors["name"] = "The name can't be empty."

    for field, limit in (("tagline", LIMITS["tagline"]), ("hours", LIMITS["hours"]), ("footer_note", LIMITS["footer"])):
        if take(f"{field}_fr") or take(f"{field}_en"):
            setattr(restaurant, field, apply_tr(getattr(restaurant, field), data, field, limit))
            changed.append(field)

    for field in ("brand_color", "accent_color"):
        if take(field):
            value = data[field].strip()
            if HEX_RE.match(value):
                setattr(restaurant, field, value.lower())
                changed.append(field)
            elif value == "" and field == "accent_color":
                restaurant.accent_color = ""
                changed.append(field)
            else:
                errors[field] = "Use a hex colour like #7a2e2a."

    if take("theme"):
        if data["theme"] in THEMES:
            restaurant.theme = data["theme"]
            changed.append("theme")
        else:
            errors["theme"] = "Unknown theme."
    if take("color_mode"):
        if data["color_mode"] in COLOR_MODES:
            restaurant.color_mode = data["color_mode"]
            changed.append("color_mode")
        else:
            errors["color_mode"] = "Unknown colour mode."

    if take("address"):
        restaurant.address = clean_text(data["address"], 400)
    if take("phone"):
        restaurant.phone = clean_text(data["phone"], 30)
    if take("maps_url"):
        url = data["maps_url"].strip()
        try:
            if url:
                URLValidator(schemes=["http", "https"])(url)
            restaurant.maps_url = url
        except ValidationError:
            errors["maps_url"] = "Enter a full link starting with https://"

    if take("english"):
        restaurant.languages = ["fr", "en"] if data["english"] in ("1", "on", "true") else ["fr"]

    if take("slug"):
        if restaurant.slug_is_locked():
            errors["slug"] = "This address is permanent: the menu has been published."
        else:
            slug = slugify(data["slug"])[:80]
            if not slug:
                errors["slug"] = "Use letters, numbers and dashes."
            elif Restaurant.objects.filter(slug=slug).exclude(pk=restaurant.pk).exists():
                errors["slug"] = "This address is already used by another restaurant."
            else:
                restaurant.slug = slug

    restaurant.save()
    parts = []
    if "/settings/" in request.headers.get("HX-Current-URL", ""):
        parts = [
            f'<div id="err-{key}" class="field-error" role="alert" hx-swap-oob="true">{escape(msg)}</div>'
            for key, msg in errors.items()
        ]
        for key in data:
            if key not in errors and key != "csrfmiddlewaretoken":
                parts.append(f'<div id="err-{key}" class="field-error" hx-swap-oob="true"></div>')
        parts.append(
            '<div id="public-url-box" hx-swap-oob="innerHTML">'
            + render_public_url(request, restaurant)
            + "</div>"
        )
    response = HttpResponse("".join(parts))
    trigger = {
        "settingsSaved": {
            "publicPath": restaurant.public_path,
            "theme": restaurant.theme,
            "colorMode": restaurant.color_mode,
        }
    }
    if errors:
        trigger["validation"] = {"message": next(iter(errors.values()))}
    response["HX-Trigger"] = json.dumps(trigger)
    return response


def render_public_url(request, restaurant):
    from django.template.loader import render_to_string

    return render_to_string("editor/_public_url.html", {"restaurant": restaurant}, request)


@staff_required
@require_POST
def restaurant_publish(request, pk):
    restaurant = get_restaurant(pk)
    restaurant.is_published = not restaurant.is_published
    restaurant.save()
    response = HttpResponse(status=200)
    response["HX-Refresh"] = "true"
    return response


@staff_required
@require_POST
def restaurant_logo(request, pk):
    restaurant = get_restaurant(pk)
    error = ""
    if request.POST.get("remove"):
        if restaurant.logo:
            restaurant.logo.delete(save=False)
        restaurant.save()
    else:
        upload = request.FILES.get("logo")
        if not upload:
            error = "Choose an image file."
        elif upload.size > MAX_UPLOAD:
            error = "That file is too large (15 MB max)."
        else:
            try:
                processed = images.process_logo(upload, upload.name)
            except Exception:  # Pillow raises many error types for bad files
                error = "That doesn't look like an image."
            else:
                if restaurant.logo:
                    restaurant.logo.delete(save=False)
                restaurant.logo.save(processed.name, processed, save=False)
                restaurant.save()
    response = render(request, "editor/_logo_box.html", {"restaurant": restaurant, "error": error})
    if error:
        response.status_code = 422
    else:
        response["HX-Trigger"] = json.dumps({"settingsSaved": {"publicPath": restaurant.public_path}})
    return response

