"""POST /admin/ai/translate/ and POST /admin/r/<pk>/translate-missing/."""

import json

from django.contrib.messages import get_messages
from django.urls import reverse

from menus.models import Category, DailySpecial, Item

URL = "ai:translate"


def _post_json(client, payload, **extra):
    return client.post(reverse(URL), json.dumps(payload), content_type="application/json", **extra)


# ------------------------------------------------------------------ /admin/ai/translate/


def test_translate_contract(fake_ai, staff_client):
    resp = _post_json(
        staff_client,
        {"source": "fr", "target": "en", "texts": {"cat": "Entrées", "dish": "Pâté maison", "empty": ""}},
    )
    assert resp.status_code == 200
    assert resp.json() == {"translations": {"cat": "Starters", "dish": "[EN] Pâté maison", "empty": ""}}


def test_translate_defaults_to_fr_en(fake_ai, staff_client):
    assert _post_json(staff_client, {"texts": {"a": "Fromages"}}).json() == {"translations": {"a": "Cheese"}}


def test_translate_disabled_returns_503_json(no_ai, staff_client):
    resp = _post_json(staff_client, {"source": "fr", "target": "en", "texts": {"a": "Bonjour"}})
    assert resp.status_code == 503
    assert "ANTHROPIC_API_KEY" in resp.json()["error"]


def test_translate_ai_failure_returns_503(fake_ai, staff_client, monkeypatch):
    from ai import services

    def boom(*a, **kw):
        raise services.AIUnavailable("The AI service is temporarily unavailable.")

    monkeypatch.setattr(services, "translate_texts", boom)
    resp = _post_json(staff_client, {"texts": {"a": "x"}})
    assert resp.status_code == 503 and resp.json() == {"error": "The AI service is temporarily unavailable."}


def test_translate_validates_input(fake_ai, staff_client):
    assert _post_json(staff_client, {"texts": "nope"}).status_code == 400
    assert _post_json(staff_client, {"texts": {"a": 1}}).status_code == 400
    assert _post_json(staff_client, {"source": "fr", "target": "fr", "texts": {"a": "x"}}).status_code == 400
    assert _post_json(staff_client, {"source": "fr", "target": "de", "texts": {"a": "x"}}).status_code == 400
    bad = staff_client.post(reverse(URL), "{not json", content_type="application/json")
    assert bad.status_code == 400 and "error" in bad.json()


def test_translate_requires_post_login_and_csrf(fake_ai, client, django_user_model):
    assert _post_json(client, {"texts": {"a": "x"}}).status_code == 401
    client.force_login(django_user_model.objects.create_user("plain", password="pw-for-tests-123"))
    assert _post_json(client, {"texts": {"a": "x"}}).status_code == 403

    from django.test import Client

    staff = django_user_model.objects.create_user("boss", password="pw-for-tests-123", is_staff=True)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(staff)
    assert _post_json(strict, {"texts": {"a": "x"}}).status_code == 403  # CSRF token missing

    assert client.get(reverse(URL)).status_code == 405


# ------------------------------------------------------------------ translate-missing


def _menu(restaurant):
    restaurant.tagline = {"fr": "Cuisine du marché", "en": ""}
    restaurant.hours = {"fr": "Fermé le lundi", "en": "Closed on Mondays"}  # already translated
    restaurant.footer_note = {"fr": "Prix nets, service compris", "en": ""}
    restaurant.save()
    starters = Category.objects.create(restaurant=restaurant, name={"fr": "Entrées", "en": ""}, position=0)
    mains = Category.objects.create(restaurant=restaurant, name={"fr": "Plats", "en": "Hand-written mains"}, position=1)
    Category.objects.create(restaurant=restaurant, name={"fr": "", "en": ""}, position=2)  # nothing to translate
    Item.objects.create(
        category=starters,
        name={"fr": "Terrine de campagne maison", "en": ""},
        description={"fr": "Cornichons", "en": ""},
        prices=[{"label": {"fr": "le verre", "en": ""}, "cents": 550}, {"label": {"fr": "", "en": ""}, "cents": 900}],
        position=0,
    )
    Item.objects.create(
        category=mains,
        name={"fr": "Entrecôte grillée", "en": "My own English"},
        description={"fr": "Sauce au poivre", "en": ""},
        position=0,
    )
    DailySpecial.objects.create(
        restaurant=restaurant, kind="formule", title={"fr": "Formule du midi", "en": ""}, position=0
    )


def test_translate_missing_only_fills_empty_english(fake_ai, staff_client, restaurant):
    _menu(restaurant)
    before = restaurant.updated_at
    resp = staff_client.post(reverse("ai:translate_missing", args=[restaurant.pk]), follow=True)

    assert resp.redirect_chain[-1][0] == reverse("editor:restaurant_edit", args=[restaurant.pk])
    restaurant.refresh_from_db()
    assert restaurant.tagline["en"] == "[EN] Cuisine du marché"
    assert restaurant.footer_note["en"] == "Prices include service"
    assert restaurant.hours == {"fr": "Fermé le lundi", "en": "Closed on Mondays"}  # untouched
    assert Category.objects.get(name__fr="Entrées").name["en"] == "Starters"
    assert Category.objects.get(name__fr="Plats").name["en"] == "Hand-written mains"  # untouched
    terrine = Item.objects.get(name__fr="Terrine de campagne maison")
    assert terrine.name["en"] == "Homemade country terrine"
    assert terrine.description["en"] == "[EN] Cornichons"
    assert terrine.prices[0]["label"] == {"fr": "le verre", "en": "glass"}
    assert terrine.prices[1]["label"] == {"fr": "", "en": ""}
    assert Item.objects.get(name__fr="Entrecôte grillée").name["en"] == "My own English"
    assert Item.objects.get(name__fr="Entrecôte grillée").description["en"] == "[EN] Sauce au poivre"
    assert DailySpecial.objects.get().title["en"] == "Lunch set menu"
    assert restaurant.updated_at > before

    (msg,) = [m.message for m in get_messages(resp.wsgi_request)]
    assert msg == "Translated 8 fields"


def test_translate_missing_is_idempotent(fake_ai, staff_client, restaurant):
    _menu(restaurant)
    url = reverse("ai:translate_missing", args=[restaurant.pk])
    staff_client.post(url)
    resp = staff_client.post(url, follow=True)
    assert "Nothing to translate" in [m.message for m in get_messages(resp.wsgi_request)][-1]


def test_translate_missing_htmx_fragment(fake_ai, staff_client, restaurant):
    _menu(restaurant)
    resp = staff_client.post(reverse("ai:translate_missing", args=[restaurant.pk]), HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert resp["HX-Refresh"] == "true"
    assert "Translated 8 fields" in resp.content.decode()


def test_translate_missing_disabled(no_ai, staff_client, restaurant):
    _menu(restaurant)
    url = reverse("ai:translate_missing", args=[restaurant.pk])
    htmx = staff_client.post(url, HTTP_HX_REQUEST="true")
    assert htmx.status_code == 503 and "ANTHROPIC_API_KEY" in htmx.content.decode()
    resp = staff_client.post(url, follow=True)
    assert "ANTHROPIC_API_KEY" in [m.message for m in get_messages(resp.wsgi_request)][0]
    restaurant.refresh_from_db()
    assert restaurant.tagline["en"] == ""  # nothing written


def test_translate_missing_requires_post_and_login(fake_ai, client, restaurant):
    url = reverse("ai:translate_missing", args=[restaurant.pk])
    assert client.post(url).status_code == 302  # login redirect
    assert client.get(url).status_code in (302, 405)
