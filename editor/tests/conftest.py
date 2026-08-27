import io

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from menus.models import Category, DailySpecial, Item, Restaurant


@pytest.fixture(autouse=True)
def _clean_cache_and_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user("boss", password="s3cret-pass-123", is_staff=True)


@pytest.fixture
def client(client, staff):
    client.force_login(staff)
    return client


@pytest.fixture
def anon(client):
    from django.test import Client

    return Client()


@pytest.fixture
def restaurant(db):
    return Restaurant.objects.create(name="Chez Test")


@pytest.fixture
def category(restaurant):
    return Category.objects.create(restaurant=restaurant, name={"fr": "Plats", "en": ""}, position=0)


@pytest.fixture
def category2(restaurant):
    return Category.objects.create(restaurant=restaurant, name={"fr": "Desserts", "en": ""}, position=1)


@pytest.fixture
def item(category):
    return Item.objects.create(
        category=category, name={"fr": "Steak", "en": ""}, prices=[{"cents": 1800}], position=0
    )


@pytest.fixture
def special(restaurant):
    return DailySpecial.objects.create(restaurant=restaurant, kind="plat", title={"fr": "Blanquette", "en": ""})


def make_image(fmt="PNG", size=(800, 600), color=(200, 30, 30), name="pic.png", content_type="image/png"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


@pytest.fixture
def image_file():
    return make_image()


HX = {"HTTP_HX_REQUEST": "true"}
