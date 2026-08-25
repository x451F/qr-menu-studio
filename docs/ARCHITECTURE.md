# QR Menu Studio — Architecture

Single-admin tool: turn a restaurant's paper menu into a fast, permanent-URL web menu plus
printed QR material in about ten minutes. This document records the stack, the data model and
the contracts between the apps.

## 1. Product decisions

| Topic | Decision |
|---|---|
| Publishing | Autosave = live. Once a restaurant is published, every saved edit is visible to diners immediately. Unpublished restaurants are only visible to the logged-in admin (preview). |
| Admin UI language | **English** (code, admin labels). Public menu UI strings are FR/EN. |
| Menu content languages | **FR (default) + EN**. Data model stores per-field translations as JSON `{"fr": "...", "en": "..."}` so adding a language later is small. |
| Domain | Configurable via `PUBLIC_BASE_URL` / `SITE_ADDRESS` env vars (placeholder until provided). |

## 2. Stack (and why)

| Layer | Choice | Why |
|---|---|---|
| Web framework | **Django 5.2 LTS** | Python; batteries included (ORM, migrations, auth + password hashing, sessions, CSRF, forms, templates, static files). Fewer libraries to glue than FastAPI+SQLAlchemy+Alembic+auth. LTS supported until 2028. |
| DB | **SQLite** (WAL mode) in `/data` | Single user, tiny write volume, reads are cheap. Zero extra service; backup = one file (`sqlite3 .backup`). |
| Public pages | **Server-rendered Django templates**, inline critical CSS, ~5 KB vanilla JS, self-hosted WOFF2 fonts | Fastest first paint on 4G, no build step, no framework runtime. |
| Admin interactivity | **HTMX** (vendored) + **SortableJS** (vendored, touch drag & drop) + small vanilla JS | Server-rendered partials, autosave via `hx-trigger="change, keyup delay:600ms"`. No node toolchain. |
| Images | **Pillow** | EXIF rotate, resize, JPEG + WebP variants. |
| QR | **segno** | Pure Python, SVG + PNG, no system deps. |
| PDF | **WeasyPrint** | Print layouts written in HTML/CSS (same skills as the menu themes), embeds fonts, CMYK-ish safe output; needs pango (in Docker image; `brew install pango` on macOS). |
| AI | **anthropic** Python SDK, model from `ANTHROPIC_MODEL` (default `claude-opus-5-5`) | Vision extraction with structured JSON output; translation. Feature hidden when `ANTHROPIC_API_KEY` is absent. |
| App server | **gunicorn** (3 sync workers) + **WhiteNoise** for hashed static files | Standard, simple. |
| Reverse proxy | **Caddy** | Automatic HTTPS, gzip/zstd, serves `/media` straight from the volume. |
| Deploy | **Docker Compose**: `web` (Django+gunicorn) + `caddy`. One named volume `data` (`db.sqlite3` + `media/`). | Two containers, one volume, one `.env`. |
| Tests | **pytest + pytest-django** (unit), **Playwright for Python** (e2e + screenshots), Lighthouse via `npx` | All Python except Lighthouse. |

No Redis, no Celery, no node build, no Postgres. AI calls are synchronous (a menu photo takes
~20–60 s; the UI shows a progress state; gunicorn timeout is raised to 330 s; the AI client uses a 150 s timeout with 1 retry).

## 3. Folder structure

```
qr-menu/
├── config/                     settings.py, settings_test.py, urls.py, wsgi.py
├── menus/                      domain app
│   ├── models.py, migrations/
│   ├── constants.py            allergens, diets, themes, languages
│   ├── formatting.py           price parse/format (French)
│   ├── i18n.py                 tr() helper
│   ├── context_processors.py
│   ├── templatetags/menu_tags.py   |tr, |price filters
│   ├── images.py               upload processing + WebP variants
│   ├── signals.py, cache.py    invalidation / content version
│   ├── seed_data.py, seed_assets/, management/commands/   seed_demo, create_admin, backup
│   └── tests/
├── public/                     diner-facing menu
│   ├── views.py, urls.py, middleware.py, menu_context.py
│   ├── theming.py              palette + WCAG contrast adjust
│   ├── strings.py              FR/EN UI strings
│   ├── templatetags/public_tags.py
│   └── tests/
├── editor/                     admin app (auth + menu editor + live preview)
├── printing/                   QR + PDF app
├── ai/                         AI import + translation app
├── templates/                  public/, editor/, printing/, ai/, registration/, 404/500
├── static/                     public/ (css, js, fonts, icons.svg), editor/ (htmx, Sortable), printing/, ai/
├── docker/                     Dockerfile, Caddyfile, entrypoint.sh
├── docker-compose.yml, .env.example
├── scripts/                    backup.sh, restore.sh, screenshots.py
├── e2e/                        Playwright end-to-end tests
├── docs/                       ARCHITECTURE.md, screenshots/, qa/
└── DESIGN.md                   public menu design system
```

