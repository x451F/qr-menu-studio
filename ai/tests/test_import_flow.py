"""Upload -> review -> save flow (fake AI mode, no network)."""

import io

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from ai.models import ImportDraft
from menus.models import Category, DailySpecial, Item


def _upload(client, restaurant, jpeg, **extra):
    f = io.BytesIO(jpeg)
    f.name = "menu.jpg"
    return client.post(reverse("ai:import", args=[restaurant.pk]), {"photos": [f]}, **extra)


def _review_post(draft, **overrides):
    """A browser-like POST of an untouched review form (everything ticked)."""
    post = {
        "action": "save",
        "opt_merge": "on",
        "opt_specials": "on",
        "opt_info_phone": "on",
        "opt_info_address": "on",
        "opt_info_hours": "on",
    }
    for ci, cat in enumerate(draft.data["categories"]):
        post[f"c{ci}_on"] = "on"
        post[f"c{ci}_name"] = cat["name"]
        post[f"c{ci}_desc"] = cat["description"]
        for ii, item in enumerate(cat["items"]):
            k = f"c{ci}i{ii}"
            post[f"{k}_on"] = "on"
            post[f"{k}_name"] = item["name"]
            post[f"{k}_desc"] = item["description"]
            post[f"{k}_al"] = item["allergens"]
            post[f"{k}_di"] = item["diets"]
            for pi, p in enumerate(item["prices"]):
                post[f"{k}p{pi}_label"] = p["label"]
                post[f"{k}p{pi}_text"] = p["text"]
    for si, sp in enumerate(draft.data["specials"]):
        k = f"s{si}"
        post.update({f"{k}_on": "on", f"{k}_kind": sp["kind"], f"{k}_title": sp["title"], f"{k}_desc": sp["description"]})
        for pi, p in enumerate(sp["prices"]):
            post[f"{k}p{pi}_label"], post[f"{k}p{pi}_text"] = p["label"], p["text"]
    post.update(overrides)
    return post


@pytest.fixture
def draft(fake_ai, staff_client, restaurant, sample_jpeg):
    resp = _upload(staff_client, restaurant, sample_jpeg)
    assert resp.status_code == 302
    return ImportDraft.objects.get(restaurant=restaurant)


def _fix_bad_price(post):
    for key, value in post.items():
        if isinstance(value, str) and value == "selon arrivage":
            post[key] = "19,50"
    return post


# ------------------------------------------------------------------ access


def test_anonymous_is_redirected_to_login(client, restaurant):
    resp = client.get(reverse("ai:import", args=[restaurant.pk]))
    assert resp.status_code == 302 and "login" in resp["Location"]


def test_non_staff_is_forbidden(client, restaurant, django_user_model):
    client.force_login(django_user_model.objects.create_user("plain", password="pw-for-tests-123"))
    assert client.get(reverse("ai:import", args=[restaurant.pk])).status_code == 403


# ------------------------------------------------------------------ disabled mode


def test_disabled_shows_explanation_and_link_back(no_ai, staff_client, restaurant):
    resp = staff_client.get(reverse("ai:import", args=[restaurant.pk]))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "ANTHROPIC_API_KEY" in body
    assert reverse("editor:restaurant_edit", args=[restaurant.pk]) in body
    assert 'type="file"' not in body


