import io

from PIL import Image

from printing.qr import (
    MIN_CONTRAST,
    contrast_ratio,
    make_qr_png,
    make_qr_svg,
    make_qr_svg_inline,
    normalize_hex,
    resolve_color,
    safe_qr_color,
)

URL = "https://menu.example.fr/m/le-bistrot/"


def test_dark_brand_colour_kept():
    assert safe_qr_color("#7a2e2a") == "#7a2e2a"
    assert contrast_ratio("#7a2e2a", "#ffffff") >= MIN_CONTRAST


def test_pale_brand_colour_is_darkened_to_meet_contrast():
    pale = "#f2d98a"
    assert contrast_ratio(pale, "#ffffff") < MIN_CONTRAST
    safe = safe_qr_color(pale)
    assert safe != pale
    assert contrast_ratio(safe, "#ffffff") >= MIN_CONTRAST


def test_mid_tone_colours_are_darkened():
    for color in ("#ff0000", "#00a0ff", "#ffa500", "#3cb371"):
        assert contrast_ratio(safe_qr_color(color), "#ffffff") >= MIN_CONTRAST


def test_invalid_colour_falls_back_to_near_black():
    for bad in ("", None, "red", "#12", "#gggggg"):
        assert contrast_ratio(safe_qr_color(bad), "#ffffff") >= MIN_CONTRAST


def test_colour_lighter_than_background_falls_back_to_dark():
    assert safe_qr_color("#ffffff", "#ffffff") in ("#111111", "#000000")


def test_short_hex_is_expanded():
    assert normalize_hex("#abc") == "#aabbcc"


def test_resolve_color_modes():
    assert resolve_color("black", "#7a2e2a") == "#000000"
    assert resolve_color("brand", "#7a2e2a") == "#7a2e2a"
    assert resolve_color(None, "#7a2e2a") == "#000000"


def test_svg_document_and_inline():
    doc = make_qr_svg(URL, "#7a2e2a")
    assert doc.startswith("<?xml")
    assert "<svg" in doc and "#7a2e2a" in doc
    inline = make_qr_svg_inline(URL, "#f2d98a")
    assert inline.lstrip().startswith("<svg")
    assert "#f2d98a" not in inline  # pale colour was replaced by a scannable one


def test_png_quiet_zone_and_size():
    import segno

    data = make_qr_png(URL, size_px=512)
    im = Image.open(io.BytesIO(data)).convert("RGB")
    assert im.width == im.height >= 512
    modules = segno.make(URL, error="q", micro=False).symbol_size(border=4)[0]
    scale = im.width // modules
    assert scale * modules == im.width
    # the outer 4 modules are quiet zone: pure background
    for x in range(0, im.width, 5):
        for y in range(4 * scale):
            assert im.getpixel((x, y)) == (255, 255, 255)
            assert im.getpixel((y, x)) == (255, 255, 255)
