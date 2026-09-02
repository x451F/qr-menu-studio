"""The definition of done: create -> import photo -> edit -> publish -> scan URL -> print PDF."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
import zxingcpp
from PIL import Image
from playwright.sync_api import expect

from .conftest import ADMIN_PASS, ADMIN_USER, BASE, SAMPLE_MENU, login  # noqa: F401

NAME = "Le Café des Tests"

def decode_qr(png: bytes) -> str | None:
    """Decode a QR PNG (zxing-cpp, a dev dependency); None if no code is found."""
    results = zxingcpp.read_barcodes(Image.open(io.BytesIO(png)))
    return results[0].text if results else None


def drag(page, source, target):
    """Mouse drag with intermediate moves (SortableJS needs real pointer motion)."""
    source.scroll_into_view_if_needed()
    sb = source.bounding_box()
    page.mouse.move(sb["x"] + sb["width"] / 2, sb["y"] + sb["height"] / 2)
    page.mouse.down()
    page.mouse.move(sb["x"] + 5, sb["y"] + 15, steps=3)
    target.scroll_into_view_if_needed()
    tb = target.bounding_box()
    page.mouse.move(tb["x"] + tb["width"] / 2, tb["y"] + tb["height"] * 0.8, steps=15)
    page.mouse.move(tb["x"] + tb["width"] / 2, tb["y"] + tb["height"] * 0.9, steps=5)
    page.mouse.up()


def open_item(page, name):
    row = page.locator("article.item", has=page.locator(".item__main", has_text=name)).first
    if not row.locator(".item__body").is_visible():
        row.locator("[data-toggle-open]").click()
    return row


@pytest.mark.parametrize("width", [375, 1280], ids=["mobile", "desktop"])
def test_main_flow(make_context, tmp_path, width):
    ctx = make_context(width)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    # 1. login
    login(page)
    expect(page.locator("h1")).to_be_visible()

    # 2. create restaurant
    page.goto("/admin/r/new/")
    page.fill("input[name=name]", NAME)
    page.click("text=Create and add dishes")
    page.wait_for_url(re.compile(r"/admin/r/\d+/$"))
    pk = int(page.url.rstrip("/").rsplit("/", 1)[1])
    expect(page.locator("h1.h1")).to_have_text(NAME)

    # 3. import a photo (fake AI)
    page.get_by_role("link", name="Import photo").first.click()
    page.wait_for_url(f"**/admin/r/{pk}/import/")
    page.set_input_files("#ai-files", str(SAMPLE_MENU))
    expect(page.locator("#ai-thumbs li")).to_have_count(1)
    page.click("#ai-submit")
    expect(page.get_by_role("heading", name="Check your menu")).to_be_visible(timeout=60000)
    expect(page.locator("#ai-price-alert")).to_contain_text("1 price")
    bad = page.locator(".ai-price.is-bad input[aria-invalid=true]")
    expect(bad).to_have_count(1)
    bad.fill("19,50")
    # untick one item
    unwanted = page.locator("article.ai-item", has=page.locator("input[value='Foie gras de canard mi-cuit']"))
    unwanted.locator(".ai-item__on").uncheck()
    page.click("#ai-import-btn")
    page.wait_for_url(re.compile(rf"/admin/r/{pk}/$"))
    expect(page.locator(".flash__item--success")).to_be_visible()
    expect(page.locator("#categories .item__main", has_text="Confit de canard")).to_be_visible()
    expect(page.locator("#categories .item__main", has_text="Andouillette")).to_contain_text("19,50")
    expect(page.locator("#categories .item__main", has_text="Foie gras")).to_have_count(0)
    expect(page.locator("#categories .item__main", has_text="Soupe à l'oignon")).to_be_visible()

    # 4a. add an item with price "12,5"
    desserts = page.locator("section.cat", has=page.locator("input[name=name_fr][value='Desserts et boissons']"))
    qa = desserts.locator("form[data-quick-add]")
    qa.locator("input[name=name_fr]").fill("Café gourmand")
    qa.locator("input[name=price_amount]").fill("12,5")
    qa.locator("button[type=submit]").click()
    new_item = page.locator("#categories .item__main", has_text="Café gourmand")
    expect(new_item).to_contain_text("12,50")  # editor summary
    expect(new_item).to_contain_text("€")

    # 4b. sold out
    row = page.locator("article.item", has=page.locator(".item__main", has_text="Risotto aux cèpes"))
    row.locator(".tgl--soldout").click()
    expect(row).to_have_class(re.compile("is-soldout"))

    # 4c. plat du jour with two prices
    n_before = page.locator("#specials .special").count()
    page.click("#today .add-row button:has-text('Plat du jour')")
    expect(page.locator("#specials .special")).to_have_count(n_before + 1)
    sp = page.locator("#specials .special").last
    sp.locator("input[name=title_fr]").fill("Tartare du chef")
    sp.locator("[data-price-add]").click()
    expect(sp.locator(".price-row")).to_have_count(2)
    r1 = sp.locator(".price-row").first
    r1.locator("input[name=price_label_fr]").fill("midi")
    r1.locator("input[name=price_amount]").fill("13,5")
    r2 = sp.locator(".price-row").nth(1)
    r2.locator("input[name=price_label_fr]").fill("soir")
    r2.locator("input[name=price_amount]").fill("16")
    r2.locator("input[name=price_amount]").blur()
    expect(page.locator("#save-status")).to_have_attribute("data-state", "saved")

    # 4d. reorder: move select (item to another category)
    it = open_item(page, "Crème brûlée")
    sel = it.locator("select[data-move]")
    sel.focus()
    sel.select_option(label="Plats")
    expect(page.locator("#items-" + str(
        page.locator("section.cat", has=page.locator("input[name=name_fr][value='Plats']")).get_attribute("data-id")
    ) + " .item__main", has_text="Crème brûlée")).to_be_visible()

    # 4e. drag and drop categories
    cats = page.locator("#categories > section.cat")
    first_name = cats.first.locator(".cat__head input[name=name_fr]").input_value()
    drag(page, cats.first.locator(".cat-handle"), cats.last.locator(".cat__head"))
    expect(cats.last.locator(".cat__head input[name=name_fr]")).to_have_value(first_name)
    expect(page.locator("#save-status")).to_have_attribute("data-state", "saved")
    page.reload()
    expect(page.locator("#categories > section.cat").last.locator(".cat__head input[name=name_fr]")).to_have_value(first_name)

    # 4f. theme switch in the preview toolbar
    if width < 1024:
        page.click("[data-preview-open]")
    frame = page.locator("iframe[data-frame]")
    expect(frame).to_have_attribute("src", re.compile("preview=1"))
    page.click("#preview [data-theme=cafe]")
    expect(frame).to_have_attribute("src", re.compile("theme=cafe"))
    page.click("#preview [data-theme=gastro]")
    expect(frame).to_have_attribute("src", re.compile("theme=gastro"))
    page.click("#preview [data-theme=cafe]")
    expect(frame).to_have_attribute("src", re.compile("theme=cafe"))
    if width < 1024:
        page.click("[data-preview-close]")

    # 4g. translate missing (fake)
    page.click("#translate-missing")
    expect(page.locator("#translate-missing")).to_be_enabled()
    page.wait_for_load_state("load")

    # 4h. settings: brand colour and logo
    page.goto(f"/admin/r/{pk}/settings/")
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (200, 200), (30, 90, 160, 255)).save(logo)
    page.set_input_files("input[name=logo]", str(logo))
    expect(page.locator("#logo-box img")).to_be_visible()
    hexin = page.locator("input[name=brand_color]")
    hexin.fill("#2f5d50")
    hexin.dispatch_event("change")
    expect(page.locator("#save-status")).to_have_attribute("data-state", "saved")
    page.reload()
    expect(page.locator("input[name=brand_color]")).to_have_value("#2f5d50")
    expect(page.locator("#logo-box img")).to_be_visible()

    # 5. publish
    page.goto(f"/admin/r/{pk}/")
    expect(page.locator(".pubchip")).to_contain_text("Draft")
    page.click(".pubchip")
    expect(page.locator(".pubchip")).to_contain_text("Published")

    # 6. the URL the QR encodes
    page.goto(f"/admin/r/{pk}/print/")
    public_url = page.locator("#pr-url").input_value()
    assert re.fullmatch(rf"{re.escape(BASE)}/m/[a-z0-9-]+/", public_url), public_url
    png = ctx.request.get(f"/admin/r/{pk}/qr.png?color=black&size=1024")
    assert png.ok and png.body()[:4] == b"\x89PNG"
    assert decode_qr(png.body()) == public_url

    # 7. print PDFs (before logging out; admin session)
    for path, tag in [
        (f"/admin/r/{pk}/print/stickers.pdf?size=70&shape=square&color=brand", "stickers"),
        (f"/admin/r/{pk}/print/tent.pdf?format=a5&color=brand", "tent-a5"),
        (f"/admin/r/{pk}/print/tent.pdf?format=a6&color=black&line=Bon+app%C3%A9tit", "tent-a6"),
    ]:
        r = ctx.request.get(path)
        assert r.status == 200, tag
        assert "pdf" in r.headers["content-type"], tag
        body = r.body()
        assert body[:4] == b"%PDF" and len(body) > 5000, (tag, len(body))
    # PDFs also downloadable from the UI form
    with page.expect_download() as dl:
        page.locator("form[data-pr-pdf-form]").first.locator("button[type=submit]").click()
    assert Path(dl.value.path()).read_bytes()[:4] == b"%PDF"

    # log out, then act as an anonymous diner
    anon = make_context(375)
    diner = anon.new_page()
    diner.goto(public_url)
    expect(diner.locator("h1.name")).to_have_text(NAME)
    dishes = diner.locator("li.dish")
    expect(dishes.filter(has_text="Confit de canard")).to_be_visible()
    expect(dishes.filter(has_text="Foie gras")).to_have_count(0)
    expect(dishes.filter(has_text="Café gourmand")).to_contain_text("12,50")
    expect(dishes.filter(has_text="Andouillette")).to_contain_text("19,50")
    expect(dishes.filter(has_text="Risotto")).to_contain_text(re.compile("Épuisé|Sold out|Complet", re.I))
    today = diner.locator("section.today")
    expect(today).to_contain_text("Tartare du chef")
    expect(today).to_contain_text("13,50")
    expect(today).to_contain_text("16,00")
    assert diner.evaluate("document.documentElement.scrollWidth <= innerWidth")
    expect(diner.locator("html")).to_have_attribute("lang", "fr")
    diner.locator(".lang a[hreflang=en]").click()
    expect(diner.locator("html")).to_have_attribute("lang", "en")
    diner.reload()
    expect(diner.locator("html")).to_have_attribute("lang", "en")
    expect(diner.locator("li.dish").filter(has_text="Risotto")).to_contain_text(re.compile("Sold out", re.I))
    # a really logged-out admin context cannot use print URLs
    assert anon.request.get(f"/admin/r/{pk}/qr.png", max_redirects=0).status in (301, 302)
