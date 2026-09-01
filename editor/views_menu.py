"""Menu editor: page, categories, items, specials, reorder, photos. Most endpoints answer HTMX."""

from __future__ import annotations

import json

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from menus import images
from menus.constants import ALLERGENS, DIETS, SPECIAL_KINDS, THEMES
from menus.formatting import parse_price
from menus.models import Category, DailySpecial, Item, Restaurant

from .auth import staff_required
from .services import (
    CATEGORY_PRESETS,
    LIMITS,
    apply_tr,
    choose_codes,
    clean_text,
    missing_english_count,
    next_position,
    parse_prices,
    renumber,
)
from .views_restaurant import BRAND_PRESETS, MAX_UPLOAD, get_restaurant

UNDO_KEY = "editor_undo_item"


# -- helpers -----------------------------------------------------------------------------


def trigger(response, **events):
    response["HX-Trigger"] = json.dumps(events)
    return response


def base_ctx(restaurant: Restaurant, **extra):
    ctx = {
        "restaurant": restaurant,
        "all_categories": list(restaurant.categories.all()),
        "special_kinds": SPECIAL_KINDS,
    }
    ctx.update(extra)
    return ctx


def amount_echo(data) -> list[str | None]:
    """Normalised text for each posted amount row (None when empty/invalid)."""
    from .templatetags.editor_tags import cents_input

    out = []
    for raw in data.getlist("price_amount"):
        cents = parse_price(raw)
        out.append(cents_input(cents) if cents is not None else None)
    return out


def price_feedback(data, errors):
    """HX-Trigger payload describing price validation + normalised values."""
    events = {"pricesFormatted": {"values": amount_echo(data)}}
    if errors:
        rows = [i for i, _ in errors]
        raw = errors[0][1]
        message = f"“{raw}” isn't a valid price. Try 12,50"
        events["priceError"] = {"rows": rows, "message": message}
        events["validation"] = {"message": message}
    return events


def missing_oob(restaurant) -> str:
    n = missing_english_count(restaurant)
    return render_to_string("editor/_missing_en.html", {"missing_count": n, "oob": True})


def get_category(pk) -> Category:
    return get_object_or_404(Category.objects.select_related("restaurant"), pk=pk)


def get_item(pk) -> Item:
    return get_object_or_404(Item.objects.select_related("category__restaurant"), pk=pk)


def render_toggle(request, url, on, kind):
    return render(request, "editor/_toggle.html", {"url": url, "on": on, "kind": kind})


# -- the editor page -----------------------------------------------------------------------


@staff_required
def restaurant_edit(request, pk):
    restaurant = get_restaurant(pk)
    categories = list(restaurant.categories.prefetch_related("items"))
    ctx = base_ctx(
        restaurant,
        categories=categories,
        all_categories=categories,
        specials=list(restaurant.specials.all()),
        themes=THEMES,
        missing_count=missing_english_count(restaurant),
        english_on="en" in restaurant.enabled_languages(),
        preview_base=restaurant.public_path + "?preview=1",
        category_presets=CATEGORY_PRESETS,
        brand_presets=BRAND_PRESETS,
    )
    return render(request, "editor/edit.html", ctx)


# -- categories ------------------------------------------------------------------------------


@staff_required
@require_POST
def category_add(request, pk):
    restaurant = get_restaurant(pk)
    name_fr = clean_text(request.POST.get("name_fr"), LIMITS["name"])
    name_en = clean_text(request.POST.get("name_en"), LIMITS["name"])
    if not name_en and name_fr in CATEGORY_PRESETS:
        name_en = CATEGORY_PRESETS[name_fr]
    if not name_fr:
        response = HttpResponse("Type a category name first.", status=422)
        response["HX-Retarget"] = "#cat-add-error"
        response["HX-Reswap"] = "innerHTML"
        return response
    category = Category.objects.create(
        restaurant=restaurant,
        name={"fr": name_fr, "en": name_en},
        position=next_position(restaurant.categories),
    )
    restaurant.touch()
    html = render_to_string(
        "editor/_category.html", base_ctx(restaurant, category=category), request
    )
    if restaurant.categories.count() == 1:
        html += '<div id="empty-state" hx-swap-oob="delete"></div>'
    html += '<div id="cat-add-error" hx-swap-oob="innerHTML"></div>'
    return HttpResponse(html)


