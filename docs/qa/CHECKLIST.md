# Diner-UX checklist

Run against the Docker/Caddy stack (`docker compose -p qrmenu-qa`, seeded demo data, no API key),
Playwright Chromium at 375x812 unless noted; code: `e2e/test_diner_checklist.py`
(`DINER_BASE=http://localhost:8080 DINER_ADMIN_PASSWORD=... uv run pytest e2e/test_diner_checklist.py`;
skipped when `DINER_BASE` is unset). Screenshots: `docs/qa/screens/`. Lighthouse: `docs/qa/lighthouse.md`.
Result (whole e2e folder against the stack): 94 passed, 2 skipped (by-design cases below), 0 failed.

Note on the demo data: petit-kiosque has one category and no plat du jour, so by design it renders no chip bar
and no "Aujourd'hui" section; the checks that need them use the other four menus.

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Loads < 1 s on 4G, page weight | **PASS** (with a Lighthouse caveat) | Fast 4G (9 Mbit/s, 70 ms RTT, 4x CPU, cold cache, median of 3): FCP = LCP = 272-384 ms on all 5 menus. Weight over the wire (gzip via Caddy): HTML 9.9-17.1 KB (limit 20), JS 3.0 KB (limit 6), fonts 64-114 KB, total 113-365 KB (petit-kiosque 113, auberge 219, chez-gino 243, maison-vialle 295, bistrot 365 of which 280 photos). Lighthouse *Slow 4G simulation*: FCP 0.8-1.2 s, LCP 1.5-3.0 s, so under Lighthouse's harsher profile only petit-kiosque has FCP < 1 s; see Lighthouse findings (bistrot LCP 3.0 s, Perf 94). |
| 2 | No popups / cookie banner, no cookies for anonymous | **PASS** | All 5 menus: no `dialog`/`alert`, no `dialog[open]`, no new tabs, body text has no cookie/consent/newsletter wording, `context.cookies() == []` after load and scroll; HTTP response has no `Set-Cookie`. |
| 3 | Sticky chip bar, scroll-spy | **PASS** | 4 menus with a bar: `.bar` computed `position: sticky`, `getBoundingClientRect().top <= 1` at every section, and `aria-current="true"` moves to the matching chip for each of 3-11 sections (Aujourd'hui + every category); tapping the last chip scrolls to its section and highlights it. petit-kiosque: no bar (single category), skipped. |
| 4 | FR/EN remembered on reload and new visit | **PASS** | Click EN: `html[lang=en]`; after reload still en; a new page in the same profile still en, and another menu (chez-gino) opens in en. Cookie `menu_lang`, 365 days, SameSite=Lax, not HttpOnly (preference cookie). A visitor with `Accept-Language: en-GB` gets EN with no cookie. |
| 5 | Specials at the top | **PASS** | 4 menus with specials: DOM order `head, bar, today, cat`; "Aujourd'hui" card top at y=256-291 px (first screen 812 px), first category at y=632-740. |
| 6 | Dish bottom sheet; Back closes it without leaving | **PASS** | All 5: tapping a dish link opens `dialog#sheet` (URL gets `#dish-N`/`#sp-N`); `history.back()` closes it and stays on `/m/<slug>/`; forward re-opens; Escape closes; a deep link `/m/<slug>/#dish-N` opens the sheet on load and its close button leaves the page in place. |
| 7 | Allergen and diet filters, legend | **PASS** | chez-gino (81 dishes): legend `#legend` with 12 entries; ticking "gluten" hides exactly the 43 dishes with `data-al~=gluten`, status line + reset restore all; diet "vegetarian" leaves 41 dishes, none without the diet; text search narrows the list. |
| 8 | Sold-out greyed, not hidden | **PASS** | Present and visible in bistrot and chez-gino (`[data-sold]`): name colour rgb(92,79,71) vs normal rgb(33,26,23), price `line-through`, "Épuisé" pill, photo `grayscale(1)` + opacity .55. |
| 9 | Tap targets >= 44 px | **PASS** | 9-99 interactive elements per menu checked at 375 and 1280: none under 44x44 (lang switch, chips, filter button, footer links, sheet close). Dish links are text-height (23-28 px) but a `::after{inset:0}` overlay stretches the hit area over the whole row (`static/public/css/base.css:110`), so the row rect is what was measured. |
| 10 | No horizontal scroll at 320/375/1280 | **PASS** | `scrollWidth == innerWidth` for all 5 menus x 3 widths, also with the sheet open. |
| 11 | Footer: maps link, `tel:`, hours | **PASS** | All 5: `address a` -> `https://www.google.com/maps/search/?api=1&query=...`; `a.tel` -> `tel:+33...`; hours table has 1-4 rows (e.g. "Mardi - Samedi 12h - 14h, 19h - 22h"). |
| 12 | 5-second test (375x812) | **PASS** | See below; screenshots `docs/qa/screens/fold-<slug>-375x812.png`. |
| 13 | prefers-reduced-motion, transitions <= 200 ms | **PASS** (note) | Reduced: `scroll-behavior` not smooth, sheet `animation-name: none`. Longest transition/animation on any element: 200 ms (sheet-in, normal) and 150 ms (chip colour, also present under reduced motion). Note: the 150 ms colour transition is not switched off under reduced motion; harmless but not strictly "respected". **Fixed:** chip colour transition now only under `prefers-reduced-motion: no-preference`. |
| 14 | Body >= 16 px, tabular numerals | **PASS** (note) | body 16-17 px, dish name 18-21, description 16-17, prices 16-19, address and hours 16-17; `font-variant-numeric: lining-nums tabular-nums` on every `.dish-prices` and hours row (7-89 checked per menu). Secondary text is smaller: `.note` 14, `.lang a` 14, `.pill` 13, legend 15, and on maison-vialle the tagline and chips are 13 px. **Resolution:** kept by design (uppercase, letter-spaced labels); gastro price labels raised from 12 to 13 px. |
| 15 | Light + dark for every theme; with/without photos | **PASS** | Admin preview `?preview=1&theme=T&mode=M&photos=0/1` on chez-gino (81 items), 5 themes x light/dark x photos on/off: `data-theme` applied, body background dark (luminance < 0.2) in dark and light in light, dish name contrast 12.7-17.8:1 and description 6.1-8.6:1, no horizontal scroll, photos absent with `photos=0` and present with `photos=1`. Screenshots `docs/qa/screens/theme-<theme>-<mode>-photos<0|1>.png`. |

## 12. Above the fold at 375x812 (bistrot-des-halles as the example)
Top to bottom: FR/EN switch (top right), round logo, restaurant name "Le Bistrot des Halles" in large serif,
tagline "Cuisine du marche, produits de Correze", a sticky chip bar (`Aujourd'hui | Entrees | Plats | ...`
scrolling sideways, plus a "Filtrer" button), then the "AUJOURD'HUI" card with the plat du jour
(Blanquette de veau 15,50 EUR) and the formule (19,90/23,90 EUR), and the first heading "ENTREES" starting
at the bottom edge. A diner can tell: the name (h1 in fold on all 5), that it is a menu (chips are category
names, prices, dishes), today's special (card in fold on all 4 menus that have one, 256-291 px from the top)
and where categories are (chip bar in fold, top at 200-235 px). Weakness: nothing literally says "Menu" or
"Carte" on the bistrot-style pages; it is inferred. petit-kiosque (no specials, one category) shows name,
tagline and a "Carte" heading with dishes straight away.

## Docker/Caddy stack checks (Part 1)
- `/healthz` 200 and `/m/<slug>/` 200 for all 5 seeded menus through Caddy (gzip sizes 8.8-16.1 KB).
- `/media/...` served by Caddy: `Cache-Control: public, max-age=2592000`, ETag, Last-Modified, `Server: Caddy`.
- `/static/...` hashed files: `Cache-Control: max-age=315360000, public, immutable` (JS and WOFF2).
- Menu HTML: strong `ETag` and `Cache-Control: no-cache`; sending it back as `If-None-Match` returns `304`.
- Admin login works (admin user from `.env`). No `ANTHROPIC_API_KEY`: no "Import photo"/translate buttons in the editor
  (actions: Settings, Print & QR, View menu), the new-restaurant page has no "Start from a photo" button, and
  `/admin/r/<pk>/import/` returns 200 with "AI import is turned off" and instructions, plus a back link.

## Bugs / observations to report (no app code was changed)
1. ~~`/favicon.ico` 404 on all menus~~ **fixed** (`<link rel="icon">`, Best Practices 100).
2. ~~bistrot-des-halles Lighthouse Performance 94-95~~ **fixed**: now 98-99 (small WebP header logo +
   dish-name font preload), see `docs/qa/lighthouse.md`.
3. Minor: 13 px tagline and chips on maison-vialle (gastro), 14 px `.lang a` and `.note`, `.pill` 13 px. Kept by design (labels, not body text); gastro price labels raised to 13 px.
4. ~~Minor: 150 ms colour transitions stay active under `prefers-reduced-motion`~~ **fixed**.
