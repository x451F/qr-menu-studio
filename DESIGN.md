# QR Menu Studio: public menu design

Status: implemented. Sections 1-9 are the approved design; section 10 lists the review amendments and every place the build differs from the proposal.
Inputs: `public/menu_context.py` (template context), `menus/constants.py`, `menus/seed_data.py`, docs/ARCHITECTURE.md (performance targets).

The public menu is what restaurant owners judge. The bar is "a well-designed restaurant website",
not "a menu template": real typography, a considered colour system, one strong idea per theme,
and zero framework look. No emoji, no stock gradients, no drop-shadow soup, no Bootstrap radii.

---

## 1. Shared UX architecture

### 1.1 Principle: one semantic document, five skins

There is exactly one template (`templates/public/menu.html`, plus small partials) and one shared
stylesheet (`base.css`, layout and components, ~9 KB minified). Each theme adds a small stylesheet
(`theme-<name>.css`, ~3 KB) and a palette from `theming.py`. The root element carries
`<html lang="fr" data-theme="bistro" data-mode="auto|light|dark">`.

Themes differ by:
1. CSS custom properties (fonts, radii, density, rules, palette),
2. a theme stylesheet that restyles the *same* selectors (heading treatment, row style, chip style, specials block, photo frame),
3. decorative details drawn only in CSS (`::before/::after`, gradients as hairlines, inline SVG data-URIs for ornaments), so the DOM stays identical and testable.

Only the active theme's CSS and fonts are sent. Both CSS files are **inlined** into `<style>` by a
template tag (`{% inline_css theme %}`, reads from disk, `lru_cache`d, re-read when DEBUG).
QR visitors are mostly first-time on 4G, so a second blocking request costs more than the bytes it saves.

### 1.2 Page anatomy (mobile, top to bottom)

```
<a class="skip">Aller à la carte</a>
<header>      lang switch (top-right) · logo · h1 name · tagline
<nav>         sticky category chips, first chip "Aujourd'hui" when specials (+ "Filtrer" button when JS)
<main>        <section id="today"> specials (only if any), then <section id="cat-N"> h2 + description + <ul class="dishes"> rows
<section id="legend">  allergen & diet legend (only codes used on this menu)
<footer>      address → maps, phone → tel:, hours, footer note
<dialog class="sheet" id="sheet">   dish detail   (JS only)
<dialog class="sheet" id="filters"> search + filters (JS only)
```

Landmarks: `header` (banner), `nav aria-label="Catégories"`, `main`, `footer` (contentinfo). Headings:
`h1` restaurant, `h2` category (and "Aujourd'hui"), `h3` dish.

### 1.3 Components (behaviour with and without JS)

**Header.** Language switch is a two-item segmented control of real links
(`<a href="?lang=en" hreflang="en" lang="en">EN</a>`), each at least 44x44 px, top-right, visible
without scrolling on every theme. Works without JS (server sets the cookie). Logo max 64 px high /
180 px wide, `width/height` attributes, `alt=""` when the name is displayed next to it (always: name and
tagline are always rendered as text; the logo never replaces the `h1`). No logo: the name in the theme's
display face is the identity.

**Specials block ("Aujourd'hui").** Right after the header, before the chip bar, so it scrolls away
and the sticky bar takes over. One card containing every active special as a row: eyebrow
(`kind_label`: "Plat du jour", "Formule du jour"...) in accent colour, title in display face, description,
prices (same two-column price component as dishes). 1 to 4 specials, no carousel. Pure HTML, no JS.
Absent when `menu.specials` is empty (no empty frame).

**Category chip bar.** `<nav><ul>` of anchor chips (`href="#cat-12"`), sticky at `top: 0`,
horizontally scrollable (`overflow-x: auto; scroll-snap-type: x proximity`, scrollbar hidden, soft edge
fade through `mask-image`), chips 44 px high. Hidden when there is one category.
- *Without JS*: anchors jump natively; `scroll-margin-top: calc(var(--bar-h) + 12px)` on sections keeps
  headings clear of the bar; `scroll-behavior: smooth` only under `prefers-reduced-motion: no-preference`.
  No active state.
- *With JS*: scroll-spy (`IntersectionObserver`, `rootMargin: -(bar+8px) 0 -65% 0`) sets
  `aria-current="true"` on the chip of the section under the bar and scrolls the bar sideways
  (`bar.scrollLeft`, never `scrollIntoView`, so the page never jumps) to keep the active chip centred.
  Tapping a chip uses `history.replaceState` for the hash, so Back is never polluted by chip taps.
- *At >= 1024 px* the same `<nav>` becomes a vertical sticky sidebar (220 px, `top: 24px`), the
  editorial "table of contents" layout, active item marked by a bar in `--brand-ui`.

**Dish row.** `<li class="dish" id="dish-12" data-al="gluten milk" data-diet="vegetarian" data-sold="0|1" data-sheet>`:
```
h3.dish-name                       .dish-prices  (right column, tabular numerals)
p.dish-desc (omitted when empty)
ul.dish-tags  (allergen + diet icons, each with visually-hidden label)
[img.dish-thumb]                   (only when photo exists)
```
- Name left, price right-aligned in its own column that never shrinks (`flex: none`, `min-width: 5.5ch`,
  `font-variant-numeric: lining-nums tabular-nums`), so decimals line up down the whole menu.
- Long names wrap inside the left column (`text-wrap: pretty`, `overflow-wrap: anywhere` as a last resort); the price
  stays on the first line, top-aligned with the first line of the name.
- Two or more prices stack in the right column, one per line: muted label left of amount
  (`25 cl  4,00 €` / `50 cl  7,50 €`, `Verre  5,50 €` / `Bouteille  28,00 €`); amounts share one right edge.
  Labels are 14 px `--ink-2`, amounts 17 px.
- No description: the row is simply shorter (no placeholder, no gap).
- **Sold out**: never hidden. Row gets `data-sold="1"`; name and price switch to `--ink-2`
  (still AA), price is struck through, a pill "Épuisé" / "Sold out" sits after the name, photo is desaturated
  (`filter: grayscale(1); opacity: .55`). The pill text is real text (screen readers read it).
- **Tags**: allergens are 18 px outline icons in `--ink-2`; diets are 18 px icons inside a filled
  circle in `--brand-soft` with `--brand-text` glyph, so "good news" reads differently from "warning".
  Each is `<li><svg aria-hidden><use href="#al-gluten"/></svg><span class="sr-only">Gluten</span></li>`.
  Hover/long-press is not relied on; meaning is taught by the legend and the sheet.

