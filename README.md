# QR Menu Studio

Internal tool that turns a restaurant's paper menu into a fast public web menu with printed QR
codes. Django + SQLite, server-rendered pages, deployed with Docker Compose (Django/gunicorn +
Caddy). One data volume holds everything: `db.sqlite3`, `media/` (photos, logos) and `backups/`.

Menus live at a permanent URL, `https://<your-domain>/m/<slug>/`, which is what the QR codes point
to. The slug of a published restaurant can never change. Architecture notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features

- **One admin, many restaurants.** Single password login; each restaurant has a name, logo, brand colours, theme, address, phone, opening hours and languages.
- **Menu editor** (phone-first): categories and dishes with FR/EN names and descriptions, French prices (`12,50 €`, several sizes such as `Verre / Bouteille`), optional photos (auto-compressed, WebP variants), the 14 EU allergens and diet tags (végétarien, vegan, sans gluten), sold-out toggle, drag-and-drop ordering, autosave, and a live phone preview.
- **"Aujourd'hui" panel**: plat du jour, formule, dessert or suggestion, edited in a few taps and shown at the top of the public menu.
- **Five themes**, each in light and dark: `bistro`, `trattoria`, `cafe`, `gastro`, `auberge`. The restaurant's colours are applied and automatically adjusted to keep WCAG AA contrast. Design notes are in [DESIGN.md](DESIGN.md) and screenshots in [docs/screenshots/](docs/screenshots/).
- **Public menu** at a permanent URL `https://<domain>/m/<slug>/`: server-rendered, about 15 KB gzipped for 80 dishes, and no cookies except the chosen language.
  - FR/EN switch, sticky category chips, and a dish bottom sheet (the Back button closes it).
  - Search plus allergen and diet filters, and sold-out dishes greyed rather than hidden.
  - Footer with tap-to-call, maps link and hours.
- **QR codes and print**: QR as SVG or PNG (brand colour when it stays scannable), and print-ready PDFs of table stickers and chevalets (table tents).
- **AI import**: photograph the paper menu, Claude reads it into categories, dishes and prices, and you correct everything on a review screen before saving. There is also one-click "Translate missing" FR to EN. Both are optional; everything else works without an API key.

## Using the editor

Typical 10-minute session in front of the owner:

1. **Sign in** at `/admin/` (the account comes from `ADMIN_USERNAME` / `ADMIN_PASSWORD`).
2. **New restaurant**: type the name and pick a theme. Sensible defaults are applied (FR+EN, footer note "Prix nets, service compris."). You land in the menu editor.
3. **Fill the menu**: either *Import from photo* (see below), or type it in:
   - Add a category, type a dish name, press Enter, type the price (`12,50`, `12.5`, `12€50` all work) and press Enter again for the next dish.
   - Tap a dish to open it: description, extra sizes, allergen and diet chips, photo (the phone camera works), sold-out, visibility, duplicate, delete (with Undo).
   - Drag the ⋮⋮ handles to reorder categories and dishes, or use the *Category* select inside a dish to move it.
   - The **Editing: FR | EN** switch shows English fields with the French text as a hint; *Translate missing with AI* fills every empty English field.
4. **Aujourd'hui panel**: add a *Plat du jour* or *Formule* in one tap, with several labelled prices if needed. The *Active* toggle hides it from the public menu without deleting it.
5. **Preview**: on desktop it sits next to the editor; on a phone tap **Preview**. The theme, light/dark and photos toggles only change the preview, so you can show the owner options. *Use this theme* saves the choice.
6. **Settings**: logo, brand and accent colours, colour mode, address, phone, hours (one line per row, e.g. `Mardi – Samedi : 12h – 14h, 19h – 22h`), footer note, English on/off.
7. **Publish**. From this moment the menu is live and **its address can never change**, because printed QR codes point to it. Every later edit is saved and live immediately.

## Printing QR codes