## 4. Data model (`menus/models.py`)

Translatable text = `JSONField(default=dict)` holding `{"fr": str, "en": str}`. Read it with
`menus.i18n.tr(value, lang)` (falls back to `fr`, then first non-empty). Prices are integer
cents; display is always French format `12,50 €` (NBSP before €), for both languages.

**Restaurant**
- `name` (str) · `slug` (unique; generated from name; **immutable once `first_published_at`
  is set**, enforced in `save()`) · `tagline` (tr) · `logo` (image, optional)
- `brand_color` (hex, default `#7a2e2a`) · `accent_color` (hex, optional)
- `theme` (`bistro|trattoria|cafe|gastro|auberge`) · `color_mode` (`auto|light|dark`)
- `address` (text) · `maps_url` (optional override; default built from address) · `phone`
- `hours` (tr, multi-line text; each line rendered as a row) · `footer_note` (tr, e.g.
  "Prix nets, service compris")
- `languages` (JSON list, default `["fr","en"]`)
- `is_published` · `first_published_at` · `created_at` · `updated_at` (**content version**:
  bumped by `touch()` whenever the restaurant or any child changes; used for caching/ETag)

**Category** — `restaurant` FK · `name` (tr) · `description` (tr, optional, e.g. "Servis avec
frites maison") · `position` · `is_visible`

**Item** — `category` FK · `name` (tr) · `description` (tr) · `prices` (JSON list of
`{"label": {"fr": "25 cl", "en": "25 cl"}, "cents": 850}`; label optional; empty list = no
price shown) · `photo` (image, optional; normalized JPEG, WebP variants generated on save) ·
`allergens` (list of codes) · `diets` (list of codes) · `is_sold_out` · `is_visible` · `position`

**DailySpecial** ("Plat du jour / Formule") — `restaurant` FK · `kind`
(`plat|formule|dessert|suggestion`) · `title` (tr) · `description` (tr) · `prices` (same shape
as Item) · `is_active` · `position` · `updated_at`

Codes (`menus/constants.py`):
- 14 EU allergens: `gluten, crustaceans, eggs, fish, peanuts, soy, milk, nuts, celery,
  mustard, sesame, sulphites, lupin, molluscs`
- Diets: `vegetarian, vegan, gluten_free`
- Each has FR/EN labels in constants; icon = `static/public/icons.svg#al-<code>` /
  `#diet-<code>` (the editor reuses the same sprite).

## 5. Routes / contracts

### Public
| URL | Name | Notes |
|---|---|---|
| `/m/<slug>/` | `public:menu` | **Permanent QR target**. Lang from `?lang=` (sets `menu_lang` cookie, 1 year, a preference cookie — not tracking), else cookie, else `Accept-Language` if `en` is preferred and enabled, else `fr`. Unpublished → 404 unless admin. |
| `/m/<slug>/?preview=1&theme=<t>&mode=<m>&photos=0` | — | Admin only: no cache, `theme`/`mode` overrides for the live preview and theme switcher; `photos=0` hides photos (design screenshots). |
| `/healthz` | `healthz` | 200 "ok" |
| `/` | — | Redirect to `/admin/` |

Permanent public URL = `settings.PUBLIC_BASE_URL + reverse("public:menu", args=[slug])`, also
available as `restaurant.public_url`.

Template context for `templates/public/menu.html` is produced by
`public.menu_context.build_menu_context(restaurant, lang, *, theme=None, mode=None,
preview=False)` and documented in that module's docstring (dataclasses `MenuView`,
`CategoryView`, `ItemView`, `SpecialView`, `PriceView`). Theme templates render it; fields may be
added, but renaming or removing one means updating every theme.