**Photo treatment (per row).** Thumbnail on the right, 88 px square on mobile, 112 px at >= 720 px, fixed
box (`aspect-ratio: 1`, `object-fit: cover`) so there is no layout shift; frame style per theme (section 3). No photo: no
box, no placeholder, ever. Full details in section 5.

**Dish detail bottom sheet** (JS only; rows with a photo, allergens or diets get `data-sheet`).
Native `<dialog>` opened with `showModal()`: focus trap, `Esc`, inert background and `aria-modal` come free.
- Content is *cloned from the row* (name, description, prices, tags with labels) so markup is not duplicated in the HTML;
  the large photo comes from `data-photo` / `data-srcset` on the row and is only fetched when the sheet opens.
- Layout: drag handle (40x4), photo (full width, max 4:3), `h2` name, prices, full description, "Allergènes" list
  (icon + label, one per line), "Régimes" list, 44x44 close button (top-right over the photo, scrim behind it).
- Motion: open 200 ms (`translateY(24px)` and fade, `cubic-bezier(.2,.8,.2,1)`), backdrop 150 ms. Reduced motion: none.
- **History**: opening does `history.pushState({sheet:1}, "", "#dish-12")`. The browser Back button (`popstate`)
  closes the sheet. UI closes (X, backdrop tap, swipe, Esc) call `history.back()` when `history.state.sheet`, so
  the stack stays consistent. Cold load on `/m/x/#dish-12` opens the sheet with `replaceState` and marks the state `cold`;
  UI close then does `replaceState` to the bare URL instead of `back()` (otherwise the diner would leave the page).
  Forward re-opens it. Without JS the same URL scrolls to the dish, so dish links are shareable everywhere.
- **Swipe down**: pointer events on the handle/photo/header zone (and anywhere when `scrollTop === 0`). The sheet follows the finger
  (`transform`), closes on drag > 96 px or velocity > 0.5 px/ms, otherwise springs back in 180 ms. `overscroll-behavior: contain`
  and `html:has(dialog[open]) { overflow: hidden }` stop the page scrolling behind it. At >= 720 px it is a centred 560 px modal.

**Search and allergen/diet filter** (JS only; button "Filtrer" at the right end of the chip bar, 44 px, icon + label).
Opens the second sheet, "Rechercher et filtrer":
1. Search field (only if `item_count >= 20`): accent- and case-insensitive (`normalize("NFD")` stripped) match on name and
   description; live.
2. **Régimes** (show only): toggle chips "Végétarien", "Vegan", "Sans gluten". Vegetarian also matches dishes tagged vegan.
3. **Allergènes** ("Masquer les plats contenant"): checkboxes, 48 px rows, icon + label, only allergens present on this menu
   (`legend_allergens`). Checkbox is a real `<input type="checkbox">` styled with `accent-color` and a 3:1 border.
4. Footer button "Voir 37 plats" closes the sheet (count updates live); "Réinitialiser" link.
- Filtered rows get `hidden`; categories with zero visible rows and their chips are hidden too. A sticky one-line status under the bar
  ("2 filtres · 14 plats masqués · Réinitialiser") makes the state impossible to forget. Zero results shows a friendly empty state.
- **Safety wording** shown in the sheet: "Indication fournie par le restaurant. En cas d'allergie, demandez au personnel."
  Dishes with *no* allergen data are **not** hidden by an allergen filter (we cannot know); this is stated in the wording. State is
  in memory (plus `sessionStorage`, no cookies); a reload keeps it within the session.
- *Without JS*: the button does not exist (it is created by the script), every dish is shown, the legend explains every icon.

**Legend** (`#legend`, before the footer): title "Allergènes et régimes", a two-column list (one column at 320 px) of icon + text label for every
code used on this menu (`legend_allergens`, `legend_diets`), plus the note. Static HTML, always visible; the "no JS" and "print" path
for allergen information. Omitted if nothing is tagged.

**Footer.** `<address>` with a maps link ("Itinéraire", map-pin icon, 48 px row), phone as `tel:` link (`phone_href`, phone icon, 48 px row), hours as
a definition list: a line `"Mardi – Samedi : 12h – 14h, 19h – 22h"` is split at the first ` : ` into label and value (two columns, tabular);
lines without ` : ` (e.g. "Fermé le lundi") span both columns. Then `footer_note` in 14 px `--ink-2`. No "powered by" line.

### 1.4 UI strings needed in `public/strings.py` (FR / EN)