Open **Print & QR** from the editor or dashboard (`/admin/r/<id>/print/`):

- **QR code** as SVG (vector, for print shops) or PNG (512–2048 px), in the brand colour or black. A pale brand colour is automatically darkened so the code stays scannable.
- **Table stickers** (A4 sheet): 5, 7 or 10 cm, square or round, with cut marks. 7 cm or more is recommended for tables.
- **Chevalets (table tents)**:
  - *A5 tent*: one A4 sheet, fold in the middle.
  - *A6 tent*: two tents per A4 sheet, cut and fold marks included.
  - Each tent carries the logo or name, the QR code, "Scannez pour voir le menu · Scan for the menu", the short URL and an optional line such as "Plat du jour à l'ardoise".
- Print at **100 % / actual size**. The QR always encodes the permanent URL `PUBLIC_BASE_URL/m/<slug>/`, so set `PUBLIC_BASE_URL` to the real domain **before** printing anything. If the restaurant is not published yet, the page warns you, because the code works but diners would see a 404.

## AI import & translation

- Set `ANTHROPIC_API_KEY` in `.env` to enable the AI features. The model is `claude-opus-5-5` unless you set `ANTHROPIC_MODEL`.
- **Import from photo** (`/admin/r/<id>/import/`):
  - Take or choose up to 6 photos (one per page, flat, good light).
  - Claude extracts categories, dishes, descriptions, prices as printed, and allergens or diets only when the menu marks them. Reading takes about 20–60 s.
  - On the **review screen** you fix anything flagged, such as an unreadable price, untick items, and rename categories. You can also merge into existing categories, import the specials and fill empty restaurant info (phone, address, hours).
  - Nothing is saved until you press **Save**. Imported text goes into French; tick *Also translate to English* to translate at the same time.
- **Translate missing**: in the editor, one call fills every empty English field (restaurant texts, categories, dishes, specials, price labels) from the French. There is also a per-field *Translate* button.
- **Without a key** the AI buttons are hidden and the import page explains how to enable it; everything else works normally. `AI_FAKE=1` returns a canned sample menu and fake translations, for demos and automated tests, without calling the API.
- Photos are resized to at most 2000 px before being sent. The API key is only read from the environment and is never logged.

## Local development

Requirements: Python 3.13 and [uv](https://docs.astral.sh/uv/). PDF export (WeasyPrint) needs
pango: `brew install pango` on macOS, `apt install libpango-1.0-0 libpangoft2-1.0-0` on Debian.

```bash
uv sync
export DJANGO_DEBUG=1                # insecure dev secret key allowed
uv run python manage.py migrate
uv run python manage.py seed_demo --admin-password devpassword123
uv run python manage.py runserver 8000
uv run pytest                        # tests
uv run ruff check .                  # lint
```

Open <http://localhost:8000/admin/> (`admin` / `devpassword123`) and the demo menus:

| Restaurant | URL | Theme |
|---|---|---|
| Le Bistrot des Halles | `/m/bistrot-des-halles/` | bistro |
| Chez Gino (about 80 items) | `/m/chez-gino/` | trattoria |
| Le Petit Kiosque | `/m/petit-kiosque/` | cafe |
| Maison Vialle | `/m/maison-vialle/` | gastro (dark) |
| Auberge du Puy Blanc | `/m/auberge-du-puy-blanc/` | auberge (pale yellow brand colour) |

`seed_demo` is idempotent: it rebuilds only these demo restaurants (by slug) and never touches
other data. `--if-empty` seeds only when there are no restaurants at all. Demo photos come from
Wikimedia Commons (CC0 / public domain / CC BY), see `menus/seed_assets/CREDITS.md`.

Useful management commands: `seed_demo`, `create_admin` (create/update the admin from
`ADMIN_USERNAME` / `ADMIN_PASSWORD`), `backup`.

## Docker: try it locally

```bash
docker compose up --build
```

No `.env` needed. Then open <http://localhost:8080/> (menus: `/m/chez-gino/`, admin: `/admin/`,
login `admin` / `local-admin-password`). The first start loads the demo restaurants. Stop with
`docker compose down`; add `-v` to also delete the data volume.

