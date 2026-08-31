"""AI import flow (upload -> review -> save) and translation endpoints."""

from __future__ import annotations

import json
import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods, require_POST

from menus.constants import ALLERGENS, DIETS, SPECIAL_KINDS, SUPPORTED_LANGUAGES
from menus.models import Restaurant

from . import drafts, services
from .missing import fill_missing_translations
from .models import ImportDraft

logger = logging.getLogger(__name__)

MAX_TRANSLATE_KEYS = 500
MAX_TRANSLATE_CHARS = 100_000


def staff_required(view):
    """Login + staff. Anonymous users are redirected to the login page; non-staff get 403."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "fetch" or "application/json" in request.headers.get(
        "Accept", ""
    )


# --------------------------------------------------------------------------------------
# import: upload
# --------------------------------------------------------------------------------------
def _upload_context(request, restaurant, **extra):
    latest = restaurant.import_drafts.filter(status=ImportDraft.STATUS_DRAFT).first()
    resume = None
    if latest:
        n_items = sum(len(c.get("items", [])) for c in latest.data.get("categories", []))
        resume = {"draft": latest, "items": n_items}
    return {
        "restaurant": restaurant,
        "ai_enabled": services.is_enabled(),
        "ai_fake": services.is_fake(),
        "max_images": services.MAX_IMAGES,
        "resume": resume,
        **extra,
    }


@staff_required
@require_http_methods(["GET", "POST"])
def import_upload(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    if request.method == "GET":
        return render(request, "ai/import_upload.html", _upload_context(request, restaurant))

    def fail(message, status):
        if _wants_json(request):
            return JsonResponse({"error": message}, status=status)
        return render(
            request,
            "ai/import_upload.html",
            _upload_context(request, restaurant, error=message),
            status=status,
        )

    if not services.is_enabled():
        return fail("AI is disabled: set ANTHROPIC_API_KEY", 503)

    files = request.FILES.getlist("photos")
    if not files:
        return fail("Add at least one photo of your menu.", 400)
    if len(files) > services.MAX_IMAGES:
        return fail(f"Too many photos: at most {services.MAX_IMAGES} pages per import.", 400)

    blobs = [f.read() for f in files]
    types = [f.content_type or "image/jpeg" for f in files]
    try:
        menu = services.extract_menu(blobs, types)
    except services.ImageError as exc:
        return fail(str(exc), 400)
    except services.AIUnavailable as exc:
        return fail(exc.user_message, 503)

    draft = ImportDraft.objects.create(
        restaurant=restaurant, data=drafts.menu_to_draft(menu), page_count=len(files)
    )
    url = _review_url(restaurant, draft)
    if _wants_json(request):
        return JsonResponse({"redirect": url})
    return redirect(url)


def _review_url(restaurant, draft) -> str:
    return reverse("ai:import_review", args=[restaurant.pk, draft.pk])


# --------------------------------------------------------------------------------------
# import: review / save
# --------------------------------------------------------------------------------------
def _review_context(restaurant, draft, data, **extra):
    annotated = drafts.annotate(data, restaurant)
    return {
        "restaurant": restaurant,
        "draft": draft,
        "d": annotated,
        "allergens": [(code, labels["en"]) for code, labels in ALLERGENS.items()],
        "diets": [(code, labels["en"]) for code, labels in DIETS.items()],
        "special_kinds": [(code, labels["en"]) for code, labels in SPECIAL_KINDS.items()],
        "ai_enabled": services.is_enabled(),
        **extra,
    }


@staff_required
@require_http_methods(["GET", "POST"])
def import_review(request, pk, draft_id):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    draft = get_object_or_404(ImportDraft, pk=draft_id, restaurant=restaurant)
    editor_url = _editor_url(restaurant)
    if draft.status != ImportDraft.STATUS_DRAFT:
        messages.info(request, "This import was already saved or discarded.")
        return redirect(editor_url)

    if request.method == "GET":
        return render(request, "ai/import_review.html", _review_context(restaurant, draft, draft.data))

    data = drafts.parse_post(request.POST, draft.data)
    draft.data = data
    draft.save(update_fields=["data", "updated_at"])  # edits survive a reload / error

    if request.POST.get("action") != "save":
        messages.success(request, "Changes kept. Your import is still waiting for review.")
        return redirect(request.path)

    if drafts.count_bad_prices(data):
        return render(
            request,
            "ai/import_review.html",
            _review_context(restaurant, draft, data, show_errors=True),
            status=400,
        )

    translations = None
    warning = ""
    if data["options"].get("translate"):
        try:
            translations = drafts.translate_draft_texts(data)
        except services.AIUnavailable as exc:
            warning = f"Imported without English translation ({exc.user_message})"

    try:
        with transaction.atomic():
            claimed = ImportDraft.objects.filter(pk=draft.pk, status=ImportDraft.STATUS_DRAFT).update(
                status=ImportDraft.STATUS_SAVED
            )
            if not claimed:
                messages.info(request, "This import was already saved.")
                return redirect(editor_url)
            stats = drafts.apply_draft(restaurant, data, translations)
    except drafts.InvalidPrices:
        return render(
            request,
            "ai/import_review.html",
            _review_context(restaurant, draft, data, show_errors=True),
            status=400,
        )

    messages.success(request, _summary(stats))
    if warning:
        messages.warning(request, warning)
    return redirect(editor_url)


def _summary(stats: dict) -> str:
    n, c = stats["items"], stats["categories"]
    text = f"Imported {n} item{'s' if n != 1 else ''} in {c} categor{'ies' if c != 1 else 'y'}"
    if stats["specials"]:
        s = stats["specials"]
        text += f", {s} special{'s' if s != 1 else ''}"
    if stats["info"]:
        text += f" and restaurant info ({', '.join(stats['info'])})"
    return text


def _editor_url(restaurant) -> str:
    return reverse("editor:restaurant_edit", args=[restaurant.pk])


@staff_required
@require_POST
def import_discard(request, pk, draft_id):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    draft = get_object_or_404(ImportDraft, pk=draft_id, restaurant=restaurant)
    if draft.status == ImportDraft.STATUS_DRAFT:
        draft.status = ImportDraft.STATUS_DISCARDED
        draft.save(update_fields=["status", "updated_at"])
        messages.info(request, "Import discarded.")
    return redirect(_editor_url(restaurant))


# --------------------------------------------------------------------------------------
# translation endpoints
# --------------------------------------------------------------------------------------
def _json_error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@require_POST
def translate(request):
    """POST /admin/ai/translate/  {"source","target","texts":{key: text}} -> {"translations": {...}}"""
    user = request.user
    if not user.is_authenticated:
        return _json_error("Authentication required.", 401)
    if not user.is_staff:
        return _json_error("Forbidden.", 403)
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return _json_error("Invalid JSON body.", 400)
    if not isinstance(payload, dict):
        return _json_error("Invalid JSON body.", 400)

    source = payload.get("source", "fr")
    target = payload.get("target", "en")
    texts = payload.get("texts")
    if source not in SUPPORTED_LANGUAGES or target not in SUPPORTED_LANGUAGES or source == target:
        return _json_error("source and target must be two different supported languages.", 400)
    if not isinstance(texts, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in texts.items()
    ):
        return _json_error("'texts' must be an object of string values.", 400)
    if len(texts) > MAX_TRANSLATE_KEYS or sum(len(v) for v in texts.values()) > MAX_TRANSLATE_CHARS:
        return _json_error("Too much text in one request.", 400)

    try:
        translations = services.translate_texts(texts, source, target)
    except services.AIUnavailable as exc:
        return _json_error(exc.user_message, 503)
    return JsonResponse({"translations": translations})


@staff_required
@require_POST
def translate_missing(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    is_htmx = request.headers.get("HX-Request") == "true"
    try:
        count = fill_missing_translations(restaurant)
    except services.AIUnavailable as exc:
        if is_htmx:
            return HttpResponse(
                format_html('<span class="ai-toast ai-toast--error" role="alert">{}</span>', exc.user_message),
                status=503,
            )
        messages.error(request, f"Translation failed: {exc.user_message}")
        return redirect(_editor_url(restaurant))

    message = (
        f"Translated {count} field{'s' if count != 1 else ''}"
        if count
        else "Nothing to translate: every English field is already filled"
    )
    if is_htmx:
        response = HttpResponse(
            format_html('<span class="ai-toast" role="status">{}</span>', message)
        )
        response["HX-Refresh"] = "true"
        return response
    messages.success(request, message)
    return redirect(_editor_url(restaurant))
