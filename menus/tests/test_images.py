from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from menus import images
from menus.models import Item
from menus.tests.factories import image_file, make_image_bytes, make_menu, make_restaurant


def _open(content) -> Image.Image:
    content.seek(0)
    img = Image.open(BytesIO(content.read()))
    img.load()
    return img


def test_process_photo_downsizes_and_outputs_progressive_jpeg():
    out = images.process_photo(image_file(size=(3200, 2400)), "big.png")
    img = _open(out)
    assert out.name == "big.jpg"
    assert img.format == "JPEG"
    assert max(img.size) == 1600
    assert img.size == (1600, 1200)
    assert img.info.get("progressive") or img.info.get("progression")


def test_process_photo_does_not_upscale():
    img = _open(images.process_photo(image_file(size=(300, 200))))
    assert img.size == (300, 200)


def test_process_photo_applies_exif_rotation_and_strips_metadata():
    # 200x100 with orientation=6 (rotate 90 CW) -> displayed as 100x200
    img = _open(images.process_photo(image_file(size=(200, 100), exif_orientation=6)))
    assert img.size == (100, 200)
    assert not img.getexif()
    assert "exif" not in img.info


def test_process_photo_flattens_transparency_onto_white():
    data = ContentFile(make_image_bytes(size=(20, 20), fmt="PNG", mode="RGBA", color=(0, 0, 0, 0)))
    img = _open(images.process_photo(data))
    assert img.mode == "RGB"
    assert img.getpixel((5, 5)) == (255, 255, 255)


def test_process_photo_rejects_non_image():
    with pytest.raises(ValidationError) as exc:
        images.process_photo(ContentFile(b"%PDF-1.4 definitely not an image", name="menu.pdf"))
    assert "not a valid image" in exc.value.messages[0]