The local defaults are deliberately insecure (public secret key, known admin password): never
use them on a public server.

## Configuration

All settings are environment variables; with Docker, put them in `.env` (copy `.env.example`).

| Variable | Default (local) | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure local key | Signs sessions/CSRF. **Set a long random value in production.** |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host names Django answers to (your domain). |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `PUBLIC_BASE_URL` | Origins (with scheme) allowed to POST to the admin. |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | Base URL printed into QR codes, no trailing slash. |
| `SITE_ADDRESS` | `:80` | Caddy site address. A domain gives automatic HTTPS; `:80` is plain HTTP. |
| `HTTP_PORT`, `HTTPS_PORT` | `8080`, `8443` | Host ports published by Caddy. Use `80` and `443` in production. |
| `ADMIN_USERNAME` | `admin` | Admin account, created/updated on every start when a password is set. |
| `ADMIN_PASSWORD` | `local-admin-password` | Admin password. Set a long unique one in production. |
| `ANTHROPIC_API_KEY` | empty | Enables AI import/translation. Empty hides the AI buttons. |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | Model used for AI features. |
| `AI_FAKE` | `0` | `1` returns canned AI results without calling the API (demos, tests). |
| `SEED_DEMO` | `1` locally, `0` in `.env.example` | `1` loads demo restaurants at start when the database is empty. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |
| `DATA_DIR` | `/data` in Docker, `./data` otherwise | Where `db.sqlite3`, `media/` and `backups/` live. |
| `DJANGO_DEBUG` | `0` in Docker | `1` only for local development. |

## Deploying to a VPS

1. **Server.** Any small VPS (1 vCPU, 1 GB RAM is enough) running Debian 12+ or Ubuntu 22.04+.
2. **DNS.** At your registrar, create an `A` record (and `AAAA` if the server has IPv6) for
   `[YOUR_DOMAIN]` (for example `menu.example.fr`) pointing to the server's IP. Wait until
   `dig +short [YOUR_DOMAIN]` returns it. Caddy cannot get a certificate before that.
3. **Firewall.** Allow ports 22, 80 and 443 (`ufw allow OpenSSH && ufw allow 80,443/tcp && ufw allow 443/udp && ufw enable`).
4. **Install Docker** (official convenience script, includes the compose plugin):
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker "$USER"   # log out and back in afterwards
   docker compose version
   ```
5. **Get the code.**
   ```bash
   git clone <your-repo-url> qr-menu && cd qr-menu
   ```
6. **Configure.** `cp .env.example .env`, then edit `.env`:
   - `DJANGO_SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `PUBLIC_BASE_URL`, `SITE_ADDRESS`: your domain
   - `ADMIN_PASSWORD`: a long unique password
   - `ANTHROPIC_API_KEY`: optional, for AI import
   - keep `SEED_DEMO=0`, `HTTP_PORT=80`, `HTTPS_PORT=443`
7. **Start.** `docker compose up -d --build`. The first start builds the image (a few minutes),
   runs migrations, creates the admin account and obtains the HTTPS certificate.
   Check with `docker compose ps` and `docker compose logs -f web caddy`.
8. **First login.** Open `https://[YOUR_DOMAIN]/admin/` and sign in with `ADMIN_USERNAME` /
   `ADMIN_PASSWORD`. Create your restaurant, publish it, and print the QR codes. Decide the
   domain before printing: QR codes contain `PUBLIC_BASE_URL`.
9. **Set up backups** (next section) before entering real data.

**Updating.**

```bash
cd qr-menu
scripts/backup.sh          # safety copy first
git pull
docker compose up -d --build
```