@staff_required
@require_POST
def category_update(request, pk):
    category = get_category(pk)
    category.name = apply_tr(category.name, request.POST, "name", LIMITS["name"])
    category.description = apply_tr(category.description, request.POST, "description", LIMITS["description"])
    category.save()
    category.restaurant.touch()
    return HttpResponse(missing_oob(category.restaurant))


@staff_required
@require_POST
def category_toggle(request, pk):
    category = get_category(pk)
    category.is_visible = not category.is_visible
    category.save(update_fields=["is_visible"])
    category.restaurant.touch()
    return render_toggle(
        request, reverse("editor:category_toggle", args=[category.pk]), category.is_visible, "cat_visible"
    )


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_category(pk)
    restaurant = category.restaurant
    category.delete()
    renumber(restaurant.categories.all())
    restaurant.touch()
    return HttpResponse(missing_oob(restaurant))


# -- items -----------------------------------------------------------------------------------


def item_context(request, item, **extra):
    restaurant = item.category.restaurant
    return base_ctx(restaurant, item=item, category=item.category, **extra)


@staff_required
@require_POST
def item_add(request, pk):
    category = get_category(pk)
    restaurant = category.restaurant
    name = clean_text(request.POST.get("name_fr"), LIMITS["name"])
    raw_price = request.POST.get("price_amount", "").strip()
    error = ""
    if not name:
        error = "Type a name first."
    cents = parse_price(raw_price) if raw_price else None
    if raw_price and cents is None:
        error = f"“{raw_price}” isn't a valid price. Try 12,50"
    if error:
        response = HttpResponse(error, status=422)
        response["HX-Retarget"] = f"#qa-err-{category.pk}"
        response["HX-Reswap"] = "innerHTML"
        return response
    item = Item.objects.create(
        category=category,
        name={"fr": name, "en": ""},
        prices=[{"cents": cents}] if cents is not None else [],
        position=next_position(category.items),
    )
    restaurant.touch()
    html = render_to_string("editor/_item.html", item_context(request, item), request)
    html += f'<div id="qa-err-{category.pk}" hx-swap-oob="innerHTML"></div>'
    html += missing_oob(restaurant)
    return HttpResponse(html)


@staff_required
@require_POST
def item_update(request, pk):
    item = get_item(pk)
    restaurant = item.category.restaurant
    data = request.POST
    events: dict = {}

    item.name = apply_tr(item.name, data, "name", LIMITS["name"])
    item.description = apply_tr(item.description, data, "description", LIMITS["description"])
    if "_chips" in data:
        item.allergens = choose_codes(data.getlist("allergens"), ALLERGENS)
        item.diets = choose_codes(data.getlist("diets"), DIETS)

    if "category" in data and data["category"].isdigit() and int(data["category"]) != item.category_id:
        target = Category.objects.filter(pk=int(data["category"]), restaurant=restaurant).first()
        if target:
            item.category = target
            item.position = next_position(target.items)
            events["itemMoved"] = {"item": item.pk, "category": target.pk}

    if "price_amount" in data:
        prices, errors = parse_prices(data)
        if not errors:
            item.prices = prices
        events.update(price_feedback(data, errors))

    item.save()
    restaurant.touch()
    html = render_to_string(
        "editor/_item_oob.html", {"item": item, "missing_count": missing_english_count(restaurant)}, request
    )
    return trigger(HttpResponse(html), **events)


@staff_required
@require_POST
def item_toggle(request, pk, field):
    if field not in ("is_sold_out", "is_visible"):
        return HttpResponseBadRequest("unknown field")
    item = get_item(pk)
    setattr(item, field, not getattr(item, field))
    item.save(update_fields=[field])
    item.category.restaurant.touch()
    kind = "soldout" if field == "is_sold_out" else "item_visible"
    url = reverse("editor:item_toggle", args=[item.pk, field])
    return render_toggle(request, url, getattr(item, field), kind)


