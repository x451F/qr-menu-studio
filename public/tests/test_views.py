import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from menus import images
from menus.models import Item
from menus.tests.factories import image_file, make_menu, make_restaurant


@pytest.fixture
def restaurant(db):
    r, _cat, _items = make_menu(make_restaurant("Chez Test"))
    return r


@pytest.fixture
def url(restaurant):
    return reverse("public:menu", args=[restaurant.slug])


@pytest.fixture
def staff_client(db):
    user = get_user_model().objects.create_user("boss", password="x" * 12, is_staff=True, is_superuser=True)
    c = Client()
    c.force_login(user)
    return c


# -- language selection ---------------------------------------------------------------------
def test_default_language_is_french(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert 'lang="fr"' in r.content.decode()
    assert "menu_lang" not in r.cookies


def test_lang_param_wins_and_sets_cookie(client, url):
    r = client.get(url + "?lang=en", headers={"Accept-Language": "fr"})
    assert 'lang="en"' in r.content.decode()
    cookie = r.cookies["menu_lang"]
    assert cookie.value == "en"
    assert cookie["max-age"] == 60 * 60 * 24 * 365
    assert cookie["samesite"] == "Lax"


def test_cookie_used_when_no_param_and_not_reset(client, url):
    client.cookies["menu_lang"] = "en"
    r = client.get(url)
    assert 'lang="en"' in r.content.decode()
    assert "menu_lang" not in r.cookies  # cookie only set on ?lang=


def test_lang_param_beats_cookie(client, url):
    client.cookies["menu_lang"] = "en"
    r = client.get(url + "?lang=fr")
    assert 'lang="fr"' in r.content.decode()
    assert r.cookies["menu_lang"].value == "fr"


def test_accept_language_english(client, url):
    r = client.get(url, headers={"Accept-Language": "en-GB,en;q=0.9,fr;q=0.8"})
    assert 'lang="en"' in r.content.decode()
    assert "menu_lang" not in r.cookies


def test_accept_language_french_first_stays_french(client, url):
    r = client.get(url, headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"})
    assert 'lang="fr"' in r.content.decode()


def test_cookie_beats_accept_language(client, url):
    client.cookies["menu_lang"] = "fr"
    r = client.get(url, headers={"Accept-Language": "en"})
    assert 'lang="fr"' in r.content.decode()


def test_invalid_lang_ignored(client, url):
    r = client.get(url + "?lang=de")
    assert 'lang="fr"' in r.content.decode()
    assert "menu_lang" not in r.cookies


def test_english_disabled_restaurant_ignores_english(client, restaurant, url):
    restaurant.languages = ["fr"]
    restaurant.save()
    r = client.get(url + "?lang=en", headers={"Accept-Language": "en"})
    assert 'lang="fr"' in r.content.decode()
    assert "menu_lang" not in r.cookies


def test_vary_header(client, url):
    vary = client.get(url)["Vary"]
    assert "Accept-Language" in vary and "Cookie" in vary


# -- 404s ---------------------------------------------------------------------------------------
def test_unknown_slug_404(client, db):
    assert client.get("/m/does-not-exist/").status_code == 404


def test_unpublished_404_for_anonymous(client, db):
    r = make_restaurant("Secret", published=False)
    assert client.get(reverse("public:menu", args=[r.slug])).status_code == 404


def test_unpublished_visible_to_admin_without_caching(staff_client, client, db):
    r = make_restaurant("Secret", published=False)
    make_menu(r)
    url = reverse("public:menu", args=[r.slug])
    resp = staff_client.get(url)
    assert resp.status_code == 200
    assert "ETag" not in resp
    assert client.get(url).status_code == 404  # never leaks through the cache


# -- cookies ----------------------------------------------------------------------------------
def test_no_session_or_csrf_cookie_for_anonymous(client, url):
    for target in (url, url + "?lang=en"):
        r = client.get(target)
        assert "sessionid" not in r.cookies
        assert "csrftoken" not in r.cookies
        assert set(r.cookies) <= {"menu_lang"}
    r = client.get(url, headers={"If-None-Match": client.get(url)["ETag"]})
    assert r.status_code == 304
    assert not r.cookies


def test_no_cookies_on_404(client, db):
    assert not client.get("/m/nope/").cookies


# -- preview ------------------------------------------------------------------------------------
def test_preview_ignored_for_anonymous(client, url):
    r = client.get(url + "?preview=1&theme=gastro")
    assert r.status_code == 200
    assert r["Cache-Control"] == "no-cache"
    assert "ETag" in r


def test_preview_admin_no_store_and_overrides(staff_client, url, monkeypatch):
    seen = {}
    import public.views as views

    real = views.build_menu_context

    def spy(restaurant, lang, **kwargs):
        seen.update(kwargs)
        return real(restaurant, lang, **kwargs)

    monkeypatch.setattr(views, "build_menu_context", spy)
    r = staff_client.get(url + "?preview=1&theme=gastro&mode=dark&photos=0&lang=en")
    assert r.status_code == 200
    assert r["Cache-Control"] == "no-store"
    assert "ETag" not in r
    assert "menu_lang" not in r.cookies
    assert seen == {"theme": "gastro", "mode": "dark", "preview": True, "hide_photos": True}


def test_preview_photos_zero_hides_photos(staff_client, restaurant, url):
    item = Item.objects.filter(category__restaurant=restaurant).first()
    item.photo.save("p.jpg", images.process_photo(image_file(size=(900, 600))), save=True)
    import public.views as views

    captured = {}
    real = views.build_menu_context

    def spy(*a, **kw):
        ctx = real(*a, **kw)
        captured["has_photos"] = ctx["menu"].has_photos
        return ctx

    views.build_menu_context = spy
    try:
        staff_client.get(url + "?preview=1&photos=0")
        assert captured["has_photos"] is False
        staff_client.get(url + "?preview=1")
        assert captured["has_photos"] is True
    finally:
        views.build_menu_context = real


def test_non_preview_staff_request_not_cached_and_not_poisoning(staff_client, client, url):
    staff_client.get(url)
    r = client.get(url)
    assert r.status_code == 200


# -- caching / ETag -------------------------------------------------------------------------------
def test_cache_control_no_cache_and_strong_etag(client, url):
    r = client.get(url)
    assert r["Cache-Control"] == "no-cache"
    etag = r["ETag"]
    assert etag.startswith('"') and not etag.startswith("W/")


def test_if_none_match_returns_304(client, url):
    etag = client.get(url)["ETag"]
    r = client.get(url, headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.content == b""
    assert r["ETag"] == etag
    assert r["Cache-Control"] == "no-cache"


def test_weak_and_list_if_none_match(client, url):
    etag = client.get(url)["ETag"]
    assert client.get(url, headers={"If-None-Match": f'"other", W/{etag}'}).status_code == 304
    assert client.get(url, headers={"If-None-Match": '"other"'}).status_code == 200


def test_etag_differs_per_language(client, url):
    assert client.get(url + "?lang=fr")["ETag"] != client.get(url + "?lang=en")["ETag"]


def test_edit_changes_etag_and_content(client, restaurant, url):
    first = client.get(url)
    etag = first["ETag"]
    item = Item.objects.filter(category__restaurant=restaurant).first()
    item.is_sold_out = True
    item.save()
    r = client.get(url, headers={"If-None-Match": etag})
    assert r.status_code == 200
    assert r["ETag"] != etag


def test_html_served_from_cache_on_second_request(client, url, monkeypatch):
    client.get(url)
    import public.views as views

    def boom(*a, **kw):
        raise AssertionError("should not rebuild the context on a cache hit")

    monkeypatch.setattr(views, "build_menu_context", boom)
    assert client.get(url).status_code == 200


def test_saving_restaurant_changes_etag(client, restaurant, url):
    etag = client.get(url)["ETag"]
    restaurant.tagline = {"fr": "Nouvelle accroche", "en": ""}
    restaurant.save()
    assert client.get(url, headers={"If-None-Match": etag}).status_code == 200


def test_query_count(client, url):
    with CaptureQueriesContext(connection) as cold:
        assert client.get(url).status_code == 200
    assert len(cold) <= 4
    with CaptureQueriesContext(connection) as warm:
        assert client.get(url).status_code == 200
    assert len(warm) <= 1
    etag = client.get(url)["ETag"]
    with CaptureQueriesContext(connection) as revalidate:
        assert client.get(url, headers={"If-None-Match": etag}).status_code == 304
    assert len(revalidate) <= 1


def test_healthz(client, db):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.content == b"ok"