def test_disabled_post_does_not_crash(no_ai, staff_client, restaurant, sample_jpeg):
    resp = _upload(staff_client, restaurant, sample_jpeg)
    assert resp.status_code == 503
    assert "ANTHROPIC_API_KEY" in resp.content.decode()
    resp = _upload(staff_client, restaurant, sample_jpeg, HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code == 503 and "AI is disabled" in resp.json()["error"]
    assert not ImportDraft.objects.exists()


# ------------------------------------------------------------------ upload


def test_upload_page_has_camera_and_multi_file_inputs(fake_ai, staff_client, restaurant):
    body = staff_client.get(reverse("ai:import", args=[restaurant.pk])).content.decode()
    assert 'capture="environment"' in body and "multiple" in body and 'accept="image/*"' in body
    assert "Reading your menu" in body and "20&ndash;60" in body


def test_upload_creates_draft_and_redirects(fake_ai, staff_client, restaurant, sample_jpeg):
    resp = _upload(staff_client, restaurant, sample_jpeg, HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code == 200
    draft = ImportDraft.objects.get()
    assert resp.json()["redirect"] == reverse("ai:import_review", args=[restaurant.pk, draft.pk])
    assert len(draft.data["categories"]) == 3


def test_upload_rejects_bad_files(fake_ai, staff_client, restaurant):
    resp = staff_client.post(
        reverse("ai:import", args=[restaurant.pk]),
        {"photos": [io.BytesIO(b"not an image")]},
        HTTP_X_REQUESTED_WITH="fetch",
    )
    assert resp.status_code == 400 and "readable image" in resp.json()["error"]
    resp = staff_client.post(reverse("ai:import", args=[restaurant.pk]), {}, HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code == 400


def test_upload_shows_friendly_error_when_ai_fails(real_ai, staff_client, restaurant, sample_jpeg, monkeypatch):
    from ai import services

    def boom(*a, **kw):
        raise services.AIUnavailable("The AI service is rate-limited right now.")

    monkeypatch.setattr(services, "extract_menu", boom)
    resp = _upload(staff_client, restaurant, sample_jpeg)
    assert resp.status_code == 503
    assert "rate-limited" in resp.content.decode() and 'type="file"' in resp.content.decode()


def test_resume_link_shown_for_pending_draft(draft, staff_client, restaurant):
    body = staff_client.get(reverse("ai:import", args=[restaurant.pk])).content.decode()
    assert reverse("ai:import_review", args=[restaurant.pk, draft.pk]) in body


# ------------------------------------------------------------------ review


def test_review_renders_and_flags_unreadable_price(draft, staff_client, restaurant):
    resp = staff_client.get(reverse("ai:import_review", args=[restaurant.pk, draft.pk]))
    body = resp.content.decode()
    assert resp.status_code == 200
    assert "Soupe à l&#x27;oignon gratinée" in body or "Soupe à l'oignon gratinée" in body
    assert "Couldn&rsquo;t read this price" in body or "Couldn’t read this price" in body
    assert body.count('class="ai-cat__head"') == 3
    assert 'value="selon arrivage"' in body


def test_save_blocks_on_unreadable_price_and_keeps_edits(draft, staff_client, restaurant):
    url = reverse("ai:import_review", args=[restaurant.pk, draft.pk])
    post = _review_post(draft, c0_name="Nos entrées")
    resp = staff_client.post(url, post)
    assert resp.status_code == 400
    assert "1 price couldn" in resp.content.decode()
    assert not Item.objects.exists()
    draft.refresh_from_db()
    assert draft.status == ImportDraft.STATUS_DRAFT
    assert draft.data["categories"][0]["name"] == "Nos entrées"  # edit survived


def test_save_creates_rows_with_parsed_prices(draft, staff_client, restaurant):
    url = reverse("ai:import_review", args=[restaurant.pk, draft.pk])
    post = _fix_bad_price(_review_post(draft))
    resp = staff_client.post(url, post, follow=True)

    assert [m.message for m in get_messages(resp.wsgi_request)][0].startswith("Imported 12 items in 3 categories")
    assert resp.redirect_chain[-1][0] == reverse("editor:restaurant_edit", args=[restaurant.pk])

    cats = list(Category.objects.filter(restaurant=restaurant))
    assert [c.name["fr"] for c in cats] == ["Entrées", "Plats", "Desserts et boissons"]
    assert all(c.name["en"] == "" for c in cats)  # French only unless translate ticked
    items = {i.name["fr"]: i for i in Item.objects.all()}
    assert len(items) == 12
    assert items["Soupe à l'oignon gratinée"].prices == [{"label": {"fr": "", "en": ""}, "cents": 850}]
    assert items["Terrine de campagne maison"].prices[0]["cents"] == 950  # "9€50"
    assert items["Tarte Tatin, crème fraîche"].prices[0]["cents"] == 800  # "8€"
    assert [(p["label"]["fr"], p["cents"]) for p in items["Entrecôte grillée"].prices] == [("250 g", 2100), ("400 g", 2900)]
    assert [(p["label"]["fr"], p["cents"]) for p in items["Cahors, Château Lamartine"].prices] == [
        ("le verre", 550),
        ("la bouteille", 2600),
    ]
    assert items["Andouillette de Troyes AAAAA"].prices[0]["cents"] == 1950
    assert items["Soupe à l'oignon gratinée"].allergens == ["gluten", "milk"]
    assert items["Soupe à l'oignon gratinée"].diets == ["vegetarian"]
    assert items["Foie gras de canard mi-cuit"].allergens == []  # never guessed

    specials = list(DailySpecial.objects.filter(restaurant=restaurant))
    assert [s.kind for s in specials] == ["plat", "formule"] and specials[0].prices[0]["cents"] == 1450

    restaurant.refresh_from_db()
    assert restaurant.phone == "05 55 12 34 56"
    assert restaurant.address.startswith("8 rue du Marché")
    assert restaurant.hours["fr"].startswith("Mardi")
    draft.refresh_from_db()
    assert draft.status == ImportDraft.STATUS_SAVED


def test_save_bumps_content_version(draft, staff_client, restaurant):
    before = restaurant.updated_at
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), _fix_bad_price(_review_post(draft)))
    restaurant.refresh_from_db()
    assert restaurant.updated_at > before


def test_untick_item_category_and_specials(draft, staff_client, restaurant):
    post = _fix_bad_price(_review_post(draft))
    del post["c1i4_on"]  # Andouillette
    del post["c2_on"]  # whole "Desserts et boissons"
    del post["opt_specials"]
    del post["s0_on"]
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post)
    assert Item.objects.count() == 4 + 4
    assert Category.objects.count() == 2
    assert not DailySpecial.objects.exists()


