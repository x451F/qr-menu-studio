"""Visibility, cookies, permanent slug, AI-disabled behaviour."""

from __future__ import annotations

import subprocess
import sys
import tempfile

from playwright.sync_api import expect

from .conftest import BASE, ROOT
from .test_main_flow import decode_qr


def add_dish(page, cat_name="Plats", dish="Steak frites", price="15"):
    if page.locator("#empty-state").count():
        page.locator("#empty-state .chip", has_text=cat_name).first.click()
    else:
        page.fill("[data-cat-add] input[name=name_fr]", cat_name)
        page.click("[data-cat-add] button[type=submit]")
    qa = page.locator("form[data-quick-add]").first
    qa.locator("input[name=name_fr]").fill(dish)
    qa.locator("input[name=price_amount]").fill(price)
    qa.locator("button[type=submit]").click()
    expect(page.locator(".item__main", has_text=dish)).to_be_visible()


def publish(page):
    page.on("dialog", lambda d: d.accept())
    page.click(".pubchip")
    expect(page.locator(".pubchip")).to_contain_text("Published")


def public_path(page, pk):
    page.goto(f"/admin/r/{pk}/settings/")
    return page.locator(".urlbox__url").get_attribute("href")


def test_unpublished_hidden_from_anonymous_visible_to_admin(make_restaurant, make_context, admin_ctx):
    pk, page = make_restaurant("Brouillon Test")
    add_dish(page)
    path = public_path(page, pk)
    anon = make_context(375)
    assert anon.request.get(path).status == 404
    assert anon.request.get(path + "?preview=1").status == 404
    r = admin_ctx.request.get(path + "?preview=1")
    assert r.status == 200 and "Steak frites" in r.text()
    assert admin_ctx.request.get(path).status == 200
    # published -> anonymous sees it; unpublished again -> 404 again
    page.goto(f"/admin/r/{pk}/")
    publish(page)
    assert anon.request.get(path).status == 200
    page.click(".pubchip")
    expect(page.locator(".pubchip")).to_contain_text("Draft")
    assert anon.request.get(path).status == 404


def test_unknown_slug_404(make_context):
    assert make_context(375).request.get("/m/does-not-exist/").status == 404


def test_public_page_cookies(make_restaurant, make_context):
    pk, page = make_restaurant("Cookie Test")
    add_dish(page)
    path = public_path(page, pk)
    page.goto(f"/admin/r/{pk}/")
    publish(page)

    anon = make_context(375)
    r = anon.request.get(path)
    assert r.status == 200
    assert "set-cookie" not in r.headers, r.headers.get("set-cookie")
    diner = anon.new_page()
    diner.goto(path)
    assert anon.cookies() == []
    diner.locator(".lang a[hreflang=en]").click()
    expect(diner.locator("html")).to_have_attribute("lang", "en")
    names = [c["name"] for c in anon.cookies()]
    assert names == ["menu_lang"], names
    diner.goto(path)
    expect(diner.locator("html")).to_have_attribute("lang", "en")
    # ?lang=fr overrides and updates the remembered choice
    diner.goto(path + "?lang=fr")
    expect(diner.locator("html")).to_have_attribute("lang", "fr")
    diner.goto(path)
    expect(diner.locator("html")).to_have_attribute("lang", "fr")


def test_slug_permanent_after_publish(make_restaurant):
    pk, page = make_restaurant("Slug Test")
    add_dish(page)
    page.goto(f"/admin/r/{pk}/settings/")
    slug_input = page.locator("input[name=slug]")
    # before publishing it can be changed
    slug_input.fill("slug-test-custom")
    slug_input.dispatch_event("change")
    expect(page.locator("#save-status")).to_have_attribute("data-state", "saved")
    page.reload()
    expect(page.locator("input[name=slug]")).to_have_value("slug-test-custom")
    page.goto(f"/admin/r/{pk}/")
    publish(page)
    page.goto(f"/admin/r/{pk}/settings/")
    expect(page.locator("input[name=slug]")).to_have_attribute("readonly", "")
    # forge a change from the browser: the server must refuse it
    status = page.evaluate(
        """async (pk) => {
          const t = document.querySelector('input[name=csrfmiddlewaretoken]');
          const token = (t && t.value) || document.body.getAttribute('hx-headers').match(/"X-CSRFToken": "([^"]+)"/)[1];
          const r = await fetch(`/admin/r/${pk}/settings/`, {method: 'POST',
            headers: {'X-CSRFToken': token, 'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'slug=hacked-slug'});
          return r.status;
        }""",
        pk,
    )
    assert status == 200
    page.reload()
    expect(page.locator("input[name=slug]")).to_have_value("slug-test-custom")
    assert page.request.get("/m/hacked-slug/").status == 404
    assert page.request.get("/m/slug-test-custom/").status == 200


def test_qr_png_decodes_to_public_url(make_restaurant, admin_ctx):
    pk, page = make_restaurant("QR Decode Test")
    add_dish(page)
    url = public_path(page, pk)
    png = admin_ctx.request.get(f"/admin/r/{pk}/qr.png?color=brand&size=512").body()
    assert decode_qr(png) == BASE + url


def test_ai_disabled_service_level():
    """A second server without AI_FAKE is expensive: check the service layer in a subprocess."""
    code = (
        "import django;django.setup();"
        "from django.conf import settings;from ai import services;"
        "assert not settings.AI_ENABLED, 'AI_ENABLED should be false';"
        "ok=[];"
        "\ntry:\n services.extract_menu([b'x'],['image/jpeg'])\nexcept services.AIUnavailable:\n ok.append(1)\n"
        "try:\n services.translate_texts({'a':'bonjour'},'fr','en')\nexcept services.AIUnavailable:\n ok.append(2)\n"
        "assert ok==[1,2], ok;print('ok')"
    )
    import os

    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "AI_FAKE")}
    env.update(DJANGO_DEBUG="1", DATA_DIR=tempfile.mkdtemp(), DJANGO_SETTINGS_MODULE="config.settings")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr[-800:]
