"""Design screenshots and automated gates for the public menu.

Needs a running dev server (default http://127.0.0.1:8003) with `seed_demo` data and the admin
user (admin / devpassword123), because theme/mode/photos overrides use the admin-only preview URL.

    uv run python scripts/screenshots.py --out /tmp/shots                 # full matrix
    uv run python scripts/screenshots.py --themes bistro --modes light --widths 375 --out /tmp/x
    uv run python scripts/screenshots.py --gates                          # overflow / tap-target / console gates
    uv run python scripts/screenshots.py --interactions --out docs/screenshots
    uv run python scripts/screenshots.py --contact --out docs/screenshots  # contact sheets (needs the matrix)

Output names: <theme>-<mode>-<width>[-nophotos].png (+ -scroll for the mobile mid-menu crop).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

THEMES = ["bistro", "trattoria", "cafe", "gastro", "auberge"]
NATIVE = {
    "bistro": "bistrot-des-halles", "trattoria": "chez-gino", "cafe": "petit-kiosque",
    "gastro": "maison-vialle", "auberge": "auberge-du-puy-blanc",
}
SIZES = {375: (375, 812, 2), 1280: (1280, 900, 1)}


def login(ctx, base):
    pg = ctx.new_page()
    pg.goto(f"{base}/admin/login/")
    pg.fill("input[name=username]", "admin")
    pg.fill("input[name=password]", "devpassword123")
    with pg.expect_navigation():
        pg.keyboard.press("Enter")
    return pg


def url_for(base, slug, theme, mode, photos=True, lang=None, extra=""):
    u = f"{base}/m/{slug}/?preview=1&theme={theme}&mode={mode}"
    if not photos:
        u += "&photos=0"
    if lang:
        u += f"&lang={lang}"
    return u + extra


def new_ctx(browser, width, dark=None):
    w, h, dpr = SIZES.get(width, (width, 900, 1))
    return browser.new_context(
        viewport={"width": w, "height": h}, device_scale_factor=dpr, has_touch=w < 700, is_mobile=w < 700,
        reduced_motion="reduce", color_scheme="light",
    )


def settle(pg):
    """Scroll through the page so lazy images load, then return to the top."""
    h = pg.evaluate("document.documentElement.scrollHeight")
    y = 0
    while y < h:
        pg.evaluate(f"window.scrollTo(0,{y})")
        pg.wait_for_timeout(60)
        y += 700
    pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(500)


def save(pg, path: Path, full=False, fmt="png"):
    path.parent.mkdir(parents=True, exist_ok=True)
    if full:
        settle(pg)
    if fmt == "png":
        pg.screenshot(path=str(path), full_page=full)
    else:
        tmp = path.with_suffix(".tmp.png")
        pg.screenshot(path=str(tmp), full_page=full)
        from PIL import Image

        Image.open(tmp).save(path.with_suffix(".webp"), quality=84, method=6)
        tmp.unlink()


def slug_for(args, theme):
    return NATIVE[theme] if args.slug == "native" else args.slug


def matrix(args, browser):
    out = Path(args.out)
    for width in args.widths:
        ctx = new_ctx(browser, width)
        pg = login(ctx, args.base)
        for theme in args.themes:
            for mode in args.modes:
                for photos in args.photos:
                    name = f"{theme}-{mode}-{width}" + ("" if photos else "-nophotos")
                    pg.goto(url_for(args.base, slug_for(args, theme), theme, mode, photos))
                    pg.wait_for_load_state("networkidle")
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(250)
                    if width < 700:
                        save(pg, out / f"{name}.png", fmt=args.format)
                        pg.evaluate(f"window.scrollTo(0,{args.scroll})")
                        pg.wait_for_timeout(300)
                        save(pg, out / f"{name}-scroll.png", fmt=args.format)
                    else:
                        save(pg, out / f"{name}.png", full=True, fmt=args.format)
                    print("shot", name)
        ctx.close()


GATES_JS = """() => {
  const r = {};
  r.overflow = document.documentElement.scrollWidth - innerWidth;
  const small = [];
  for (const el of document.querySelectorAll('a, button, input:not([type=hidden]), label.arow, label.dchip')) {
    if (el.closest('[hidden]') || el.closest('dialog:not([open])') || el.classList.contains('skip')) continue;
    if (el.classList.contains('dish-link')) continue;            // stretched over the whole row
    const b = el.getBoundingClientRect();
    if (b.width === 0 || b.height === 0) continue;
    if (el.tagName === 'INPUT' && el.closest('label')) continue;  // its label is the target
    if (b.height < 43.5 || b.width < 43.5) small.push(el.tagName + '.' + el.className + ' ' + Math.round(b.width) + 'x' + Math.round(b.height) + ' ' + (el.textContent || '').trim().slice(0, 20));
  }
  r.small = small;
  return r;
}"""


def gates(args, browser):
    ok = True
    for width in (320, 375, 1280):
        ctx = new_ctx(browser, width)
        pg = login(ctx, args.base)
        errors = []
        pg.on("console", lambda m, errors=errors: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
        for theme in args.themes:
            for mode in args.modes:
                for slug in args.gate_slugs:
                    pg.goto(url_for(args.base, slug, theme, mode))
                    pg.wait_for_load_state("networkidle")
                    r = pg.evaluate(GATES_JS)
                    bad = r["overflow"] > 0 or r["small"]
                    ok &= not bad
                    print(("FAIL" if bad else "ok  "), width, theme, mode, slug, r if bad else "")
        if errors:
            ok = False
            print("console errors:", set(errors))
        ctx.close()
    return ok


def interactions(args, browser):
    out = Path(args.out)
    ctx = new_ctx(browser, 375)
    pg = login(ctx, args.base)
    theme = args.themes[0]
    pg.goto(url_for(args.base, slug_for(args, theme), theme, args.modes[0]))
    pg.wait_for_load_state("networkidle")
    # dish sheet
    pg.locator(".dish-link").nth(0).click()
    pg.wait_for_timeout(400)
    save(pg, out / f"{theme}-sheet.png", fmt=args.format)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    # filter sheet with two filters
    pg.locator("#fbtn").click()
    pg.wait_for_timeout(300)
    pg.locator("input[name=diet][value=vegetarian]").check(force=True)
    pg.locator("input[name=al][value=gluten]").check(force=True)
    pg.wait_for_timeout(200)
    save(pg, out / f"{theme}-filters.png", fmt=args.format)
    pg.locator("#fshow").click()
    pg.wait_for_timeout(400)
    save(pg, out / f"{theme}-filtered.png", fmt=args.format)
    ctx.close()


def contact(args):
    from PIL import Image

    out = Path(args.out)
    for theme in args.themes:
        tiles = []
        for mode in ("light", "dark"):
            for suffix in ("", "-scroll"):
                for ext in (".png", ".webp"):
                    p = out / f"{theme}-{mode}-375{suffix}{ext}"
                    if p.exists():
                        tiles.append(Image.open(p).convert("RGB"))
                        break
        if not tiles:
            continue
        h = max(t.height for t in tiles)
        sheet = Image.new("RGB", (sum(t.width for t in tiles) + 24 * (len(tiles) - 1), h), "#888888")
        x = 0
        for t in tiles:
            sheet.paste(t, (x, 0))
            x += t.width + 24
        sheet.save(out / f"contact-{theme}.png" if args.format == "png" else out / f"contact-{theme}.webp", quality=84)
        print("contact", theme)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8003")
    ap.add_argument("--out", default="docs/screenshots")
    ap.add_argument("--slug", default="native", help="a slug, or native = each theme's own demo restaurant")
    ap.add_argument("--themes", default=",".join(THEMES))
    ap.add_argument("--modes", default="light,dark")
    ap.add_argument("--widths", default="375,1280")
    ap.add_argument("--photos", default="on,off", help="on, off or on,off")
    ap.add_argument("--scroll", type=int, default=1500, help="mobile mid-menu crop offset")
    ap.add_argument("--format", default="png", choices=["png", "webp"])
    ap.add_argument("--gates", action="store_true")
    ap.add_argument("--gate-slugs", default="bistrot-des-halles,chez-gino,petit-kiosque,maison-vialle,auberge-du-puy-blanc")
    ap.add_argument("--interactions", action="store_true")
    ap.add_argument("--contact", action="store_true")
    ap.add_argument("--no-matrix", action="store_true")
    args = ap.parse_args()
    args.themes = args.themes.split(",")
    args.modes = args.modes.split(",")
    args.widths = [int(w) for w in args.widths.split(",")]
    args.photos = [p == "on" for p in args.photos.split(",")]
    args.gate_slugs = args.gate_slugs.split(",")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ok = True
        if args.gates:
            ok = gates(args, browser)
        elif args.interactions:
            interactions(args, browser)
        elif not args.contact and not args.no_matrix:
            matrix(args, browser)
        browser.close()
    if args.contact:
        contact(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
