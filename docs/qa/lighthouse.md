# Lighthouse (mobile) on the Docker/Caddy stack

Stack: `docker compose -p qrmenu-qa up -d --build`, `SEED_DEMO=1`, no Anthropic key, http://localhost:8080
(Caddy, gzip/zstd on, Django DEBUG=0 with WhiteNoise). Lighthouse 13 via `npx lighthouse <url>`,
default mobile emulation and default simulated "Slow 4G" throttling (1.6 Mbit/s, 150 ms RTT, 4x CPU),
headless Chrome, one run per menu (bistrot re-run 3 more times, see below).
Trimmed results: `docs/qa/lighthouse/<slug>.json` (scores, metrics, failing audits), and the full
HTML report of the one menu under the gate: `docs/qa/lighthouse/bistrot-des-halles.report.html.gz`.

## Final results (after fixes, 2026-09-02)

Same stack (`docker compose -p qrmenu up -d --build`, seeded, no Anthropic key), Lighthouse 12 mobile
defaults, **3 runs per menu** (min-max shown):

| Menu | Theme | Perf | A11y | Best pr. | SEO | FCP | LCP | CLS | Weight | Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| bistrot-des-halles | bistro | 98-99 | 100 | 100 | 100 | 0.8-0.9 s | 2.3 s | 0 | 377 KiB | pass |
| chez-gino | trattoria | 99 | 100 | 100 | 100 | 1.1-1.2 s | 2.0-2.1 s | 0 | 187 KiB | pass |
| petit-kiosque | cafe | 100 | 100 | 100 | 100 | 0.6-0.7 s | 1.5 s | 0 | 99 KiB | pass |
| maison-vialle | gastro | 99 | 100 | 100 | 100 | 1.1-1.2 s | 2.0 s | 0.001 | 251 KiB | pass |
| auberge-du-puy-blanc | auberge | 99-100 | 100 | 100 | 100 | 1.1-1.2 s | 1.8 s | 0 | 172 KiB | pass |

Fixes applied after the first audit (below):
- The header logo is now a small WebP variant fitted to 2x the 180x56 slot (`menus.images.logo_view`);
  the bistro logo went from a 75 KB PNG at high priority to 8.7 KB. That PNG was competing with the fonts
  for bandwidth under simulated Slow 4G, which delayed the LCP dish name.
- The dish-name face is preloaded in the themes where it is not one of the two existing preloads
  (bistro, trattoria, cafe).
- `<link rel="icon">` on every page (no more `/favicon.ico` 404 console error -> Best Practices 100).

## First audit (before fixes)

| Menu | Theme | Perf | A11y | Best pr. | SEO | FCP | LCP | TBT | CLS | Weight | Gate (Perf and A11y >= 95) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bistrot-des-halles | bistro | **94** | 100 | 96 | 100 | 0.9 s | 3.0 s | 0 ms | 0 | 442 KiB | **FAIL (Perf)** |
| chez-gino | trattoria | 98 | 100 | 96 | 100 | 1.2 s | 2.3 s | 40 ms | 0 | 231 KiB | pass |
| petit-kiosque | cafe | 100 | 100 | 96 | 100 | 0.8 s | 1.5 s | 0 ms | 0 | 100 KiB | pass |
| maison-vialle | gastro | 99 | 100 | 96 | 100 | 1.2 s | 2.1 s | 0 ms | 0 | 269 KiB | pass |
| auberge-du-puy-blanc | auberge | 99 | 100 | 96 | 100 | 1.1 s | 1.9 s | 0 ms | 0 | 199 KiB | pass |

Bistrot re-runs: 95 / 94 / 94 (LCP 3.0 s each time), so it sits on the edge of the gate and mostly misses it.

## Findings
1. **bistrot-des-halles Performance 94 (LCP 3.0 s simulated).** Lighthouse's LCP element is a dish name
   (`li#dish-1 h3.dish-name`, Instrument Sans 600). The bistro theme preloads `fraunces-latin-600` and
   `instrument-sans-latin-400` only, so `instrument-sans-latin-600-normal` is discovered late
   (network dependency chain HTML -> font, requested at 124 ms vs 64 ms for the preloaded ones) and the
   text repaints after the swap. Suggested fix (not verified, needs a rebuild): add
   `instrument-sans-latin-600-normal` to the bistro `preload` list in `public/theming.py:62`
   (check the other themes' `preload` lists for the same gap; they score 98-100 today).
   Measured with a real (CDP "Fast 4G", 4x CPU) cold load the same page paints FCP = LCP = 356 ms, so this
   is a simulation artefact, but the gate is defined on Lighthouse.
2. **`/favicon.ico` returns 404** on every menu: one console error ("Failed to load resource ... 404"),
   which is the only reason Best Practices is 96 instead of 100 everywhere. Suggested fix: a
   `<link rel="icon" href="data:,">` (or a real icon) in `templates/public/menu.html` head, or serve a
   favicon route.