def test_process_photo_rejects_truncated_file():
    data = make_image_bytes(size=(400, 300))
    with pytest.raises(ValidationError):
        images.process_photo(ContentFile(data[: len(data) // 3]))


def test_process_photo_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(images, "MAX_UPLOAD_BYTES", 1000)
    with pytest.raises(ValidationError) as exc:
        images.process_photo(ContentFile(b"x" * 2000, name="big.jpg"))
    assert "too large" in exc.value.messages[0]


def test_process_photo_rejects_decompression_bomb(monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 10_000)
    with pytest.raises(ValidationError) as exc:
        images.process_photo(image_file(size=(400, 400)))
    assert "too many pixels" in exc.value.messages[0]


def test_process_photo_rejects_pillow_bomb_warning(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(ValidationError):
        images.process_photo(image_file(size=(400, 400)))


def test_process_logo_keeps_alpha_and_limits_size():
    data = ContentFile(make_image_bytes(size=(1024, 512), fmt="PNG", mode="RGBA", color=(10, 20, 30, 0)))
    out = images.process_logo(data, "Logo.WEBP")
    img = _open(out)
    assert out.name == "Logo.png"
    assert img.format == "PNG"
    assert img.mode == "RGBA"
    assert img.size == (512, 256)
    assert img.getpixel((10, 10))[3] == 0


def test_process_logo_rejects_garbage():
    with pytest.raises(ValidationError):
        images.process_logo(ContentFile(b"nope"))


def test_variant_name():
    assert images.variant_name("photos/3/abc.jpg", 480) == "photos/3/abc.480.webp"
    assert images.variant_name("photos/3/abc", 960) == "photos/3/abc.960.webp"


@pytest.mark.django_db
def test_item_save_creates_webp_variants_and_photo_view():
    _, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Photo"})
    item.photo.save("plat.jpg", images.process_photo(image_file(size=(2000, 1000))), save=True)
    name = item.photo.name
    assert name.startswith(f"photos/{cat.restaurant_id}/plat")
    for w in (480, 960):
        vname = images.variant_name(name, w)
        assert default_storage.exists(vname)
        with default_storage.open(vname, "rb") as fh:
            v = Image.open(fh)
            assert v.format == "WEBP"
            assert v.width == w

    view = images.photo_view(item.photo)
    assert view["src"].endswith(".960.webp")
    assert view["srcset"].count("webp") == 2
    assert "480w" in view["srcset"] and "960w" in view["srcset"]
    assert (view["width"], view["height"]) == (960, 480)


@pytest.mark.django_db
def test_photo_view_lazily_creates_missing_variants():
    _, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Photo"})
    item.photo.save("plat.jpg", images.process_photo(image_file(size=(1200, 800))), save=True)
    name = item.photo.name
    for w in (480, 960):
        default_storage.delete(images.variant_name(name, w))
    from django.core.cache import cache

    cache.clear()
    view = images.photo_view(item.photo)
    assert default_storage.exists(images.variant_name(name, 960))
    assert view["src"].endswith(".960.webp")


@pytest.mark.django_db
def test_small_photo_variants_are_not_upscaled():
    _, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Petit"})
    item.photo.save("small.jpg", images.process_photo(image_file(size=(400, 300))), save=True)
    with default_storage.open(images.variant_name(item.photo.name, 960), "rb") as fh:
        assert Image.open(fh).width == 400
    view = images.photo_view(item.photo)
    assert view["srcset"].count("400w") == 1  # deduplicated
    assert view["width"] == 400


def test_photo_view_none_for_empty():
    assert images.photo_view(None) is None
    assert images.photo_view("") is None


@pytest.mark.django_db
def test_replacing_photo_deletes_old_file_and_variants():
    _, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Photo"})
    item.photo.save("a.jpg", images.process_photo(image_file(size=(1000, 700))), save=True)
    old = item.photo.name
    assert default_storage.exists(old)

    item.photo.save("b.jpg", images.process_photo(image_file(size=(1000, 700))), save=True)
    new = item.photo.name
    assert new != old
    assert not default_storage.exists(old)
    assert not default_storage.exists(images.variant_name(old, 480))
    assert not default_storage.exists(images.variant_name(old, 960))
    assert default_storage.exists(images.variant_name(new, 960))


@pytest.mark.django_db
def test_clearing_photo_deletes_files():
    _, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Photo"})
    item.photo.save("a.jpg", images.process_photo(image_file()), save=True)
    old = item.photo.name
    item = Item.objects.get(pk=item.pk)
    item.photo = ""
    item.save()
    assert not default_storage.exists(old)
    assert not default_storage.exists(images.variant_name(old, 960))


@pytest.mark.django_db
def test_deleting_item_and_restaurant_removes_files():
    restaurant, cat, _ = make_menu(n_items=0)
    a = Item.objects.create(category=cat, name={"fr": "A"})
    b = Item.objects.create(category=cat, name={"fr": "B"})
    a.photo.save("a.jpg", images.process_photo(image_file()), save=True)
    b.photo.save("b.jpg", images.process_photo(image_file()), save=True)
    a_name, b_name = a.photo.name, b.photo.name
    a.delete()
    assert not default_storage.exists(a_name)
    assert not default_storage.exists(images.variant_name(a_name, 480))
    assert default_storage.exists(b_name)
    restaurant.delete()  # cascades to items
    assert not default_storage.exists(b_name)
    assert not default_storage.exists(images.variant_name(b_name, 960))


@pytest.mark.django_db
def test_logo_replaced_and_deleted_files_removed():
    r = make_restaurant()
    r.logo.save("l1.png", images.process_logo(image_file(fmt="PNG", mode="RGBA", name="l.png")), save=True)
    first = r.logo.name
    assert default_storage.exists(first)
    r.logo.save("l2.png", images.process_logo(image_file(fmt="PNG", mode="RGBA", name="l.png")), save=True)
    assert not default_storage.exists(first)
    second = r.logo.name
    assert default_storage.exists(second)
    r.delete()
    assert not default_storage.exists(second)