Migrations run automatically at start. Menu pages stay online except for a few seconds while `web` restarts.

## Backups and restore

`python manage.py backup` (run inside the container by `scripts/backup.sh`) writes
`/data/backups/qrmenu-YYYYmmdd-HHMMSS.tar.gz` containing a consistent copy of `db.sqlite3`
(SQLite online backup API, safe while the site is running) plus `media/`. The 14 newest archives
are kept.

```bash
scripts/backup.sh                       # backup inside the volume, prints the path
scripts/backup.sh ~/qr-backups          # ...and copy the archive to the host
scripts/restore.sh ~/qr-backups/qrmenu-20260101-030000.tar.gz
```

`restore.sh` stops `web`, replaces `db.sqlite3` and `media/` in the volume (the previous ones are
kept as `*.pre-restore-<timestamp>`), and starts `web` again. To use another compose project name
set `COMPOSE_PROJECT_NAME`.

**Daily backup with cron** (3:15 every night, host copy in `~/qr-backups`):

```cron
15 3 * * * cd /home/deploy/qr-menu && scripts/backup.sh /home/deploy/qr-backups >> /home/deploy/qr-backups/backup.log 2>&1
```

**Off-site copy.** A backup on the same server does not survive losing the server. Copy the
host directory somewhere else, for example:

```cron
45 3 * * * rsync -a --delete /home/deploy/qr-backups/ backup-user@other-host:qr-menu-backups/
# or with rclone (S3, Backblaze B2, Google Drive...), after `rclone config`:
50 3 * * * rclone copy /home/deploy/qr-backups remote:qr-menu-backups
```

Test a restore on a scratch machine at least once.

## Troubleshooting

- **`docker compose up` fails with "port is already allocated".** Something else uses the port.
  Change `HTTP_PORT` / `HTTPS_PORT` in `.env` (locally, `HTTP_PORT=8081`).
- **No HTTPS certificate / browser shows a certificate error.** Check that the DNS record points
  to this server, ports 80 and 443 are open, and `SITE_ADDRESS` is the bare domain (no `https://`).
  See `docker compose logs caddy`. Let's Encrypt limits repeated failures; wait a few minutes.
- **`400 Bad Request` on every page.** The domain is missing from `DJANGO_ALLOWED_HOSTS`.
- **Login or admin forms fail with "CSRF verification failed".** Set `DJANGO_CSRF_TRUSTED_ORIGINS`
  to `https://[YOUR_DOMAIN]` (with the scheme) and `PUBLIC_BASE_URL` likewise, then
  `docker compose up -d`.
- **Web container keeps restarting.** `docker compose logs web`. With `DEBUG` off, an empty
  `DJANGO_SECRET_KEY` is a fatal error (the compose file provides a local default only).
  When `PUBLIC_BASE_URL` starts with `https://`, the container also refuses to start with the
  local-demo or `.env.example` placeholder values of `DJANGO_SECRET_KEY` / `ADMIN_PASSWORD`
  ("Refusing to start: ..."): put real values in `.env`.
- **Changed `.env` but nothing changed.** Run `docker compose up -d` again so the containers are recreated.
- **A sold-out toggle is not visible to diners.** Pages are revalidated on every visit and cached
  by content version, so edits show within seconds. A stale page usually means a caching proxy
  in front of Caddy; make sure it honours `Cache-Control: no-cache`.
- **Forgot the admin password.** Set a new `ADMIN_PASSWORD` in `.env` and run `docker compose up -d`
  (the account is updated at start), or `docker compose exec web python manage.py changepassword admin`.
- **Photos do not load.** Uploaded files are served by Caddy from the data volume at `/media/`.
  Check `docker compose logs caddy` and that both services mount the same `data` volume.
- **PDF export errors about pango or fonts** (local, non-Docker): install pango (see Local development).
- **Reset everything locally.** `docker compose down -v` deletes the data volume (all menus).
