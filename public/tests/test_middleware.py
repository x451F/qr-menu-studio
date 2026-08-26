import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from menus.tests.factories import make_menu, make_restaurant
from public.middleware import CSP

MIDDLEWARE_LINE = "public.middleware.SecurityHeadersMiddleware"


@pytest.fixture
def with_middleware(settings):
    mw = [m for m in settings.MIDDLEWARE if m != MIDDLEWARE_LINE]
    idx = mw.index("django.middleware.security.SecurityMiddleware") + 1
    mw.insert(idx, MIDDLEWARE_LINE)
    settings.MIDDLEWARE = mw
    return Client()


@pytest.mark.django_db
def test_public_menu_headers(with_middleware):
    r, _, _ = make_menu(make_restaurant())
    resp = with_middleware.get(reverse("public:menu", args=[r.slug]))
    assert resp["Content-Security-Policy"] == CSP
    assert "frame-ancestors 'self'" in resp["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline'" in resp["Content-Security-Policy"]
    assert "camera=()" in resp["Permissions-Policy"]
    assert "geolocation=()" in resp["Permissions-Policy"]
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert "X-Robots-Tag" not in resp


@pytest.mark.django_db
def test_404_under_m_also_gets_headers(with_middleware):
    resp = with_middleware.get("/m/unknown/")
    assert resp.status_code == 404
    assert "Content-Security-Policy" in resp


@pytest.mark.django_db
def test_admin_pages_are_noindex(with_middleware):
    resp = with_middleware.get("/admin/login/")
    assert resp["X-Robots-Tag"].startswith("noindex")
    assert "Content-Security-Policy" not in resp
    assert with_middleware.get("/dj/login/")["X-Robots-Tag"].startswith("noindex")


@pytest.mark.django_db
def test_preview_is_noindex(with_middleware):
    user = get_user_model().objects.create_user("boss", password="x" * 12, is_staff=True)
    with_middleware.force_login(user)
    r, _, _ = make_menu(make_restaurant())
    resp = with_middleware.get(reverse("public:menu", args=[r.slug]) + "?preview=1")
    assert resp["X-Robots-Tag"].startswith("noindex")


@pytest.mark.django_db
def test_other_paths_untouched(with_middleware):
    resp = with_middleware.get("/healthz")
    assert "Content-Security-Policy" not in resp
    assert "X-Robots-Tag" not in resp
