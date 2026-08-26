"""Small helpers shared by the test suites."""

from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

from menus.models import Category, DailySpecial, Item, Restaurant


def make_image_bytes(size=(200, 100), fmt="JPEG", mode="RGB", color=(200, 60, 40), exif_orientation=None):
    img = Image.new(mode, size, color if mode in ("RGB", "RGBA") else 128)
    out = BytesIO()
    kwargs = {}
    if exif_orientation:
        exif = img.getexif()
        exif[0x0112] = exif_orientation
        exif[0x010F] = "TestCam"  # Make: must be stripped
        kwargs["exif"] = exif
    img.save(out, fmt, **kwargs)
    return out.getvalue()


def image_file(name="pic.jpg", **kwargs):
    return ContentFile(make_image_bytes(**kwargs), name=name)


def make_restaurant(name="Chez Test", *, published=True, **kwargs):
    return Restaurant.objects.create(name=name, is_published=published, **kwargs)


def make_menu(restaurant=None, n_items=3):
    restaurant = restaurant or make_restaurant()
    cat = Category.objects.create(restaurant=restaurant, name={"fr": "Plats", "en": "Mains"})
    items = [
        Item.objects.create(
            category=cat,
            name={"fr": f"Plat {i}", "en": f"Dish {i}"},
            prices=[{"cents": 1000 + i}],
            position=i,
        )
        for i in range(n_items)
    ]
    DailySpecial.objects.create(
        restaurant=restaurant, kind="plat", title={"fr": "Plat du jour", "en": "Dish of the day"}, prices=[{"cents": 1400}]
    )
    return restaurant, cat, items