@staff_required
@require_POST
def item_duplicate(request, pk):
    item = get_item(pk)
    category = item.category
    restaurant = category.restaurant
    siblings = list(category.items.all())
    copy = Item(
        category=category,
        name=dict(item.name or {}),
        description=dict(item.description or {}),
        prices=list(item.prices or []),
        allergens=list(item.allergens or []),
        diets=list(item.diets or []),
        is_sold_out=item.is_sold_out,
        is_visible=item.is_visible,
    )
    fr = copy.name.get("fr", "")
    if fr:
        copy.name["fr"] = f"{fr} (copy)"
    en = copy.name.get("en", "")
    if en:
        copy.name["en"] = f"{en} (copy)"
    if item.photo:
        try:
            with item.photo.open("rb") as fh:
                copy.photo.save(item.photo.name.rsplit("/", 1)[-1], ContentFile(fh.read()), save=False)
        except OSError:
            pass
    idx = [s.pk for s in siblings].index(item.pk)
    copy.position = item.position + 1
    copy.save()
    ordered = siblings[: idx + 1] + [copy] + siblings[idx + 1 :]
    renumber(ordered)
    restaurant.touch()
    copy.refresh_from_db()
    html = render_to_string("editor/_item.html", item_context(request, copy, open=True), request)
    html += missing_oob(restaurant)
    return HttpResponse(html)


@staff_required
@require_POST
def item_delete(request, pk):
    item = get_item(pk)
    category = item.category
    restaurant = category.restaurant
    _discard_undo_photo(request)
    request.session[UNDO_KEY] = {
        "restaurant": restaurant.pk,
        "category": category.pk,
        "position": item.position,
        "fields": {
            "name": item.name,
            "description": item.description,
            "prices": item.prices,
            "allergens": item.allergens,
            "diets": item.diets,
            "is_sold_out": item.is_sold_out,
            "is_visible": item.is_visible,
            "photo": item.photo.name if item.photo else "",
        },
    }
    label = (item.name or {}).get("fr") or (item.name or {}).get("en") or "Item"
    # Keep the photo file (and its variants) so Undo can restore it: the post_delete cleanup
    # signal only removes files still attached to the instance.
    item.photo = None
    item.delete()
    restaurant.touch()
    html = render_to_string(
        "editor/_toast.html",
        {"message": f"“{label}” deleted", "undo_url": reverse("editor:item_undo", args=[restaurant.pk])},
        request,
    )
    html += missing_oob(restaurant)
    return HttpResponse(html)


def _discard_undo_photo(request):
    """Delete the photo kept for a previous, never-used undo snapshot."""
    snap = request.session.get(UNDO_KEY)
    name = (snap or {}).get("fields", {}).get("photo")
    if name and not Item.objects.filter(photo=name).exists():
        from django.core.files.storage import default_storage

        from menus.images import delete_with_variants

        delete_with_variants(default_storage, name)


@staff_required
@require_POST
def item_undo(request, pk):
    restaurant = get_restaurant(pk)
    snap = request.session.pop(UNDO_KEY, None)
    empty_toast = '<div id="toast" class="toast" hx-swap-oob="true"></div>'
    if not snap or snap.get("restaurant") != restaurant.pk:
        return HttpResponse(empty_toast)
    category = restaurant.categories.filter(pk=snap["category"]).first()
    if category is None:
        return HttpResponse(empty_toast)
    fields = snap["fields"]
    with transaction.atomic():
        siblings = list(category.items.all())
        item = Item(category=category, **{k: v for k, v in fields.items() if k != "photo"})
        if fields.get("photo"):
            item.photo.name = fields["photo"]
        item.position = snap["position"]
        item.save()
        pos = min(snap["position"], len(siblings))
        renumber(siblings[:pos] + [item] + siblings[pos:])
    restaurant.touch()
    category = Category.objects.prefetch_related("items").get(pk=category.pk)
    html = render_to_string(
        "editor/_items_list.html", base_ctx(restaurant, category=category), request
    )
    response = HttpResponse(html + empty_toast + missing_oob(restaurant))
    response["HX-Retarget"] = f"#items-{category.pk}"
    response["HX-Reswap"] = "innerHTML"
    return response


@staff_required
@require_POST
def item_photo(request, pk):
    item = get_item(pk)
    restaurant = item.category.restaurant
    error = ""
    if request.POST.get("remove"):
        if item.photo:
            item.photo.delete(save=False)
        item.save()
        restaurant.touch()
    else:
        upload = request.FILES.get("photo")
        if not upload:
            error = "Choose a photo."
        elif upload.size > MAX_UPLOAD:
            error = "That file is too large (15 MB max)."
        else:
            try:
                processed = images.process_photo(upload, upload.name)
            except Exception:
                error = "That doesn't look like an image."
            else:
                if item.photo:
                    item.photo.delete(save=False)
                item.photo.save(processed.name, processed, save=False)
                item.save()
                restaurant.touch()
    html = render_to_string("editor/_photo_box.html", {"item": item, "error": error}, request)
    html += render_to_string("editor/_thumb.html", {"item": item, "oob": True}, request)
    response = HttpResponse(html, status=422 if error else 200)
    return response


