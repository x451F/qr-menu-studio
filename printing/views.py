"""QR downloads, print page and PDF endpoints (all login required)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from menus.models import Restaurant

from . import pdf
from .qr import make_qr_png, make_qr_svg, make_qr_svg_inline, resolve_color, safe_qr_color

PNG_SIZES = (512, 1024, 2048)
DEFAULT_PNG_SIZE = 1024
MAX_PNG_SIZE = 4096


def _color_mode(request, default: str = "brand") -> str:
    mode = request.GET.get("color", default)
    return mode if mode in ("brand", "black") else default


def _file_response(request, data: bytes | str, content_type: str, filename: str) -> HttpResponse:
    response = HttpResponse(data, content_type=content_type)
    disposition = "inline" if request.GET.get("inline") else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    return response


def _int_param(request, name: str, default: int, allowed: tuple[int, ...] | None = None) -> int:
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default
    if allowed is not None and value not in allowed:
        return default
    return value


@login_required
@require_GET
def qr_svg(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    color = resolve_color(_color_mode(request, "black"), restaurant.brand_color)
    svg = make_qr_svg(restaurant.public_url, color)
    return _file_response(request, svg, "image/svg+xml", f"qr-{restaurant.slug}.svg")


@login_required
@require_GET
def qr_png(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    color = resolve_color(_color_mode(request, "black"), restaurant.brand_color)
    size = min(max(_int_param(request, "size", DEFAULT_PNG_SIZE), 128), MAX_PNG_SIZE)
    png = make_qr_png(restaurant.public_url, color=color, size_px=size)
    return _file_response(request, png, "image/png", f"qr-{restaurant.slug}-{size}px.png")


@login_required
@require_GET
@xframe_options_sameorigin
def stickers_pdf(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    size = _int_param(request, "size", 70, pdf.STICKER_SIZES_MM)
    shape = request.GET.get("shape", "square")
    data = pdf.render_stickers(
        restaurant,
        size_mm=size,
        shape=shape if shape in pdf.STICKER_SHAPES else "square",
        color_mode=_color_mode(request),
        text=request.GET.get("text", ""),
    )
    name = f"autocollants-{size // 10}cm-{restaurant.slug}.pdf"
    return _file_response(request, data, "application/pdf", name)


@login_required
@require_GET
@xframe_options_sameorigin
def tent_pdf(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    fmt = request.GET.get("format", "a5").lower()
    fmt = fmt if fmt in pdf.TENT_FORMATS else "a5"
    data = pdf.render_tent(
        restaurant,
        fmt=fmt,
        color_mode=_color_mode(request),
        line=request.GET.get("line", ""),
    )
    name = f"chevalet-{fmt}-{restaurant.slug}.pdf"
    return _file_response(request, data, "application/pdf", name)


@login_required
@require_GET
def print_page(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)
    brand_qr = safe_qr_color(restaurant.brand_color)
    context = {
        "restaurant": restaurant,
        "public_url": restaurant.public_url,
        "short_url": pdf.short_url(restaurant.public_url),
        "qr_svg": make_qr_svg_inline(restaurant.public_url, brand_qr),
        "qr_svg_black": make_qr_svg_inline(restaurant.public_url, "#000000"),
        "brand_qr_color": brand_qr,
        "brand_adjusted": brand_qr.lower() != (restaurant.brand_color or "").lower(),
        "png_sizes": PNG_SIZES,
        "sticker_sizes": [(mm, f"{mm // 10} cm") for mm in pdf.STICKER_SIZES_MM],
        "urls": {
            "qr_svg": reverse("printing:qr_svg", args=[restaurant.pk]),
            "qr_png": reverse("printing:qr_png", args=[restaurant.pk]),
            "stickers": reverse("printing:stickers_pdf", args=[restaurant.pk]),
            "tent": reverse("printing:tent_pdf", args=[restaurant.pk]),
        },
        "max_line": pdf.MAX_LINE_LEN,
        "max_sticker_text": pdf.MAX_STICKER_TEXT_LEN,
    }
    return render(request, "printing/print_page.html", context)
