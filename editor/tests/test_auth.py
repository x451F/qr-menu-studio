import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from editor.auth import LOCK_AFTER

from .conftest import HX


def editor_url_names():
    from editor.urls import urlpatterns

    return [f"editor:{p.name}" for p in urlpatterns]


ARGS = {
    "editor:restaurant_edit": [1],
    "editor:restaurant_settings": [1],
    "editor:restaurant_publish": [1],
    "editor:restaurant_logo": [1],
    "editor:category_add": [1],
    "editor:category_update": [1],
    "editor:category_toggle": [1],
    "editor:category_delete": [1],
    "editor:item_add": [1],
    "editor:item_update": [1],
    "editor:item_toggle": [1, "is_sold_out"],
    "editor:item_duplicate": [1],
    "editor:item_delete": [1],
    "editor:item_photo": [1],
    "editor:item_undo": [1],
    "editor:special_add": [1, "plat"],
    "editor:special_update": [1],
    "editor:special_toggle": [1],
    "editor:special_delete": [1],
    "editor:reorder_categories": [1],
    "editor:reorder_items": [1],
    "editor:reorder_specials": [1],
}
PUBLIC = {"editor:login"}


@pytest.mark.django_db
def test_every_editor_endpoint_requires_login():
    anon = Client()
    names = [n for n in editor_url_names() if n not in PUBLIC]
    assert len(names) > 20
    for full in names:
        url = reverse(full, args=ARGS.get(full, []))
        for method in ("get", "post"):
            resp = getattr(anon, method)(url)
            assert resp.status_code == 302, (full, method, resp.status_code)
            assert reverse("editor:login") in resp["Location"], full


@pytest.mark.django_db
def test_htmx_request_gets_401_with_redirect_header():
    resp = Client().post(reverse("editor:item_update", args=[1]), **HX)
    assert resp.status_code == 401
    assert resp["HX-Redirect"] == reverse("editor:login")


@pytest.mark.django_db
def test_non_staff_user_is_forbidden():
    user = get_user_model().objects.create_user("waiter", password="x" * 12)
    c = Client()
    c.force_login(user)
    assert c.get(reverse("editor:dashboard")).status_code == 403


@pytest.mark.django_db
def test_login_and_logout(staff):
    c = Client()
    resp = c.post(reverse("editor:login"), {"username": "boss", "password": "s3cret-pass-123"})
    assert resp.status_code == 302
    assert resp["Location"] == reverse("editor:dashboard")
    assert c.get(reverse("editor:dashboard")).status_code == 200
    # logout is POST-only
    assert c.get(reverse("editor:logout")).status_code == 405
    assert c.post(reverse("editor:logout")).status_code == 302
    assert c.get(reverse("editor:dashboard")).status_code == 302


@pytest.mark.django_db
def test_login_throttle_locks_after_ten_failures(staff):
    c = Client()
    url = reverse("editor:login")
    for _ in range(LOCK_AFTER):
        resp = c.post(url, {"username": "boss", "password": "wrong"})
        assert resp.status_code == 200
    # even the correct password is refused while locked
    resp = c.post(url, {"username": "boss", "password": "s3cret-pass-123"})
    assert resp.status_code == 429
    assert b"Too many failed attempts" in resp.content
    assert c.get(reverse("editor:dashboard")).status_code == 302


@pytest.mark.django_db
def test_throttle_is_per_ip_and_success_resets(staff):
    url = reverse("editor:login")
    c = Client()
    for _ in range(3):
        c.post(url, {"username": "boss", "password": "wrong"}, REMOTE_ADDR="10.0.0.1")
    ok = c.post(url, {"username": "boss", "password": "s3cret-pass-123"}, REMOTE_ADDR="10.0.0.1")
    assert ok.status_code == 302
    other = Client()
    for _ in range(LOCK_AFTER):
        other.post(url, {"username": "boss", "password": "wrong"}, REMOTE_ADDR="10.0.0.2")
    # a different IP is unaffected
    fresh = Client().post(url, {"username": "boss", "password": "s3cret-pass-123"}, REMOTE_ADDR="10.0.0.3")
    assert fresh.status_code == 302
