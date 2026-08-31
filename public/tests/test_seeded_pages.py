"""Every demo restaurant renders in both languages, within the query budget, with photo variants."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from menus.models import Item, Restaurant
from public.menu_context import build_menu_context, load_restaurant


@pytest.mark.django_db
def test_all_demo_menus_render(client):
    call_command("seed_demo", stdout=StringIO())
    for restaurant in Restaurant.objects.all():
        for lang in ("fr", "en"):
            with CaptureQueriesContext(connection) as ctx:
                resp = client.get(restaurant.public_path + f"?lang={lang}")
            assert resp.status_code == 200, restaurant.slug
            assert len(ctx) <= 4, (restaurant.slug, len(ctx))
            assert not {"sessionid", "csrftoken"} & set(resp.cookies)


@pytest.mark.django_db
def test_photo_context_uses_webp_variants_and_fallbacks():
    call_command("seed_demo", stdout=StringIO())
    vialle = load_restaurant("maison-vialle")
    ctx = build_menu_context(vialle, "en")["menu"]
    items = [i for c in ctx.categories for i in c.items]
    assert items and all(i.photo for i in items)
    assert all(i.photo.src.endswith(".960.webp") and "480w" in i.photo.srcset for i in items)
    assert Item.objects.filter(category__restaurant__slug="chez-gino").count() >= 75

    # French fallback when an English text is missing
    gino = load_restaurant("chez-gino")
    fr = build_menu_context(gino, "fr")["menu"]
    en = build_menu_context(gino, "en")["menu"]
    fr_names = {i.id: i.name for c in fr.categories for i in c.items}
    en_names = {i.id: i.name for c in en.categories for i in c.items}
    assert fr_names.keys() == en_names.keys()
    assert all(en_names[k] for k in en_names)