`skip` (Aller à la carte / Skip to menu), `categories` (Catégories / Categories), `today` (Aujourd'hui / Today), `sold_out` (Épuisé / Sold out),
`filter` (Filtrer / Filter), `filter_title` (Rechercher et filtrer / Search and filter), `search` (Rechercher un plat / Find a dish),
`diets_h` (Régimes / Diets), `allergens_h` (Allergènes / Allergens), `hide_containing` (Masquer les plats contenant / Hide dishes containing),
`show_n` (Voir {n} plats / Show {n} dishes), `reset` (Réinitialiser / Reset), `filter_note`, `no_results`, `close` (Fermer / Close),
`directions` (Itinéraire / Directions), `call` (Appeler / Call), `hours` (Horaires / Opening hours), `legend_title`, `language` (Langue / Language).

---

## 2. The 5-second test

Scenario: a diner at 375 px scans the QR, wants the *tarte tatin* and its price, on an 80-dish menu.

1. **Second 0 to 1: orientation.** The header is short (about 140 px on mobile without logo), the chip bar is at the top of the first screen.
   The chips *are* the table of contents: "Entrées · Plats · Fromages · Desserts · Vins...". A first-time visitor understands the structure without reading anything.
2. **Second 1 to 2: jump.** One tap on "Desserts" scrolls there (chip active state confirms it). On a long menu they may also scroll: the sticky bar keeps
   position awareness (scroll-spy) at all times.
3. **Second 2 to 4: scan.** Inside a category the eye follows a single left edge (names, semi-bold 17-18 px) and a single right edge (prices, tabular, one column).
   The name is the loudest thing in the row; descriptions are quieter (16 px, `--ink-2`); allergen icons are quietest. Rhythm is created by
   row padding (12 to 16 px vertical) plus a hairline between rows, not by boxes, so about 5 dishes fit per mobile screen.
4. **Second 4 to 5: price.** The price sits on the name's first line at a fixed right edge; the eye reads "Tarte tatin ......... 8,50 €" without
   crossing the description. Two-size items show both prices in the same column.
5. **Fallbacks.** If the dish is not found by scanning: search (menus of 20+ dishes) in the filter sheet, under the button that sits in the chip bar.
   Allergen constraints are one more tap, not a different mode.

Design rules that protect the test: names never truncate (wrap instead); prices never wrap or move; category headings are 1.6x to 2x the dish name size with generous top space
(section boundaries visible in peripheral vision); no more than one accent per row; sold-out dishes stay in place (stable positions).

---

## 3. Themes

Common rules (all themes):
- Body text 16 px minimum (`1rem`, line-height 1.5); dish names 17 to 20 px; meta (labels, tags, footer note) 14 px minimum; only uppercase eyebrows may drop to 13 px with 0.08em tracking.
  Fluid H1/H2 via `clamp()`. Root font-size is never set below 100%, so browser zoom and OS text size work.
- Spacing scale on a 4 px base: `--s1..--s8` = 4, 8, 12, 16, 24, 32, 48, 72 px. Row padding is `calc(var(--s3) * var(--density))`; page gutter 20 px (mobile), content column max 40rem (mobile/tablet), 44rem with sidebar at >= 1024.
- Motion: at most 200 ms, `transform` and `opacity` only; every animation wrapped in `@media (prefers-reduced-motion: no-preference)`.
- Neutral bases (`--bg --surface --ink --ink-2 --line --line-strong`) are fixed per theme and mode (below), lightly tinted toward the brand hue by `theming.py`; the brand colour is applied only through roles (section 4).
- Fonts: WOFF2 from Fontsource (`https://cdn.jsdelivr.net/fontsource/fonts/<id>@latest/latin-<weight>-normal.woff2`, latin-ext variants `latin-ext-<weight>-normal.woff2`), self-hosted under
  `static/public/fonts/<theme>/`. All OFL 1.1 (licence texts in `static/public/fonts/LICENSES/`). The `latin` subset already covers "Œ œ € NBSP – — ’"; `latin-ext` (Ÿ, Ł, ...) is declared with `unicode-range` and is never downloaded unless a character needs it.
  Every heading font is verified to contain Œ/œ, €, and (body faces) the `tnum` feature with `fonttools` during implementation; a face failing this is replaced.

### 3.1 `bistro`: "The brasserie carte"

*Mood/references*: zinc bar, bentwood chairs, the printed *ardoise* and paper *carte* of a Parisian brasserie, Lipp, Bouillon Chartier, Le Comptoir. Warm paper, ink, one burgundy.
*Strong idea*: **dotted leaders**. Every dish is a line of a printed menu: name . . . . . . . . price, the leader running to the price on the last line of the name (`align-items: last baseline`; leader hidden where unsupported). Category headings sit between **double rules** (2 px + 1 px, 3 px apart).

| | |
|---|---|
| Fonts | **Fraunces** 600 (h1, h2, specials title; opsz default) + **Instrument Sans** 400 (body, descriptions), 600 (dish names, prices, chips). Files: `fraunces` latin-600, `instrument-sans` latin-400, latin-600. About 55 KB. |
| Scale | h1 `clamp(2rem, 8vw, 2.75rem)`/1.05; h2 1.5rem (small caps effect: `font-variant-caps: all-small-caps; letter-spacing .06em`, size 1.65rem); dish name 1.1875rem/1.3; description 1rem/1.5; price 1.125rem; meta .875rem |
| Light | bg `#f6f0e4`, surface `#fbf8f1`, ink `#211a17`, ink-2 `#5c4f47`, line `#d9cdb8`, line-strong `#8f8170` |
| Dark | bg `#17120f`, surface `#211a16`, ink `#f1e8d8`, ink-2 `#b8aa98`, line `#3a2f27`, line-strong `#7a6b5c` |
| Default brand / accent | `#7a2e2a` burgundy / `#b8893a` brass |
| Brand use | h1 and price colour `--brand-text`; double rules and active chip `--brand`; accent only on the specials eyebrow and a 1-px brass rule under the header |
| Density | `--density: 1` |
| Row | flat on `--bg`; 1 px dotted `--line` between rows; leader dotted `--ink-2` at 40% (decorative, not text) |
| Category heading | centred at mobile, left with sidebar at desktop, double rule above and below, optional description in Instrument Sans 16 px `--ink-2` |
| Chips | rectangular, radius 2 px, 1 px `--line-strong`, active = filled `--brand` with `--on-brand` |
| Specials | a "ticket": `--surface` panel, 1 px `--ink` border, corner notches (radial-gradient cut-outs), dotted top rule, eyebrow "PLAT DU JOUR" in accent |
| Photos | 88 px square, radius 2 px, 1 px `--line-strong` border and 3 px `--surface` mat (a mounted print) |
| Motion | chip active underline slides 150 ms |

### 3.2 `trattoria`: "Osteria table"

*Mood/references*: checked tablecloths, hand-painted pizzeria signs, olive oil bottles; loud, warm, generous, family-run. Rounded, heavy, appetising.
*Strong idea*: **gingham band + big price stamps**. The header sits on a red-and-cream gingham strip (pure CSS: two crossing `repeating-linear-gradient`s at 12% alpha in `--brand`), dishes are soft cards, and prices are bold in `--brand-text`.

| | |
|---|---|
| Fonts | **Young Serif** 400 (h1, h2, specials title) + **Figtree** 400 (body), 600 (names, chips), 700 (prices). Files: `young-serif` latin-400, `figtree` latin-400/600/700. About 60 KB. |
| Scale | h1 `clamp(2.25rem, 10vw, 3.25rem)`/1; h2 1.75rem/1.1; dish name 1.1875rem/1.25 (600); description 1rem; price 1.1875rem (700); meta .875rem |
| Light | bg `#fff9ef`, surface `#ffffff`, ink `#2a1b14`, ink-2 `#66524a`, line `#ecdcc4`, line-strong `#9a8572` |
| Dark | bg `#1c1310`, surface `#281b16`, ink `#fbeedd`, ink-2 `#c4ae9c`, line `#43312a`, line-strong `#85705f` |
| Default brand / accent | `#b8412a` terracotta / `#3d6b3a` basil green |
| Brand use | gingham band, price colour, active chip fill, h2 underline "brush stroke" (SVG data-URI wavy line 6 px); accent for the specials eyebrow and diet badges |
| Density | `--density: 1.1` |
| Row | each dish is a card: `--surface`, 1 px `--line`, radius 16 px, 4 px vertical gap, padding 16 px; no shadow (border only) |
| Category heading | left-aligned Young Serif 1.75rem, wavy brand underline (6 px high, 64 px wide) |
| Chips | pill (radius 999), `--surface` with 1.5 px `--line-strong`; active = `--brand` fill, 600 weight |
| Specials | large card, `--brand` background with `--on-brand` text (contrast enforced by theming), cream gingham corner, title in Young Serif 1.5rem, prices as cream pills |
| Photos | 88 px, radius 12 px, no border; in "all photos" mode the thumbnail is 104 px and card padding shrinks |
| Motion | card press feedback: `transform: scale(.985)` 100 ms on tap for sheet rows |

### 3.3 `cafe`: "Pastry-case label"

*Mood/references*: contemporary café, bakery, tea room; Instagram-friendly, airy, friendly, modern Paris/Brooklyn labels on pastry cases.
*Strong idea*: **round and light**: pill chips, circular photos like coasters, prices as small "sticker" pills, generous white space, and the brand colour as a large soft tinted header panel.

| | |
|---|---|
| Fonts | **Bricolage Grotesque** 700 (h1, h2, specials title) + **Nunito Sans** 400 (body), 700 (names, prices, chips). Files: `bricolage-grotesque` latin-700, `nunito-sans` latin-400/700. About 50 KB. |
| Scale | h1 `clamp(2.25rem, 10vw, 3.5rem)`/1 with -0.02em tracking; h2 1.5rem/1.15; dish name 1.125rem/1.3; description 1rem; price 1rem (700) in pill; meta .875rem |
| Light | bg `#faf6f0`, surface `#ffffff`, ink `#1f2a27`, ink-2 `#55605c`, line `#e6dfd2`, line-strong `#7d8581` |
| Dark | bg `#14191a`, surface `#1d2425`, ink `#eef2ee`, ink-2 `#a9b5b0`, line `#2d3839`, line-strong `#6f7d79` |
| Default brand / accent | `#2f5d50` pine / `#e0a458` honey |
| Brand use | header panel is `--brand-soft` with a 40 px radius bottom edge; chips active = `--brand`; price pill = `--brand-soft` background with `--brand-text`; accent for specials eyebrow dot |
| Density | `--density: 1.05` |
| Row | flat on `--bg`, no rules, 20 px vertical rhythm; a 1 px `--line` only between categories |
| Category heading | Bricolage 1.5rem with a small filled circle (10 px, `--accent`) before it |
| Chips | pill, no border, `--surface` on `--bg`, active = `--brand` fill; slight 1 px `--line` bottom edge |
| Specials | rounded 28 px card, `--surface`, big Bricolage title, price pills; a 12-px accent semicircle peeking out of the top-right corner |
| Photos | circle, 88 px, no border (with `--line` ring 2 px); in "all photos" mode 104 px |
| Motion | chip active background cross-fade 150 ms |

### 3.4 `gastro`: "Tasting menu card"

*Mood/references*: fine dining, Michelin websites, letterpress stationery, gallery labels. Quiet, centred, lots of air. The most restrained theme.
*Strong idea*: **typographic silence**. No boxes, no rules except one hairline; centred column; dish names in an elegant serif, descriptions in small tracked sans; prices stay right-aligned (the 5-second test comes first) but are small, in a lighter weight, so hierarchy is whispered, not shouted.

| | |
|---|---|
| Fonts | **Cormorant Garamond** 500 and 500 italic (h1, h2, dish names, specials title) + **Jost** 400 (body, descriptions), 500 (chips, prices, labels). Files: `cormorant-garamond` latin-500-normal, latin-500-italic, `jost` latin-400/500. About 65 KB. Cormorant has a small x-height, so all its sizes are +12% versus the other themes. |
| Scale | h1 `clamp(2.25rem, 9vw, 3.25rem)`/1.05 letter-spacing .02em; h2 italic 2rem/1.1 centred; dish name 1.375rem/1.25 (Cormorant 500); description 1rem/1.55 Jost 400 `--ink-2`; price 1rem Jost 500; meta .875rem, eyebrows 13 px uppercase tracking .14em |
| Light | bg `#fbfaf7`, surface `#fbfaf7` (flat), ink `#14130f`, ink-2 `#5a574f`, line `#e2ded4`, line-strong `#8e8a80` |
| Dark | bg `#0d0d0c`, surface `#141413`, ink `#ece8df`, ink-2 `#a9a59b`, line `#2a2925`, line-strong `#77746b` |
| Default brand / accent | `#6b5a3a` bronze / none (accent falls back to brand) |
| Brand use | almost invisible by design: 1 px rule under h1 (`--brand-ui`), price digits `--ink` not brand, active chip = 1 px underline `--brand-ui` + `--ink` text, focus ring. Specials eyebrow in `--brand-text`. |
| Density | `--density: 1.5` (rows 20 to 24 px padding) |
| Row | no dividers, no cards; whitespace only; descriptions max-width 34rem |
| Category heading | centred italic Cormorant with a 24 px hairline centred above it and 32 px hairline below |
| Chips | text-only, no container, uppercase 13 px tracking .12em, 44 px high, active = 1 px underline |
| Specials | centred, no box, "· Aujourd'hui ·" eyebrow, title italic 1.75rem, one hairline above and below |
| Photos | 96x120 portrait (4:5), no radius, no border; grayscale is never applied except for sold out |
| Motion | fades only (opacity 150 ms); sheet slides 200 ms |

### 3.5 `auberge`: "Farmhouse chalk and kraft"

*Mood/references*: country inn, farm shop, *auberge* with produce from the village; kraft paper labels, twine, enamel signs, wheat and copper. Warm, handmade, generous, trustworthy.
*Strong idea*: **kraft paper with stitched dividers**. Background is a warm kraft tone, cards are lighter paper with *dashed stitching* borders, category headings carry a small hand-drawn sprig ornament (inline SVG data-URI), and photos are slightly tilted polaroid-style prints.

| | |
|---|---|
| Fonts | **Alegreya** 700 (h1, h2, dish names, specials title) + **Alegreya Sans** 400 (body), 700 (prices, chips). Files: `alegreya` latin-700, `alegreya-sans` latin-400/700. About 72 KB. |
| Scale | h1 `clamp(2.25rem, 9.5vw, 3.25rem)`/1.05; h2 1.75rem/1.1; dish name 1.3125rem/1.25 (Alegreya 700); description 1.0625rem/1.5 (Alegreya Sans, larger since it runs small); price 1.125rem (700); meta .9375rem |
| Light | bg `#efe6d2`, surface `#f8f1e1`, ink `#2b2117`, ink-2 `#5e4f3d`, line `#d3c4a3`, line-strong `#8a7859` |
| Dark | bg `#1b1610`, surface `#251e15`, ink `#efe4cd`, ink-2 `#b9a98c`, line `#3d3324`, line-strong `#7d6d52` |
| Default brand / accent | `#5b6b3a` moss / `#b5651d` copper |
| Brand use | h1, price and ornament in `--brand-text`; active chip `--brand`; copper accent on the specials "enamel sign" and diet badges |
| Density | `--density: 1.05` |
| Row | `--surface` paper strip, radius 6 px, 1.5 px dashed `--line-strong` inner stitch (`outline-offset: -5px` on a 6 px-radius box), 8 px gap |
| Category heading | Alegreya 1.75rem, sprig ornament (28 px) above, thin `--line-strong` hairline right of the text (flex `::after`) |
| Chips | rounded rectangles radius 8 px, `--surface`, dashed border `--line-strong`; active = solid `--brand` |
| Specials | "enamel sign": `--accent` border 3 px, inner 1 px cream ring, title Alegreya 1.5rem, eyebrow in caps; sits slightly rotated -0.6deg on desktop only |
| Photos | polaroid: 3 px white-ish mat (`--surface`), 1 px `--line`, rotate(-1.2deg), alternate rows +1.2deg (static, so allowed under reduced motion) |
| Motion | chip and card colour transitions 120 ms |

**Differentiation check**: bistro = paper, rules, leaders, sharp corners; trattoria = saturated, rounded cards, gingham; café = airy, pills, circles; gastro = borderless, centred, italic serif, huge whitespace; auberge = kraft, stitching, tilted prints, ornament. Different type voice (didone-ish soft serif / chunky serif / geometric grotesque / high-contrast garalde / humanist serif) and different row anatomy in each, so a screenshot of any two rows is instantly attributable.

---

## 4. Colour safety (`public/theming.py`)

`build_theme_vars(theme, brand_color, accent_color) -> {"light": {...}, "dark": {...}}` emits **all** colour variables for both modes (neutral bases from the tables above included), so all palette logic and all tests live in one Python module. Structural variables (fonts, radii, density) stay in the theme CSS. Pure Python, no dependencies, deterministic.

### 4.1 Colour maths
sRGB hex <-> linear sRGB <-> OKLab <-> OKLCH (Bjorn Ottosson's matrices), WCAG 2.x relative luminance for the contrast ratio (the legal metric), gamut clipping by reducing chroma at fixed L and h (binary search, 12 iterations).

### 4.2 Algorithm

```
sanitize(hex, fallback):   accept #rgb/#rrggbb (case-insensitive, optional '#'); anything else -> theme default
tame(c, theme):            L,C,h = oklch(c)
                           if C < 0.025: neutral brand, keep C (black/grey brand is allowed; h irrelevant)
                           else C' = C if C <= 0.10 else 0.10 + (C-0.10)*0.45       # soft compression of neon
                                C' = min(C', THEME_CHROMA_CAP[theme])                # bistro .14 trattoria .17 cafe .15 gastro .08 auberge .12
                           L' = clamp(L, 0.28, 0.80)       # not near-white, not near-black as a "colour"
                           h  = h                          # hue is never changed: the owner's colour identity stays
```
Roles, derived from the tamed colour `t` (each fixed at hue `h`, gamut-mapped, then contrast-fixed):

| Variable | Definition | Guaranteed |
|---|---|---|
| `--brand` | fill colour: `t`, but L moved into `[0.35, 0.58]` (light) or `[0.55, 0.72]` (dark) | reference for the two below |
| `--on-brand` | whichever of `#ffffff` / `--ink-on-dark` (`#12100e`) has the higher contrast with `--brand` | contrast(`--on-brand`, `--brand`) >= 4.5; if best < 4.5, walk `--brand` L in 0.01 steps (darker in light mode for white text, lighter in dark mode for dark text) until it holds |
| `--brand-text` | brand as text/price/link on page: start at `--brand`, walk L away from the background (darker in light, lighter in dark) in 0.01 steps | >= 4.5 against `--bg` **and** `--surface` **and** `--brand-soft` |
| `--brand-ui` | borders, focus ring, active bar, icons: like `--brand-text` but target 3.0 | >= 3.0 against `--bg` and `--surface` |
| `--brand-soft` | tint: mix of `--brand` into `--surface` in OKLab, 9% (light) / 16% (dark) | `--ink` and `--ink-2` on it >= 4.5 (checked; mix reduced by 2% steps if not) |
| `--accent`, `--accent-text`, `--accent-ui`, `--on-accent`, `--accent-soft` | same pipeline from the accent colour; if no accent: theme default accent (gastro: brand). **If accent is within ΔE(OKLab) < 0.06 of brand or is neutral, use the theme default accent** so accent is always distinguishable | same guarantees |

The loops are bounded (max 70 steps, L walks to 0 or 1, where contrast with the base is at least 12:1), so termination and success are guaranteed.

**Neutrals** (`--bg --surface --ink --ink-2 --line --line-strong`) come from the theme tables (all pre-verified: ink >= 12.7:1, ink-2 >= 6.1:1 on bg and surface, line-strong >= 3.0:1). `theming.py` tints them toward the brand hue: `C = 0.006` for `bistro/trattoria/cafe/auberge` (0 for `gastro`), L preserved, so the page feels made *for* this restaurant, then re-checks the same thresholds (falls back to the untinted value if a check fails).

**Garish colours**: pure `#ff0000`, `#00ff00`, `#ffff00`, `#ff00ff`, `#0000ff` are chroma-compressed and capped (e.g. `#00ff00` becomes a leaf green, C about 0.13 at bistro-level cap), yellows and lime are forced to L <= 0.58 as fills and dark as text, so they read as mustard/olive rather than highlighter.
White/very light brands (L > 0.80) become the tinted-neutral "champagne" `L=0.80`; black/very dark brands become the dark neutral (used as-is in fills, lifted to L >= 0.55 in dark mode).

### 4.3 Emitted custom properties (both modes have the same key set)

`--bg --surface --ink --ink-2 --line --line-strong --brand --on-brand --brand-text --brand-ui --brand-soft --accent --on-accent --accent-text --accent-ui --accent-soft --scrim --focus`
(`--focus` = the `--brand-ui` or `--ink`, whichever has higher contrast vs `--bg`; `--scrim` = `rgb(0 0 0 / .5)` in light, `rgb(0 0 0 / .65)` in dark.)

Structural vars (theme CSS): `--font-display --font-body --radius --radius-sm --density --gutter --measure --bar-h`.

Rendering (template): light variables in `:root`; `@media (prefers-color-scheme: dark) { :root[data-mode="auto"] { dark } }` and `:root[data-mode="dark"] { dark }`; `:root { color-scheme: light dark }` for auto, `light`/`dark` when forced. Two `<meta name="theme-color" content="{bg}" media="(prefers-color-scheme: ...)">`.

### 4.4 Tests (`public/tests/test_theming.py`)
Property test over: the 2 seed brand colours, `#000000 #ffffff #ffff00 #00ff00 #ff00ff #0000ff #ff0000 #808080 #fafafa #050505`, invalid strings (`""`, `"red"`, `"#12"`, `None`), and 300 seeded-random colours, for 5 themes x 2 modes x accent (None / random / equal to brand): assert every threshold in the table above, same key set in both modes, valid `#rrggbb` output, determinism.

---

## 5. Photos, density and content edge cases

`photo_mode` is computed in a template tag from the context (no contract change): `none` (0 photos), `some` (< 60% of dishes), `all` (>= 60%). Set as `data-photos` on `<main>`.

| Case | Layout |
|---|---|
| **No photos** (most restaurants) | Typography-first. Rows are text only, full width, so long descriptions run at a comfortable measure (<= 34rem). The theme's character comes from headings, rules, chips, specials and header; nothing looks "missing". The bottom sheet is only for allergens (no photo area). This is the primary design target and gets the most screenshot attention. |
| **Some photos** | Only rows with a photo get the right-hand thumbnail (88 px, frame per theme); their text column is narrower by 104 px (name, description and price move together, so a row's own price/name relationship holds). Rows without photos keep full width. No placeholder boxes. Optional: within one category, if fewer than a third of rows have photos, photo rows are flagged `data-photo="1"` for a slightly taller min-height (104 px) so rhythm doesn't jitter. |
| **All photos** (`data-photos="all"`) | Photos become part of the rhythm: thumbnails grow to 104 px (112 px at >= 720 px), row min-height 120 px, and at >= 720 px the dish list becomes a **two-column grid** (columns 20rem). At mobile it is still one column of rows, never a giant photo card, so an 80-item menu stays scannable (about 4.5 rows per screen, not 1.5). |
| **80-item menu** | Categories 8 to 10 with the chip bar as the index; rows about 76 px (no photos) so a category of 10 is about 760 px; `content-visibility: auto; contain-intrinsic-size: auto 800px` on each category section to keep rendering cheap; search in the filter sheet; sidebar nav at desktop. |
| **5-item menu** | One or two categories: chip bar hidden if a single category; header and rows get extra breathing room (`data-count="few"` when `item_count <= 8` raises `--density` by 0.25 and dish name +1 px); the page must not look empty: footer and specials get more presence, min page height fills the viewport with the footer at the bottom (`min-height: 100dvh` flex column). |
| **Long name** ("Confit de canard du Périgord, pommes sarladaises à la graisse de canard et salade verte à l'huile de noix") | Wraps to 3 to 4 lines at 375 px inside the left column; price top-aligned on line 1; `text-wrap: pretty`; no truncation ever. Leader (bistro) attaches to the last line only when supported, hidden otherwise. |
| **No description** | Row collapses; name to price only. Row padding stays constant, so short rows do not feel cramped. |
| **Two-size prices** | Right-column stack (section 1.3). Column width is `max-content`, capped at 45% of the row; if the labels are long ("Bouteille") the label sits above the amount rather than beside it below 360 px. |
| **3+ prices** ("Petite / Moyenne / Grande") | Same stack; specials use the same component. |
| **Missing English translation** | `tr()` already falls back to French; theme does not care. No `lang` switching on fallback text (out of scope). |
| **No category description** | No gap; with description, shown under h2 in 16 px `--ink-2`, max 34rem. |

---

## 6. Icons (`static/public/icons.svg`)

One SVG sprite of 17 `<symbol>`s, `viewBox="0 0 24 24"`. Public pages inline **only the symbols used on the page** (template tag extracts them from the sprite, cached) to avoid an extra request and to avoid a flash of missing icons; the editor references the external file with `<use href="/static/public/icons.svg#al-gluten">`.

- **Style**: 24 px grid, live area 20x20 (2 px padding), 1.5 px stroke, `stroke="currentColor"`, `fill="none"`, round caps and joins, at most one small solid dot per icon (`fill="currentColor"`); no gradients, no text in glyphs; corner radii multiples of 1; every symbol under 450 bytes (sprite about 7 KB). Icons are drawn as simple, distinct silhouettes, tested at 16 px and 20 px in a contact sheet (`docs/screenshots/icons.png`).
- **Allergens** (`#al-<code>`): `gluten` wheat ear; `crustaceans` curled shrimp; `eggs` egg with highlight; `fish` fish profile; `peanuts` two-lobed shell with dots; `soy` open pod with three beans; `milk` bottle; `nuts` hazelnut with cap; `celery` stalk with leaves; `mustard` jar with lid and label; `sesame` cluster of three seeds; `sulphites` wine glass; `lupin` flower spike; `molluscs` mussel shell.
- **Diets** (`#diet-<code>`): drawn inside a 22 px circle outline so they read as badges: `vegetarian` leaf with midrib, `vegan` seedling (two leaves), `gluten_free` wheat ear with diagonal slash (clearly different from `gluten` at 16 px).
- **Extra UI icons** (same style, `#ui-*`): `search`, `sliders` (filter), `close`, `pin`, `phone`, `clock`, `check`.
- **Text is never optional**: every icon appears with a text label in the legend and the sheet, and a visually-hidden label in rows; icons carry `aria-hidden="true"`. Rows never rely on colour alone to distinguish allergen from diet (shape: bare glyph vs circle badge).

---

## 7. Performance and accessibility budget

| Item | Target |
|---|---|
| HTML (80 dishes, 5 photos) | proposed <= 9 KB gzip; **as built ~15 KB gzip / 110 KB raw** for the 81-dish seed (per-row `data-*`, icon `<use>`s and hidden labels); 5-dish page ~5 KB gzip |
| Inline CSS (base + theme, minified) | proposed <= 13 KB raw / 4.5 KB gzip; **as built ~19.5 KB raw / ~5.1 KB gzip** (PLAN ceiling 20 KB gz). Enforced by `test_templates.py` (<= 22 KB raw, <= 5.5 KB gz) |
| Fonts | 3 to 4 WOFF2 latin files per theme, <= 75 KB total, <= 40 KB render-blocking (2 preloaded: display face + body regular). `latin-ext` only through `unicode-range` |
| JS | one deferred file `menu.js`, **readable source served as is (no build step): ~8.2 KB raw / ~3.0 KB gz**, no dependencies. Features: scroll-spy, sheet + history + swipe, search/filter. Everything else is CSS. Enforced by `test_templates.py` (<= 10 KB raw, <= 3.5 KB gz) |
| Images | thumbnails `srcset` 480/960 WebP via `PhotoView`, `sizes="88px"` (`112px` >= 720 px), `loading="lazy" decoding="async"`, explicit `width`/`height`, first 4 thumbs eager. Sheet image loaded on open. Fixed thumb boxes (no CLS) |
| Requests on first load | HTML + 2 fonts (+ `menu.js`) + thumbs; nothing third-party; no analytics |
| Lighthouse (mobile, throttled) | Performance >= 95, Accessibility >= 95 (aim 100), Best Practices >= 95, CLS < 0.02, LCP < 1.8 s |

**Font loading**: `<link rel="preload" as="font" type="font/woff2" crossorigin>` for the display face and body regular; `font-display: swap`;
each family gets a metrics-matched local fallback `@font-face` (`size-adjust`, `ascent-override`, `descent-override` on Georgia/Arial) so the swap is almost invisible (CLS ~ 0). Hashed filenames from WhiteNoise, `Cache-Control: public, max-age=31536000, immutable`.
The `latin` subset is used as shipped by Fontsource (no further subsetting; adding a custom pyftsubset step would save only a few KB and would add a build step).

**A11y**: `lang` on `<html>` follows the current language (and on language-switch links); skip link; landmarks as in 1.2; correct heading order; every interactive element >= 44x44 px with >= 8 px spacing (chips, lang switch, filter button, sheet close, footer links 48 px, checkbox rows 48 px);
visible focus for keyboard: `:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px }` (>= 3:1); `aria-current` on the active chip; `<dialog>` semantics with labelled headings (`aria-labelledby`); sold-out and allergen info exposed as text; no information by colour alone; `prefers-reduced-motion`; `forced-colors` mode keeps borders (`border-color: CanvasText` fallbacks); zoom to 200% and OS text scaling do not clip or overlap; **no horizontal scroll at 320 or 375 px** (checked in the screenshot script: `document.documentElement.scrollWidth <= innerWidth`).

**Light/dark**: restaurant `color_mode` `auto | light | dark`. `auto` follows `prefers-color-scheme` (dark variables in a media query), `light`/`dark` force via `data-mode`. Dark palettes are designed (not inverted): backgrounds are warm near-black, text is off-white (never `#fff` on `#000`), photos keep full colour, brand roles are lifted to meet the same contrast targets. No in-page toggle (the QR visitor's phone setting is the truth; a toggle would be UI noise).

**Other**: print stylesheet (`@media print`: black on white, no chips/sheet, legend kept) is a cheap extra; `<meta name="robots" content="noindex">` on `?preview=1` (decision below); OG tags (`og:title` name, `og:description` tagline, `og:image` first photo or logo) so link sharing looks good.

---

## 8. Screenshot and critique protocol

`scripts/screenshots.py` (Playwright for Python, dev server on port 8003, admin login, seed data via `seed_demo`):
1. **Matrix**: 5 themes x {375x812 @2x, 1280x900 @1x} x {light, dark} x {photos on, `photos=0`}, using `/m/<slug>/?preview=1&theme=<t>&mode=<m>&photos=0`. Full-page plus first-viewport crops, saved as `docs/screenshots/<theme>-<mode>-<w>[-nophotos].png`; contact sheets per theme (`docs/screenshots/contact-<theme>.png`).
2. **Interaction shots**: dish sheet open (with photo, without photo), filter sheet with 2 filters active, specials block, chip bar mid-scroll (active chip), footer, long-name row, two-price row, sold-out row.
3. **Automated gates during the run**: no horizontal overflow at 320/375/1280; every tap target >= 44 px (bounding boxes of `a, button, input, label`); console has no errors; a scripted 5-second test (locate "Tarte tatin" via chips then read the price); axe-core (injected from `npx`/local file, no runtime dependency) with zero serious violations; Lighthouse via `npx lighthouse` on the demo menu at mobile settings, results logged in `docs/screenshots/lighthouse.txt`.
4. **Critique loop (>= 2 iterations, more if needed)**: after each render I open every screenshot and write a written critique against a fixed checklist:
   hierarchy (name > price > description > tags), price alignment, rhythm and density (dishes per screen), distinctiveness vs the other four themes, colour harmony with the brand, dark-mode contrast (contrast sampled from pixels for suspicious spots), header/first screen, specials block, chips (active state legible), photo frames, long-name and two-price rows, 5-item and 80-item behaviour, empty states.
   Then fix, re-shoot, re-critique. Iteration notes and before/after evidence are kept in `docs/screenshots/CRITIQUE.md` (a working log, not a deliverable report).
5. **Cross-checks**: icon contact sheet at 16/20/24 px; a colour torture set (`#ffff00`, `#00ff00`, `#ff00ff`, `#111111`, `#f5f5f5` as brand) rendered for all themes and checked visually and by `test_theming.py`; Œ/œ/€/Ÿ rendering test row; no-JS render (Playwright with JS disabled) confirming a fully usable page.

---

## 9. Decisions and assumptions (all resolved, see section 10)

1. **Allergen data completeness.** A filter can only be as trustworthy as the data. Proposal: no new field; the sheet says "indication fournie par le restaurant" and dishes with *no* allergen tags are never hidden by an allergen filter. (Alternative: a restaurant-level "allergens fully declared" flag that enables the allergen filter.)
2. **Inline used-symbol sprite** on public pages (external `icons.svg` remains for the editor). Needs nothing from you.
3. **Static files**: I assume `STATICFILES_DIRS = [BASE_DIR / "static"]` and WhiteNoise hashed storage in production, and that the `inline_css` tag may read CSS through `finders`/`staticfiles_storage`. Please confirm settings.
4. **Photo variants**: `PhotoView.srcset` should include 480w and 960w; the sheet uses the 960w. No contract change if the image pipeline provides `srcset`.
5. **Hours format**: I split lines on the first ` : ` into label/value (matches the seed data); other lines render full-width. The editor's hint text for `hours` should say "one line per row, `Label : times`".
6. **Search inside the filter sheet** (>= 20 dishes) is my addition to the brief; it costs about 0.4 KB gz and materially helps the 5-second test on big menus. Confirm you want it.
7. **Robots/preview**: `noindex` on preview only; public menu indexable. Tell me if menus should be `noindex` by default.
8. **Logo vs name**: both are always shown (logo above the name). Confirm this rather than "logo replaces the name" (which silently loses the `h1` and looks wrong for icon-only logos).
9. **Fonts**: ten OFL families across five themes (about 60 to 70 KB each theme) will be vendored in `static/public/fonts/`; licence files are included. Fontsource file availability was checked (HTTP 200 for the latin files listed).

---

## 10. Review amendments and as-built notes

**Answers to section 9.** (1) Allergen trust as proposed: no new field, untagged dishes are never hidden by an allergen filter,
safety wording shown in the filter sheet. (2) Inline used-symbol sprite approved (external `icons.svg` stays for the editor).
(3) `STATICFILES_DIRS=[BASE_DIR/"static"]`, WhiteNoise hashed storage when DEBUG is off; `inline_css` reads the *source* CSS through
`finders.find()`; fonts and `menu.js` use `{% static %}` (hashed). (4) `PhotoView.srcset` may be empty: handled (thumbnail falls back to `src`).
(5) Hours `Label : times` split approved. (6) Search in the filter sheet at >= 20 dishes: yes. (7) Public menus stay indexable; `noindex` only on
`?preview=1`. (8) Logo and name both always shown. (9) Fonts approved, within budget.

**Amendments applied**
- **a. Every dish row with detail is an accessible control.** The dish *name* is `<h3><a class="dish-link" href="#dish-N">` with a stretched
  `::after` covering the whole row (accessible name = dish name; heading semantics kept). Without JS it anchors to the row; with JS it opens the
  sheet (`aria-haspopup="dialog"`). Rows with only a name and a price (no description, photo, allergen or diet) render plain text and no link; they
  have no visible affordance, and linked rows show none either (press/hover tint only), so the menu stays visually consistent.
- **b. Row descriptions clamp to 2 lines** (`line-clamp`); the sheet shows the full text. A `<noscript><style>` un-clamps the text without JS.
  Any row with a description is a link, so every clamped description opens the sheet.
- **c. `content-visibility: auto` was tried and then removed** (second review): it left unpainted bands in full-page screenshots for little gain at <= 80 dishes.
- **d. Bistro leaders only on single-price rows** (the `.lead` element is only rendered when there is exactly one price).
- **e. Lighthouse measured on a production-like server** (`docs/screenshots/lighthouse.txt`): performance 97-100, accessibility 100, best practices 100, SEO 100.
- **f. Preview:** no visible chrome; `noindex, nofollow` meta only.
- **g/h.** Screenshot matrix in `docs/screenshots/` (webp, 375 px viewport + mid-menu crop, 1280 px full page; light/dark; photos/no photos; native seed restaurant per theme), interaction shots, contact sheets, `icons.png`, `CRITIQUE.md`.

**As built, differences from the proposal**
- Fonts are vendored flat as `static/public/fonts/<family>-<subset>-<weight>-<style>.woff2` (latin + latin-ext, `unicode-range`), licences in `fonts/LICENSES/`.
  `fonttools` check: every latin file has Œ œ € NBSP; Fraunces and Nunito Sans have no `tnum`, so prices are never set in them (bistro prices use
  Instrument Sans, cafe prices use Bricolage Grotesque, which has `tnum`). Metric-matched fallbacks were measured with fonttools.
- **Photo rows on mobile** stack the price *under* the name (a 300 px row cannot hold name + price + thumbnail); multi-size prices become a two-column grid
  (label | amount, amounts right-aligned). At >= 720 px the price stays beside the name. All-photos two-column grids exist only at 720-1023 px and >= 1200 px (page widens to 72 rem).
- Multi-price *specials* render as a full-width price block under the title in every theme (long labels such as "Entrée + plat + dessert").
- Desktop with no chip bar (single category, < 20 dishes) is a centred single column; the filter dialog exists only when the chip bar does.
- Theming: tinting of neutrals keeps their lightness and shifts only hue/chroma (2x`tint` of the brand's a/b). White or near-white brands become neutral greys
  (roles derive from L clamped to the role range), they do not become "champagne". A dark-mode logo plate (`--logo-bg`, `--logo-pad`) is emitted
  because the demo logos are transparent PNGs drawn for light backgrounds.
- CSP: the page uses one inline `<style>` and no inline script (external `menu.js`), compatible with `style-src 'self' 'unsafe-inline'`.
- Icons: 14 allergens, 3 diets (circle badge) and 7 UI icons; sprite 7.4 KB; the shrimp glyph is the weakest at 16 px.
- `public/tests/test_templates.py` (in addition to `test_theming.py`) covers rendering for 5 themes x 3 modes, budgets, sprite and font coverage.
- `scripts/screenshots.py` also runs the gates: overflow at 320/375/1280, tap targets >= 44 px, console errors, axe-core (WCAG 2 A/AA + best practices) with `--gates --axe <axe.min.js>`.

---

## 11. Second review round (first screen, plain JS, photo gutter)

- **Chip bar directly after the header; specials are the first section of `<main>`** (`#today`) with their own first chip "Aujourd'hui" / "Today"
  (accent-styled, `.today-chip`). Scroll-spy treats `#today` like a category; the filter never hides it.
- **Specials use the dish-row anatomy on every viewport:** small kind eyebrow, title left (<= 1.1875rem, 1.3125rem in gastro's italic serif), price(s) right,
  description clamped to 2 lines with JS and shown in full in the sheet (title is a `dish-link`; the sheet is shared with dishes). Multi-price specials
  ("Formule") put label | amount rows full width under the title. No centred stacks; each theme keeps its frame (ticket, green card, enamel sign, hairlines, pastel card), only tighter.
- **Tighter header on mobile:** logo <= 56 px, smaller gaps, tagline 1rem or less, smaller h1 clamps.
- **Gate (in `scripts/screenshots.py --gates`):** at 375x812 (light) the chip bar and the first special (or first dish) are fully visible, for all five seed menus
  (chip bar bottom at 256-291 px, first special bottom at 435-520 px; the 5-dish cafe has no bar and shows its first dish).
- **`content-visibility` removed; `menu.js` served as readable source** (`menu.src.js` deleted, no build step).
- **Per-category photo gutter at >= 720 px:** in a category where at least one dish has a photo, dishes without a photo reserve the thumbnail width,
  so all prices of that category share one right edge (`.cat:has(.dish-thumb) .dish:not(:has(.dish-thumb))`). Not applied in all-photos mode (grid rows). Mobile unchanged.
