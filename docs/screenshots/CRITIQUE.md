# Critique log (working notes)

Method: render with `scripts/screenshots.py`, open every screenshot, write the critique against the checklist in
DESIGN.md section 8 (hierarchy, price alignment, rhythm/density, distinctiveness, colour harmony, dark contrast,
first screen, specials, chips, photo frames, long-name/two-price rows, 5-item and 80-item behaviour), fix, re-shoot.
Intermediate renders were not kept; only the final matrix is committed.

## Iteration 1 (bistro demo content in all five themes, 375 px, no photos)
Seen: five clearly different themes; bistro leader dots and double rules read well.
Problems and fixes:
- Specials block ate the first screen in trattoria and cafe: multi-price specials put long labels in a narrow
  right column ("Entrée + plat + dessert" broke over four lines). Fix: multi-price specials now use a full-width
  price block under the title (`.sp-row .dish-prices:has(.pr+.pr)`), trattoria specials padding and title tightened.
- Gastro: too much air above the category headings (72 px + density 1.5). Fix: 48 px.
- Filter button collided with the fading chip row. Fix: gap before the button.

## Iteration 2 (with photos, dark mode, first behaviour checks)
Problems and fixes:
- Photo rows: the name column was squeezed to about 100 px because name, price and a 88 px thumbnail shared 300 px
  (trattoria title broke over five lines). Fix: on mobile a photo row stacks name, then price under it; two-size
  prices become a two-column grid (label | amount, amounts right-aligned).
- Chip jump overshoot: `scroll-margin-top` on sections was added to `scroll-padding-top` on the root, so headings
  landed 68 px too low. Fix: root padding only, and a negative margin to cancel most of the section's own top padding.
  Verified on 80 dishes: heading lands at the same offset for all chips, up and down, and on cold `#cat-N` loads.
- Filter sheet content flush against the edge (padding selector targeted the wrong element); sheet photo collapsed
  to 80 px because `width/height` attributes on the cloned image beat `aspect-ratio`. Both fixed.
- Trattoria dark: specials text used `opacity: .92` on the brand fill and failed axe colour-contrast. Removed.

## Iteration 3 (real seed, 1280 px, layouts with and without sidebar, gates)
Problems and fixes:
- Bistro: header rule + first category's double rule stacked when there is no chip bar (5-dish menus): first
  category loses its top rule in that case.
- Cafe: dead space under the header panel when there are no specials; single-category desktop layout left an empty
  sidebar column. Fix: panel padding only when specials follow; no-bar layouts are a centred single column.
- Gastro all-photo desktop: two-column grid at 690 px made names wrap five lines. Fix: two columns only from
  1200 px where the page widens to 72 rem, and price-under-name in grid rows.
- Sidebar chips 40 px tall (target 44). Fixed; gates now run at 320/375/1280 for all five themes x light/dark.
- Console error when the page has no chip bar but a filter dialog (null button). Dialog is now rendered only with the bar.

## Iteration 4 (production-like server, Lighthouse)
- SEO 91: `hreflang` links were relative. Now absolute (`public_url` + `?lang=`), self-reference included: SEO 100.
- Logo `fetchpriority=high`. Performance 97-100, Accessibility 100 on all five seed menus.

## Open observations (not fixed)
- In "some photos" mode on desktop the price of photo rows sits left of its thumbnail, so prices of rows with and
  without photos do not share one right edge. Alternative (reserve the thumbnail gutter on every row of a category
  that has photos) trades whitespace for alignment; left to the restaurant owner to judge with real menus.
- Shrimp icon is the weakest glyph at 16 px.
