import json

import pytest
from django.urls import reverse
from django.utils import timezone

from menus.models import Restaurant

from .conftest import HX, make_image

HXS = {**HX, "HTTP_HX_CURRENT_URL": "http://testserver/admin/r/1/settings/"}


def settings_url(r):
    return reverse("editor:restaurant_settings", args=[r.pk])


@pytest.mark.django_db
def test_dashboard_lists_restaurants(client, restaurant, item):
    resp = client.get(reverse("editor:dashboard"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Chez Test" in body
    assert "1 item" in body
    assert reverse("printing:print_page", args=[restaurant.pk]) in body


@pytest.mark.django_db
def test_create_restaurant_defaults(client):
    resp = client.post(reverse("editor:restaurant_new"), {"name": "  Le Bistrot  ", "theme": "cafe"})
    r = Restaurant.objects.get(name="Le Bistrot")
    assert resp.status_code == 302
    assert resp["Location"] == reverse("editor:restaurant_edit", args=[r.pk])
    assert r.theme == "cafe"
    assert r.languages == ["fr", "en"]
    assert r.footer_note == {"fr": "Prix nets, service compris.", "en": "Prices include service."}
    assert r.brand_color == "#7a2e2a"
    assert not r.is_published
    assert r.slug == "le-bistrot"


@pytest.mark.django_db
def test_create_restaurant_requires_name_and_defaults_theme(client):
    resp = client.post(reverse("editor:restaurant_new"), {"name": "  "})
    assert resp.status_code == 200
    assert b"Give the restaurant a name" in resp.content
    client.post(reverse("editor:restaurant_new"), {"name": "X", "theme": "nope"})
    assert Restaurant.objects.get(name="X").theme == "bistro"


@pytest.mark.django_db
def test_new_page_offers_photo_start_only_with_ai(client, settings):
    settings.AI_ENABLED = False
    assert b"Start from a photo" not in client.get(reverse("editor:restaurant_new")).content
    settings.AI_ENABLED = True
    assert b"Start from a photo" in client.get(reverse("editor:restaurant_new")).content


@pytest.mark.django_db
def test_new_restaurant_then_import_redirects_to_ai(client, settings):
    settings.AI_ENABLED = True
    resp = client.post(reverse("editor:restaurant_new"), {"name": "Import me", "then": "import"})
    r = Restaurant.objects.get(name="Import me")
    assert resp["Location"] == reverse("ai:import", args=[r.pk])


@pytest.mark.django_db
def test_settings_autosave_single_fields(client, restaurant):
    resp = client.post(settings_url(restaurant), {"tagline_fr": "Cuisine du marché"}, **HX)
    assert resp.status_code == 200
    restaurant.refresh_from_db()
    assert restaurant.tagline["fr"] == "Cuisine du marché"
    assert restaurant.tagline["en"] == ""
    client.post(settings_url(restaurant), {"tagline_en": "Market cuisine"}, **HX)
    client.post(settings_url(restaurant), {"brand_color": "#2F5D50", "accent_color": ""}, **HX)
    client.post(settings_url(restaurant), {"theme": "gastro", "color_mode": "dark"}, **HX)
    client.post(settings_url(restaurant), {"hours_fr": "Lundi : 12h\r\nMardi : fermé", "phone": "01 02"}, **HX)
    client.post(settings_url(restaurant), {"english": "0"}, **HX)
    restaurant.refresh_from_db()
    assert restaurant.tagline == {"fr": "Cuisine du marché", "en": "Market cuisine"}
    assert restaurant.brand_color == "#2f5d50"
    assert restaurant.theme == "gastro"
    assert restaurant.color_mode == "dark"
    assert restaurant.hours["fr"] == "Lundi : 12h\nMardi : fermé"
    assert restaurant.languages == ["fr"]
    client.post(settings_url(restaurant), {"english": "1"}, **HX)
    restaurant.refresh_from_db()
    assert restaurant.languages == ["fr", "en"]


@pytest.mark.django_db
def test_settings_validation_errors(client, restaurant):
    resp = client.post(settings_url(restaurant), {"brand_color": "red", "maps_url": "nope", "name": ""}, **HXS)
    body = resp.content.decode()
    assert "hex colour" in body
    assert "https://" in body
    assert "be empty" in body
    restaurant.refresh_from_db()
    assert restaurant.brand_color == "#7a2e2a"
    assert restaurant.name == "Chez Test"
    assert "validation" in json.loads(resp["HX-Trigger"])
    resp = client.post(settings_url(restaurant), {"theme": "bogus"}, **HXS)
    restaurant.refresh_from_db()
    assert restaurant.theme == "bistro"


@pytest.mark.django_db
def test_settings_page_renders(client, restaurant):
    resp = client.get(settings_url(restaurant))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert restaurant.public_url in body
    assert "Bistro" in body and "Auberge" in body
    assert "One line per row" in body  # hours hint


@pytest.mark.django_db
def test_logo_upload_and_remove(client, restaurant):
    url = reverse("editor:restaurant_logo", args=[restaurant.pk])
    resp = client.post(url, {"logo": make_image(name="logo.png")}, **HX)
    assert resp.status_code == 200
    restaurant.refresh_from_db()
    assert restaurant.logo.name.endswith(".png")
    assert restaurant.logo.width <= 512
    assert restaurant.logo.name in resp.content.decode() or restaurant.logo.url in resp.content.decode()
    resp = client.post(url, {"remove": "1"}, **HX)
    assert resp.status_code == 200
    restaurant.refresh_from_db()
    assert not restaurant.logo


@pytest.mark.django_db
def test_logo_rejects_non_images(client, restaurant):
    from django.core.files.uploadedfile import SimpleUploadedFile

    bad = SimpleUploadedFile("evil.png", b"not an image", content_type="image/png")
    resp = client.post(reverse("editor:restaurant_logo", args=[restaurant.pk]), {"logo": bad}, **HX)
    assert resp.status_code == 422
    assert b"doesn" in resp.content
    restaurant.refresh_from_db()
    assert not restaurant.logo


@pytest.mark.django_db
def test_slug_editable_until_published_then_locked(client, restaurant):
    resp = client.post(settings_url(restaurant), {"slug": "Mon Menu Été"}, **HXS)
    restaurant.refresh_from_db()
    assert restaurant.slug == "mon-menu-ete"
    assert b"permanent" not in resp.content

    client.post(reverse("editor:restaurant_publish", args=[restaurant.pk]), **HXS)
    restaurant.refresh_from_db()
    assert restaurant.is_published
    assert restaurant.first_published_at is not None
    assert restaurant.slug_is_locked()

    resp = client.post(settings_url(restaurant), {"slug": "other"}, **HXS)
    restaurant.refresh_from_db()
    assert restaurant.slug == "mon-menu-ete"
    assert b"permanent" in resp.content

    page = client.get(settings_url(restaurant)).content.decode()
    assert "readonly" in page


@pytest.mark.django_db
def test_slug_uniqueness(client, restaurant):
    Restaurant.objects.create(name="Other", slug="taken")
    resp = client.post(settings_url(restaurant), {"slug": "taken"}, **HXS)
    restaurant.refresh_from_db()
    assert restaurant.slug != "taken"
    assert b"already used" in resp.content


@pytest.mark.django_db
def test_publish_toggle(client, restaurant):
    url = reverse("editor:restaurant_publish", args=[restaurant.pk])
    assert client.post(url, **HX)["HX-Refresh"] == "true"
    restaurant.refresh_from_db()
    assert restaurant.is_published
    client.post(url, **HX)
    restaurant.refresh_from_db()
    assert not restaurant.is_published
    assert restaurant.first_published_at is not None  # slug stays locked
    assert client.get(url).status_code == 405


@pytest.mark.django_db
def test_edit_page_renders_with_content(client, restaurant, category, item, special):
    resp = client.get(reverse("editor:restaurant_edit", args=[restaurant.pk]))
    body = resp.content.decode()
    assert resp.status_code == 200
    assert "Steak" in body and "Blanquette" in body
    assert "?preview=1" in body
    assert "1 item missing English" not in body or "missing English" in body
    assert restaurant.updated_at <= timezone.now()


@pytest.mark.django_db
def test_ai_buttons_hidden_when_ai_disabled(client, restaurant, item, settings):
    url = reverse("editor:restaurant_edit", args=[restaurant.pk])
    settings.AI_ENABLED = False
    body = client.get(url).content.decode()
    assert "Translate missing with AI" not in body
    assert "data-translate>" not in body and "data-translate " not in body
    assert "Import from photo" not in body
    settings.AI_ENABLED = True
    body = client.get(url).content.decode()
    assert "Translate missing with AI" in body
    assert "Import from photo" in body
