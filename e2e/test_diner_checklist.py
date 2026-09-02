"""Diner-UX checklist (docs/qa/CHECKLIST.md) against an already running stack (Docker/Caddy).

    DINER_BASE=http://localhost:8080 DINER_ADMIN_PASSWORD=... uv run pytest e2e/test_diner_checklist.py

Skipped when DINER_BASE is not set. The stack must contain the 5 seeded demo restaurants.
DINER_ADMIN_PASSWORD (and optionally DINER_ADMIN_USER, default admin) enables the admin-preview check.
Measurements are appended to $DINER_NOTES (default /tmp/qa_notes.jsonl); screenshots go to docs/qa/screens.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

DBASE = os.environ.get("DINER_BASE", "").rstrip("/")
pytestmark = pytest.mark.skipif(not DBASE, reason="DINER_BASE not set (needs the Docker stack)")

SLUGS = ["bistrot-des-halles", "chez-gino", "petit-kiosque", "maison-vialle", "auberge-du-puy-blanc"]
THEMES = {
    "bistrot-des-halles": "bistro", "chez-gino": "trattoria", "petit-kiosque": "cafe",
    "maison-vialle": "gastro", "auberge-du-puy-blanc": "auberge",
}
SCREENS = Path(__file__).resolve().parent.parent / "docs" / "qa" / "screens"
NOTES = Path(os.environ.get("DINER_NOTES", "/tmp/qa_notes.jsonl"))


def note(key, **data):
    with NOTES.open("a") as f:
        f.write(json.dumps({"key": key, **data}, ensure_ascii=False) + "\n")


@pytest.fixture
def diner(browser):
    made = []

    def factory(width=375, height=812, **kw):
        ctx = browser.new_context(viewport={"width": width, "height": height}, base_url=DBASE, **kw)
        ctx.set_default_timeout(15000)
        made.append(ctx)
        return ctx

    yield factory
    for c in made:
        c.close()


def open_menu(ctx, slug, qs=""):
    page = ctx.new_page()
    page.goto(f"/m/{slug}/{qs}")
    page.wait_for_load_state("load")
    return page


# 1 -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_01_page_weight(diner, slug):
    ctx = diner()
    page = ctx.new_page()
    sizes = []

    def on_resp(resp):
        try:
            s = resp.request.sizes()
            sizes.append((resp.url, resp.request.resource_type, s["responseBodySize"] + s["responseHeadersSize"]))
        except Exception:
            pass

    page.on("response", on_resp)
    page.goto(f"/m/{slug}/", wait_until="networkidle")
    total = sum(s for _, _, s in sizes)
    html = sum(s for u, t, s in sizes if t == "document")
    js = sum(s for u, t, s in sizes if t == "script")
    fonts = sum(s for u, t, s in sizes if t == "font")
    imgs = sum(s for u, t, s in sizes if t == "image")
    note("01", slug=slug, total_kb=round(total / 1024), html_kb=round(html / 1024, 1),
         js_kb=round(js / 1024, 1), fonts_kb=round(fonts / 1024), img_kb=round(imgs / 1024))
    assert html < 20 * 1024, "HTML+inline CSS over 20 KB gzip"
    assert js < 6 * 1024, "JS over 6 KB"


# 2 -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_02_no_popups_no_cookies(diner, slug):
    ctx = diner()
    page = ctx.new_page()
    dialogs = []
    page.on("dialog", lambda d: dialogs.append(d.message))
    popups = []
    ctx.on("page", lambda p: popups.append(p.url))
    page.goto(f"/m/{slug}/", wait_until="networkidle")
    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(300)  # let any timer-driven popup show up (negative check)
    assert dialogs == [] and popups == [page.url] or popups == []
    assert page.locator("dialog[open]").count() == 0
    body = page.inner_text("body").lower()
    assert not re.search(r"cookie|consent|newsletter|subscribe|accept all", body)
    assert ctx.cookies() == []


# 3 -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_03_sticky_bar_scroll_spy(diner, slug):
    ctx = diner()
    page = open_menu(ctx, slug)
    bar = page.locator(".bar")
    if not bar.count():
        note("03", slug=slug, bar=False, categories=page.locator(".cat").count())
        pytest.skip("single-category menu without specials renders no chip bar (by design)")
    expect(bar).to_be_visible()
    assert page.evaluate("getComputedStyle(document.querySelector('.bar')).position") == "sticky"
    secs = page.locator(".today, .cat")
    ids = [secs.nth(i).get_attribute("id") for i in range(secs.count())]
    seen = []
    for sid in ids:
        page.evaluate("id => { const s = document.getElementById(id); scrollTo({top: s.getBoundingClientRect().top + scrollY - 20, behavior: 'instant'}) }", sid)
        cur = page.locator(".bar a[aria-current=true]")
        expect(cur).to_have_attribute("href", f"#{sid}") if page.locator(f".bar a[href='#{sid}']").count() else None
        page.wait_for_function("() => document.querySelector('.bar').getBoundingClientRect().top <= 1")
        top = bar.bounding_box()["y"]
        assert top <= 1, f"bar not stuck at top: y={top} at #{sid}"
        seen.append(sid)
    note("03", slug=slug, sections=seen)
    # tapping a chip scrolls to its section
    chips = page.locator(".bar a")
    if chips.count() > 1:
        page.evaluate("scrollTo({top:0,behavior:'instant'})")
        last = chips.last
        target = last.get_attribute("href")
        last.click()
        expect(last).to_have_attribute("aria-current", "true")
        assert page.evaluate("t => document.querySelector(t).getBoundingClientRect().top < 200", target)


# 4 -------------------------------------------------------------------------------------------
def test_04_language_remembered(diner):
    ctx = diner()
    slug = "petit-kiosque"
    page = open_menu(ctx, slug)
    expect(page.locator("html")).to_have_attribute("lang", "fr")
    page.locator(".lang a[hreflang=en]").click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.close()
    p2 = open_menu(ctx, slug)  # new visit, same browser profile
    expect(p2.locator("html")).to_have_attribute("lang", "en")
    p3 = open_menu(ctx, "chez-gino")  # remembered across menus too
    lang3 = p3.locator("html").get_attribute("lang")
    c = [c for c in ctx.cookies() if c["name"] == "menu_lang"][0]
    note("04", cookie=c["name"], expires_days=round((c["expires"] - __import__("time").time()) / 86400),
         samesite=c["sameSite"], httpOnly=c["httpOnly"], other_menu_lang=lang3)
    assert c["expires"] > __import__("time").time() + 300 * 86400
    # Accept-Language en visitor gets English without cookie
    ctx2 = diner(locale="en-GB")
    p4 = open_menu(ctx2, slug)
    expect(p4.locator("html")).to_have_attribute("lang", "en")


# 5 -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_05_specials_on_top(diner, slug):
    page = open_menu(diner(), slug)
    today = page.locator("section.today")
    if not today.count():
        note("05", slug=slug, specials=False)
        pytest.skip("no active specials on this menu")
    layout = page.evaluate(
        """() => { const y = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + scrollY) : null };
        return {header: y('.head'), bar: y('.bar'), today: y('.today'), firstcat: y('.cat'), h: innerHeight,
                order: [...document.querySelectorAll('.head,.bar,.today,.cat')].map(e=>e.className.split(' ')[0]).filter((v,i,a)=>a.indexOf(v)===i)} }"""
    )
    note("05", slug=slug, specials=True, **layout, title=page.locator(".today h2").inner_text())
    assert layout["today"] < layout["firstcat"]
    assert layout["today"] < layout["h"], "specials not visible in the first screen"


# 6 -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_06_sheet_and_back_button(diner, slug):
    page = open_menu(diner(), slug)
    path = page.url
    start_len = page.evaluate("history.length")
    link = page.locator(".dish-link").first
    link.scroll_into_view_if_needed()
    link.click()
    expect(page.locator("dialog#sheet")).to_have_attribute("open", "")
    expect(page.locator("#s-name")).not_to_be_empty()
    assert page.url.startswith(path) and re.search(r"#(dish|sp)-\d+$", page.url)
    page.go_back()
    expect(page.locator("dialog#sheet")).not_to_have_attribute("open", "")
    assert page.url.split("#")[0] == path, "back navigated away"
    assert page.locator("h1.name").is_visible()
    # forward re-opens, Escape closes without leaving
    page.go_forward()
    expect(page.locator("dialog#sheet")).to_have_attribute("open", "")
    page.keyboard.press("Escape")
    expect(page.locator("dialog#sheet")).not_to_have_attribute("open", "")
    assert page.url.split("#")[0] == path
    # deep link opens the sheet cold, close stays on page
    href = link.get_attribute("href")
    p2 = open_menu(page.context, slug, href)
    expect(p2.locator("dialog#sheet")).to_have_attribute("open", "")
    p2.locator("#sheet [data-close]").click()
    expect(p2.locator("dialog#sheet")).not_to_have_attribute("open", "")
    assert p2.locator("h1.name").is_visible()
    note("06", slug=slug, history_len_before=start_len)


# 7 -------------------------------------------------------------------------------------------
def test_07_filters_and_legend(diner):
    page = open_menu(diner(), "chez-gino")
    assert page.locator("#legend").count() == 1
    assert page.locator("#legend li").count() >= 3
    total = page.locator(".dish").count()
    expect(page.locator("#fbtn")).to_be_visible()
    page.click("#fbtn")
    expect(page.locator("#filters")).to_have_attribute("open", "")
    code = page.locator("#filters input[name=al]").first.get_attribute("value")
    with_code = page.locator(f".dish[data-al~='{code}']").count()
    assert with_code > 0
    page.locator("#filters input[name=al]").first.check()
    page.locator("#fshow").click()
    hidden = page.locator(".dish[hidden]")
    expect(hidden).to_have_count(with_code)
    assert page.locator(f".dish[data-al~='{code}']:not([hidden])").count() == 0
    expect(page.locator("#fstat")).to_be_visible()
    page.locator("#freset").click()
    expect(page.locator(".dish[hidden]")).to_have_count(0)
    # diet filter
    page.click("#fbtn")
    diet = page.locator("#filters input[name=diet]").first
    dcode = diet.get_attribute("value")
    diet.check()
    page.locator("#fshow").click()
    shown = page.locator(".dish:not([hidden])")
    n = shown.count()
    assert 0 < n < total
    assert page.locator(f".dish:not([hidden]):not([data-diet~='{dcode}'])").count() == 0
    # search
    page.locator("#freset").click()
    page.click("#fbtn")
    page.fill("#fq", "pizza")
    page.wait_for_timeout(0)
    assert page.locator(".dish:not([hidden])").count() < total
    note("07", menu="chez-gino", dishes=total, allergen=code, hidden_by_allergen=with_code,
         diet=dcode, shown_by_diet=n, legend_items=page.locator("#legend li").count())


# 8 -------------------------------------------------------------------------------------------
def test_08_sold_out_greyed_not_hidden(diner):
    found = []
    for slug in SLUGS:
        page = open_menu(diner(), slug)
        sold = page.locator(".dish[data-sold]")
        if not sold.count():
            continue
        d = sold.first
        assert d.is_visible()
        info = page.evaluate(
            """() => { const d=document.querySelector('.dish[data-sold]'); const n=d.querySelector('.dish-name'); const p=d.querySelector('.pa');
            const o=document.querySelector('.dish:not([data-sold]) .dish-name');
            return {name:d.querySelector('.dish-name').textContent.trim(), color:getComputedStyle(n).color, normal:getComputedStyle(o).color,
                    strike:getComputedStyle(p).textDecorationLine, pill:!!d.querySelector('.pill'), pilltxt:d.querySelector('.pill')&&d.querySelector('.pill').textContent,
                    photo:d.querySelector('.dish-thumb')?getComputedStyle(d.querySelector('.dish-thumb')).filter+' '+getComputedStyle(d.querySelector('.dish-thumb')).opacity:null}}"""
        )
        found.append({"slug": slug, **info})
        assert info["pill"]
        assert info["color"] != info["normal"] or "line-through" in info["strike"]
    note("08", found=found)
    assert found, "no sold-out dish in any seeded menu"


# 9 -------------------------------------------------------------------------------------------
TARGETS = """() => { const out=[]; const sel='a[href],button,input:not([type=hidden]),select,summary,textarea,[tabindex]:not([tabindex="-1"])';
 for (const e of document.querySelectorAll(sel)) { const cs=getComputedStyle(e); if (cs.visibility==='hidden'||cs.display==='none') continue;
  if (e.closest('[hidden]')||e.closest('dialog:not([open])')) continue; let r=e.getBoundingClientRect(); if(!r.width&&!r.height) continue;
  if (e.classList.contains('skip')) continue;
  if (e.classList.contains('dish-link')) r=e.closest('.dish, .sp').getBoundingClientRect(); /* ::after stretches the link over the whole row */
  const label=e.getAttribute('aria-label')||e.textContent.trim().slice(0,30); out.push({t:e.tagName.toLowerCase()+'.'+[...e.classList].join('.'), w:Math.round(r.width), h:Math.round(r.height), label}) } return out }"""


@pytest.mark.parametrize("width", [375, 1280])
@pytest.mark.parametrize("slug", SLUGS)
def test_09_tap_targets(diner, slug, width):
    page = open_menu(diner(width, 812 if width < 600 else 900), slug)
    items = page.evaluate(TARGETS)
    small = [i for i in items if i["w"] < 44 or i["h"] < 44]
    note("09", slug=slug, width=width, checked=len(items), small=small[:8])
    assert not small, small[:6]


# 10 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("width", [320, 375, 1280])
@pytest.mark.parametrize("slug", SLUGS)
def test_10_no_horizontal_scroll(diner, slug, width):
    page = open_menu(diner(width, 700), slug)
    m = page.evaluate("({sw: document.documentElement.scrollWidth, bw: document.body.scrollWidth, w: innerWidth})")
    note("10", slug=slug, width=width, **m)
    assert m["sw"] <= m["w"] and m["bw"] <= m["w"], m
    page.locator(".dish-link").first.click()
    m2 = page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert m2


# 11 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_11_footer(diner, slug):
    page = open_menu(diner(), slug)
    foot = page.locator("footer.foot")
    maps = foot.locator("address a")
    tel = foot.locator("a.tel")
    rows = foot.locator(".hours dl > div")
    data = {"maps": maps.first.get_attribute("href"), "tel": tel.first.get_attribute("href"),
            "hours_rows": rows.count(), "hours_first": rows.first.inner_text().replace("\n", " ")}
    note("11", slug=slug, **data)
    assert re.match(r"https?://", data["maps"]) and data["tel"].startswith("tel:")
    assert data["hours_rows"] >= 1


# 12 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_12_five_second_test(diner, slug):
    page = open_menu(diner(375, 812), slug)
    SCREENS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENS / f"fold-{slug}-375x812.png"))
    fold = page.evaluate(
        """() => { const H=innerHeight; const vis=e=>{const r=e.getBoundingClientRect();return r.top<H&&r.bottom>0&&r.height>0};
        return {name:document.querySelector('h1').textContent.trim(), h1_in_fold:vis(document.querySelector('h1')),
          logo:!!document.querySelector('.logo'), tagline:(document.querySelector('.tagline')||{}).textContent||null,
          today: (()=>{const t=document.querySelector('.today'); if(!t) return null; const r=t.getBoundingClientRect();
                      return {in_fold:r.top<H, top:Math.round(r.top), visible_bottom:Math.round(Math.min(r.bottom,H)), title:(t.querySelector('h2')||{}).textContent,
                              first:(t.querySelector('.sp-title')||{}).textContent}})(),
          bar:(()=>{const b=document.querySelector('.bar'); if(!b) return null; const r=b.getBoundingClientRect();
                    return {top:Math.round(r.top), in_fold:r.top<H, chips:[...b.querySelectorAll('a')].filter(a=>{const q=a.getBoundingClientRect();return q.left<innerWidth&&q.right>0}).map(a=>a.textContent.trim())}})(),
          firstCat:(()=>{const c=document.querySelector('.cat h2'); return {text:c.textContent, in_fold:vis(c)}})(),
          title: document.title, lang: document.documentElement.lang} }"""
    )
    note("12", slug=slug, **fold)
    assert fold["h1_in_fold"]
    assert fold["bar"] is None or fold["bar"]["in_fold"]
    if fold["today"]:
        assert fold["today"]["in_fold"]


# 13 ------------------------------------------------------------------------------------------
MOTION = """() => { let max=0, worst=null; const dur=s=>Math.max(...s.split(',').map(x=>parseFloat(x)*(x.includes('ms')?1:1000)||0));
 for (const e of document.querySelectorAll('*,*::before,*::after')) { const cs=getComputedStyle(e);
  const d=Math.max(dur(cs.transitionDuration), cs.animationName==='none'?0:dur(cs.animationDuration));
  if (d>max){max=d;worst=e.tagName+'.'+e.className} } return {max,worst} }"""


@pytest.mark.parametrize("slug", SLUGS)
def test_13_reduced_motion_and_durations(diner, slug):
    ctx = diner(reduced_motion="reduce")
    page = open_menu(ctx, slug)
    assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") != "smooth"
    page.locator(".dish-link").first.click()
    anim = page.evaluate("getComputedStyle(document.getElementById('sheet')).animationName")
    assert anim == "none", f"sheet animates under reduced motion: {anim}"
    reduced = page.evaluate(MOTION)
    ctx2 = diner(reduced_motion="no-preference")
    p2 = open_menu(ctx2, slug)
    p2.locator(".dish-link").first.click()
    normal = p2.evaluate(MOTION)
    sheet_anim = p2.evaluate("(()=>{const s=getComputedStyle(document.getElementById('sheet'));return [s.animationName,s.animationDuration]})()")
    note("13", slug=slug, reduced_max_ms=reduced["max"], normal_max_ms=normal["max"], normal_worst=normal["worst"], sheet=sheet_anim)
    assert reduced["max"] <= 200 and normal["max"] <= 200, (reduced, normal)


# 14 ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_14_type_sizes_tabular_numerals(diner, slug):
    page = open_menu(diner(), slug)
    r = page.evaluate(
        """() => { const px=e=>parseFloat(getComputedStyle(e).fontSize);
        const sizes={}; const small=[];
        for (const sel of ['body','.dish-name','.dish-desc','.sp-desc','.cat-desc','.tagline','.note','address','.hours dd','.hours dt','.bar a','.pill','.dish-prices','.legend li','.lang a']) {
          const e=document.querySelector(sel); if(e) sizes[sel]=px(e) }
        const nums=[...document.querySelectorAll('.dish-prices,.hours dl div,.sp-row .dish-prices')].map(e=>getComputedStyle(e).fontVariantNumeric);
        return {sizes, tab: nums.every(n=>n.includes('tabular-nums')), n:nums.length} }"""
    )
    note("14", slug=slug, **r)
    assert r["sizes"]["body"] >= 16
    for sel in (".dish-name", ".dish-desc", ".sp-desc", ".note", "address"):
        if sel in r["sizes"]:
            assert r["sizes"][sel] >= 16 or sel == ".note", (sel, r["sizes"][sel])
    assert r["tab"] and r["n"] > 0


# 15 ------------------------------------------------------------------------------------------
def _luminance(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _rgb(s):
    return [float(x) for x in re.findall(r"[\d.]+", s)[:3]]


ADMIN_PW = os.environ.get("DINER_ADMIN_PASSWORD", "")


@pytest.mark.skipif(not ADMIN_PW, reason="DINER_ADMIN_PASSWORD not set")
@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("theme", ["bistro", "trattoria", "cafe", "gastro", "auberge"])
def test_15_theme_modes_and_photos(diner, theme, mode):
    ctx = diner(375, 812)
    login = ctx.new_page()
    login.goto("/admin/login/")
    login.fill("input[name=username]", os.environ.get("DINER_ADMIN_USER", "admin"))
    login.fill("input[name=password]", ADMIN_PW)
    login.click("button[type=submit]")
    login.wait_for_url("**/admin/")
    slug = "chez-gino"  # 80 items: most demanding layout
    out = {}
    SCREENS.mkdir(parents=True, exist_ok=True)
    for photos in ("1", "0"):
        page = ctx.new_page()
        page.goto(f"/m/{slug}/?preview=1&theme={theme}&mode={mode}&photos={photos}")
        page.wait_for_load_state("load")
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        cs = page.evaluate(
            """() => { const g=(s,p)=>getComputedStyle(document.querySelector(s))[p];
            return {bg:g('body','backgroundColor'), ink:g('.cat .dish-name','color'), desc:g('.cat .dish-desc','color'), scheme:getComputedStyle(document.documentElement).colorScheme,
                    imgs:document.querySelectorAll('.dish-thumb').length, imgVisible:[...document.querySelectorAll('.dish-thumb')].filter(i=>i.offsetWidth>0).length} }"""
        )
        bg = _rgb(cs["bg"])
        c_ink, c_desc = _contrast(_rgb(cs["ink"]), bg), _contrast(_rgb(cs["desc"]), bg)
        out[f"photos{photos}"] = {"bg": cs["bg"], "ink_contrast": round(c_ink, 1), "desc_contrast": round(c_desc, 1),
                                  "imgs_visible": cs["imgVisible"]}
        assert c_ink >= 4.5 and c_desc >= 4.5, cs
        # dark mode must actually be dark, light must be light
        assert (_luminance(bg) < 0.2) == (mode == "dark"), cs["bg"]
        if photos == "0":
            assert cs["imgVisible"] == 0
        if photos == "1":
            assert cs["imgs"] > 0
        page.screenshot(path=str(SCREENS / f"theme-{theme}-{mode}-photos{photos}.png"))
        page.close()
    note("15", theme=theme, mode=mode, **out)


# 1b ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("slug", SLUGS)
def test_01b_paint_times_on_fast_4g(diner, slug):
    """Cold-cache FCP/LCP with CDP 'Fast 4G' (9 Mbit/s, 70 ms RTT) and 4x CPU slowdown; median of 3."""
    ctx = diner(375, 812)
    fcps, lcps = [], []
    for _ in range(3):
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.clearBrowserCache")
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False, "latency": 70, "downloadThroughput": 9 * 1024 * 1024 / 8,
            "uploadThroughput": 3 * 1024 * 1024 / 8})
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        page.add_init_script(
            "window.__lcp=0;new PerformanceObserver(l=>{for(const e of l.getEntries())window.__lcp=e.startTime})"
            ".observe({type:'largest-contentful-paint',buffered:true})"
        )
        page.goto(f"/m/{slug}/", wait_until="load")
        page.wait_for_timeout(500)  # LCP candidates are only final after a short settle (measurement, not a sync wait)
        fcp = page.evaluate("performance.getEntriesByName('first-contentful-paint')[0].startTime")
        lcp = page.evaluate("window.__lcp")
        fcps.append(fcp)
        lcps.append(lcp)
        page.close()
    fcp, lcp = sorted(fcps)[1], sorted(lcps)[1]
    note("01b", slug=slug, fcp_ms=round(fcp), lcp_ms=round(lcp))
    assert fcp < 1000, f"FCP {fcp:.0f} ms"
    assert lcp < 2500, f"LCP {lcp:.0f} ms"