Theme palette contract (`public/theming.py`):
`build_theme_vars(theme: str, brand_color: str, accent_color: str | None) -> dict` returning
`{"light": {"--var": "value", ...}, "dark": {...}}` — all combinations guaranteed WCAG AA for
text they're used on. Template renders them as CSS custom properties.

### Admin. All under `/admin/`, login required.
| URL | Name |
|---|---|
| `/admin/login/`, `/admin/logout/` | `editor:login`, `editor:logout` |
| `/admin/` | `editor:dashboard` |
| `/admin/r/new/` | `editor:restaurant_new` |
| `/admin/r/<pk>/` | `editor:restaurant_edit` (menu editor + preview) |
| `/admin/r/<pk>/settings/` | `editor:restaurant_settings` |
| other editor endpoints (HTMX partials, reorder, upload…) | `editor:*` |
| `/admin/r/<pk>/print/` | `printing:print_page` |
| `/admin/r/<pk>/qr.svg`, `/admin/r/<pk>/qr.png` | `printing:qr_svg`, `printing:qr_png` |
| `/admin/r/<pk>/print/stickers.pdf`, `/admin/r/<pk>/print/tent.pdf` | `printing:stickers_pdf`, `printing:tent_pdf` |
| `/admin/r/<pk>/import/` (upload → review → save) | `ai:import` (+ sub-routes) |
| `POST /admin/ai/translate/` | `ai:translate` |
| `POST /admin/r/<pk>/translate-missing/` | `ai:translate_missing` |
| `/dj/` | Django admin (emergency data fixes) |

`POST /admin/ai/translate/` — JSON in `{"source": "fr", "target": "en", "texts": {"key": "texte", ...}}`
→ 200 `{"translations": {"key": "text", ...}}`; 503 `{"error": "..."}` when AI is disabled or
fails. CSRF via `X-CSRFToken` header.

`POST /admin/r/<pk>/translate-missing/` — fills every empty `en` field of the restaurant's
categories/items/specials/tagline/hours/footer_note from `fr`; returns an HTMX-friendly
fragment or redirects back to `editor:restaurant_edit` with a message.

Context processor `menus.context_processors.app_flags` exposes `AI_ENABLED` (bool; true when `ANTHROPIC_API_KEY` is set or `AI_FAKE=1`, which returns canned results for tests/e2e) and
`PUBLIC_BASE_URL` to all templates. The editor shows AI buttons only if `AI_ENABLED`.

`templates/editor/base.html` provides blocks: `title`,
`extra_head`, `content`, `extra_js`, and optional context `restaurant` for the nav. The print
and AI pages extend it and rely on nothing else.

### Python service contracts
- `menus.formatting.format_price(cents) -> "12,50 €"`, `format_prices(prices, lang) -> "8,50 € / 14,00 €"`, `parse_price("12,5") -> 1250` (accepts `12,50`, `12.5`, `12 €`, `12€50`; `None` on garbage).
- `menus.i18n.tr(value: dict, lang: str) -> str`.
- `menus.images.process_photo(file) -> ContentFile` — EXIF-rotate, max 1600 px, JPEG q82, strip metadata. `menus.images.process_logo(file) -> ContentFile` (PNG/WebP keeping alpha, max 512 px). `menus.images.photo_view(field_file) -> dict | None` → `{"src", "srcset", "width", "height"}` (WebP variants 480/960 generated on save).
- `Restaurant.touch()` bumps `updated_at`; editor views call it, and child saves trigger it through signals.
- `ai.services.extract_menu(images: list[bytes], media_types: list[str]) -> ExtractedMenu` (pydantic), `ai.services.translate_texts(texts: dict[str,str], source, target) -> dict[str,str]`, both raise `ai.services.AIUnavailable` when disabled/failing.
- `printing.qr.make_qr_svg(url, color) -> str`, `make_qr_png(url, scale) -> bytes`.

## 6. Performance & quality targets
- Public menu: 1 HTML response with inline CSS (< 20 KB gz), fonts preloaded (max 2 families/theme,
  WOFF2, latin subset, `font-display: swap`), JS deferred (< 6 KB), images lazy with explicit size.
- Lighthouse mobile ≥ 95 Performance and Accessibility.
- No cookies except `menu_lang` (preference) on public pages; session/CSRF cookies only under `/admin/`.
- Test at 375 px and 1280 px; no horizontal scroll; tap targets ≥ 44 px.