def test_info_only_imported_into_empty_fields(draft, staff_client, restaurant):
    restaurant.phone = "01 02 03 04 05"
    restaurant.address = "1 rue existante"
    restaurant.save()
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), _fix_bad_price(_review_post(draft)))
    restaurant.refresh_from_db()
    assert restaurant.phone == "01 02 03 04 05" and restaurant.address == "1 rue existante"
    assert restaurant.hours["fr"].startswith("Mardi")  # was empty


def test_info_not_imported_when_unticked(draft, staff_client, restaurant):
    post = _fix_bad_price(_review_post(draft))
    for f in ("phone", "address", "hours"):
        del post[f"opt_info_{f}"]  # unticked
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post)
    restaurant.refresh_from_db()
    assert restaurant.phone == "" and restaurant.hours["fr"] == ""


def test_appends_to_existing_category_with_same_name(draft, staff_client, restaurant):
    existing = Category.objects.create(restaurant=restaurant, name={"fr": "entrees", "en": "Starters"}, position=0)
    Item.objects.create(category=existing, name={"fr": "Déjà là", "en": ""}, position=0)
    draft.data["categories"][0]["name"] = "Entrées"
    draft.save()
    post = _fix_bad_price(_review_post(draft))
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post)
    assert Category.objects.filter(restaurant=restaurant).count() == 3  # merged, not 4
    existing.refresh_from_db()
    assert existing.name["en"] == "Starters"
    assert [i.name["fr"] for i in existing.items.all()][0] == "Déjà là"
    assert existing.items.count() == 1 + 4
    assert existing.items.order_by("-position").first().position == 4


def test_merge_can_be_disabled(draft, staff_client, restaurant):
    Category.objects.create(restaurant=restaurant, name={"fr": "Entrées", "en": ""}, position=0)
    post = _fix_bad_price(_review_post(draft))
    del post["opt_merge"]
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post)
    assert Category.objects.filter(restaurant=restaurant).count() == 4


def test_save_with_translation_fills_english(draft, staff_client, restaurant):
    post = _fix_bad_price(_review_post(draft, opt_translate="on"))
    staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post)
    starters = Category.objects.get(restaurant=restaurant, name__fr="Entrées")
    assert starters.name["en"] == "Starters"
    item = Item.objects.get(name__fr="Crème brûlée à la vanille")
    assert item.name["en"] == "Vanilla crème brûlée"
    wine = Item.objects.get(name__fr="Cahors, Château Lamartine")
    assert wine.prices[0]["label"] == {"fr": "le verre", "en": "glass"}


def test_translation_failure_still_imports(draft, staff_client, restaurant, monkeypatch):
    from ai import services

    def boom(*a, **kw):
        raise services.AIUnavailable("The AI service is rate-limited right now.")

    monkeypatch.setattr(services, "translate_texts", boom)
    post = _fix_bad_price(_review_post(draft, opt_translate="on"))
    resp = staff_client.post(reverse("ai:import_review", args=[restaurant.pk, draft.pk]), post, follow=True)
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert msgs[0].startswith("Imported 12 items") and "without English" in msgs[1]
    assert Item.objects.count() == 12 and Item.objects.first().name["en"] == ""


def test_saving_twice_does_not_duplicate(draft, staff_client, restaurant):
    url = reverse("ai:import_review", args=[restaurant.pk, draft.pk])
    post = _fix_bad_price(_review_post(draft))
    staff_client.post(url, post)
    staff_client.post(url, post)
    assert Item.objects.count() == 12


def test_save_draft_action_keeps_status(draft, staff_client, restaurant):
    url = reverse("ai:import_review", args=[restaurant.pk, draft.pk])
    resp = staff_client.post(url, _review_post(draft, action="update", c1_name="Plats du jour"))
    assert resp.status_code == 302
    draft.refresh_from_db()
    assert draft.status == ImportDraft.STATUS_DRAFT and draft.data["categories"][1]["name"] == "Plats du jour"
    assert not Item.objects.exists()


def test_discard(draft, staff_client, restaurant):
    resp = staff_client.post(reverse("ai:import_discard", args=[restaurant.pk, draft.pk]))
    assert resp.status_code == 302
    draft.refresh_from_db()
    assert draft.status == ImportDraft.STATUS_DISCARDED
    assert staff_client.get(reverse("ai:import_review", args=[restaurant.pk, draft.pk])).status_code == 302
