import re
import zlib

import pytest
from django.urls import reverse

from menus.models import Restaurant


def pdf_pages(data: bytes) -> tuple[int, list[float]]:
    """(page count, MediaBox of first page) read from the (compressed) page tree."""
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            text = zlib.decompress(m.group(1))
        except zlib.error:
            continue
        count = re.search(rb"/Count (\d+)", text)
        box = re.search(rb"/MediaBox \[([^\]]*)\]", text)
        if count and box:
            return int(count.group(1)), [float(v) for v in box.group(1).split()]
    raise AssertionError("no page tree found")


@pytest.fixture
def restaurant(db):
    return Restaurant.objects.create(
        name="Auberge de la Vallée de la Dordogne et des Gorges",
        brand_color="#f2d98a",
        is_published=True,
    )


@pytest.fixture
def logged(client, django_user_model):
    django_user_model.objects.create_user("admin", password="pw-devpassword-123")
    client.login(username="admin", password="pw-devpassword-123")
    return client


PDF_URLS = ["printing:stickers_pdf", "printing:tent_pdf"]
ALL_URLS = ["printing:print_page", "printing:qr_svg", "printing:qr_png", *PDF_URLS]


@pytest.mark.parametrize("name", ALL_URLS)
def test_login_required(client, restaurant, name):
    response = client.get(reverse(name, args=[restaurant.pk]))
    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.parametrize("name", ALL_URLS)
def test_unknown_restaurant_is_404(logged, name):
    assert logged.get(reverse(name, args=[9999])).status_code == 404


def test_qr_svg(logged, restaurant):
    response = logged.get(reverse("printing:qr_svg", args=[restaurant.pk]) + "?color=brand")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert f'filename="qr-{restaurant.slug}.svg"' in response["Content-Disposition"]
    assert response["Content-Disposition"].startswith("attachment")
    assert b"<svg" in response.content


def test_qr_svg_inline_flag(logged, restaurant):
    response = logged.get(reverse("printing:qr_svg", args=[restaurant.pk]) + "?inline=1")
    assert response["Content-Disposition"].startswith("inline")


def test_qr_png_sizes(logged, restaurant):
    import io

    from PIL import Image

    for size in (512, 1024, 2048):
        response = logged.get(reverse("printing:qr_png", args=[restaurant.pk]), {"size": size})
        assert response.status_code == 200
        assert response["Content-Type"] == "image/png"
        assert response.content.startswith(b"\x89PNG")
        assert Image.open(io.BytesIO(response.content)).width >= size
    # absurd sizes are clamped, garbage falls back to the default
    big = logged.get(reverse("printing:qr_png", args=[restaurant.pk]), {"size": 999999})
    assert Image.open(io.BytesIO(big.content)).width < 5000
    assert logged.get(reverse("printing:qr_png", args=[restaurant.pk]), {"size": "x"}).status_code == 200


def test_print_page_published_has_no_warning(logged, restaurant):
    response = logged.get(reverse("printing:print_page", args=[restaurant.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert restaurant.public_url in html
    assert "not published yet" not in html
    assert "stickers.pdf" in html and "tent.pdf" in html and "qr.png" in html and "qr.svg" in html


def test_print_page_unpublished_shows_warning(logged, restaurant):
    Restaurant.objects.filter(pk=restaurant.pk).update(is_published=False)
    response = logged.get(reverse("printing:print_page", args=[restaurant.pk]))
    assert "not published yet" in response.content.decode()


@pytest.mark.parametrize("size", [50, 70, 100])
@pytest.mark.parametrize("shape", ["square", "round"])
def test_stickers_pdf(logged, restaurant, size, shape):
    response = logged.get(
        reverse("printing:stickers_pdf", args=[restaurant.pk]),
        {"size": size, "shape": shape, "text": "Wi-Fi : demandez le code"},
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert response["Content-Disposition"].startswith("attachment")
    assert restaurant.slug in response["Content-Disposition"]
    pages, box = pdf_pages(response.content)
    assert pages == 1
    assert abs(box[2] - 595.3) < 1 and abs(box[3] - 841.9) < 1


@pytest.mark.parametrize("fmt,landscape", [("a5", False), ("a6", True)])
def test_tent_pdf(logged, restaurant, fmt, landscape):
    response = logged.get(
        reverse("printing:tent_pdf", args=[restaurant.pk]),
        {"format": fmt, "line": "Plat du jour à l'ardoise", "color": "black"},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response["Content-Disposition"].startswith("attachment")
    assert f"chevalet-{fmt}-{restaurant.slug}.pdf" in response["Content-Disposition"]
    pages, box = pdf_pages(response.content)
    assert pages == 1
    assert (box[2] > box[3]) is landscape


def test_pdf_inline_preview(logged, restaurant):
    response = logged.get(reverse("printing:tent_pdf", args=[restaurant.pk]), {"inline": 1})
    assert response["Content-Disposition"].startswith("inline")


def test_pdf_bad_options_fall_back_to_defaults(logged, restaurant):
    response = logged.get(
        reverse("printing:stickers_pdf", args=[restaurant.pk]),
        {"size": "999", "shape": "star", "color": "neon"},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    response = logged.get(reverse("printing:tent_pdf", args=[restaurant.pk]), {"format": "a3"})
    assert response.status_code == 200


def test_sticker_grid_fits_on_page():
    from printing.pdf import A4_H, A4_W, STICKER_SIZES_MM, sticker_grid

    expected = {50: 15, 70: 6, 100: 2}
    for size in STICKER_SIZES_MM:
        cells = sticker_grid(size)
        assert len(cells) == expected[size]
        for x, y in cells:
            assert x >= 8 and y >= 8
            assert x + size <= A4_W - 8 and y + size <= A4_H - 8