# -- specials ----------------------------------------------------------------------------------


def special_context(special, restaurant, **extra):
    return base_ctx(restaurant, special=special, **extra)


@staff_required
@require_POST
def special_add(request, pk, kind):
    restaurant = get_restaurant(pk)
    if kind not in SPECIAL_KINDS:
        return HttpResponseBadRequest("unknown kind")
    special = DailySpecial.objects.create(
        restaurant=restaurant, kind=kind, position=next_position(restaurant.specials)
    )
    restaurant.touch()
    html = render_to_string(
        "editor/_special.html", special_context(special, restaurant, open=True), request
    )
    if restaurant.specials.count() == 1:
        html += '<div id="specials-empty" hx-swap-oob="delete"></div>'
    return HttpResponse(html)


@staff_required
@require_POST
def special_update(request, pk):
    special = get_object_or_404(DailySpecial.objects.select_related("restaurant"), pk=pk)
    restaurant = special.restaurant
    data = request.POST
    events: dict = {}
    special.title = apply_tr(special.title, data, "title", LIMITS["name"])
    special.description = apply_tr(special.description, data, "description", LIMITS["description"])
    if data.get("kind") in SPECIAL_KINDS:
        special.kind = data["kind"]
    if "price_amount" in data:
        prices, errors = parse_prices(data)
        if not errors:
            special.prices = prices
        events.update(price_feedback(data, errors))
    special.save()
    restaurant.touch()
    html = render_to_string(
        "editor/_special_oob.html",
        {"special": special, "missing_count": missing_english_count(restaurant)},
        request,
    )
    return trigger(HttpResponse(html), **events)


@staff_required
@require_POST
def special_toggle(request, pk):
    special = get_object_or_404(DailySpecial.objects.select_related("restaurant"), pk=pk)
    special.is_active = not special.is_active
    special.save()
    special.restaurant.touch()
    return render_toggle(
        request, reverse("editor:special_toggle", args=[special.pk]), special.is_active, "special_active"
    )


@staff_required
@require_POST
def special_delete(request, pk):
    special = get_object_or_404(DailySpecial.objects.select_related("restaurant"), pk=pk)
    restaurant = special.restaurant
    special.delete()
    restaurant.touch()
    return HttpResponse(missing_oob(restaurant))


# -- ordering ----------------------------------------------------------------------------------


def _ids(raw: str) -> list[int] | None:
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        return None


@staff_required
@require_POST
def reorder_categories(request, pk):
    restaurant = get_restaurant(pk)
    ids = _ids(request.POST.get("order", ""))
    cats = {c.pk: c for c in restaurant.categories.all()}
    if ids is None or set(ids) - set(cats):
        return HttpResponseBadRequest("bad order")
    rest = [c for c in cats.values() if c.pk not in ids]
    renumber([cats[i] for i in ids] + rest)
    restaurant.touch()
    return HttpResponse(status=204)


@staff_required
@require_POST
def reorder_items(request, pk):
    """POST category=<id>&order=<id,id,...>: places those items (in that order) into the category."""
    restaurant = get_restaurant(pk)
    ids = _ids(request.POST.get("order", ""))
    cat_id = request.POST.get("category", "")
    if ids is None or not cat_id.isdigit():
        return HttpResponseBadRequest("bad order")
    category = get_object_or_404(Category, pk=int(cat_id), restaurant=restaurant)
    items = {i.pk: i for i in Item.objects.filter(pk__in=ids, category__restaurant=restaurant)}
    if set(ids) != set(items):
        return HttpResponseBadRequest("bad order")
    with transaction.atomic():
        moved = []
        for pos, item_id in enumerate(ids):
            item = items[item_id]
            item.category = category
            item.position = pos
            moved.append(item)
        Item.objects.bulk_update(moved, ["category", "position"])
    restaurant.touch()
    return HttpResponse(status=204)


@staff_required
@require_POST
def reorder_specials(request, pk):
    restaurant = get_restaurant(pk)
    ids = _ids(request.POST.get("order", ""))
    specials = {s.pk: s for s in restaurant.specials.all()}
    if ids is None or set(ids) - set(specials):
        return HttpResponseBadRequest("bad order")
    rest = [s for s in specials.values() if s.pk not in ids]
    renumber([specials[i] for i in ids] + rest)
    restaurant.touch()
    return HttpResponse(status=204)
