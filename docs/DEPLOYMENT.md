# Running and deploying QR Menu Studio

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
Wikimedia Commons (CC0 / public domain / CC BY), see [`menus/seed_assets/CREDITS.md`](../menus/seed_assets/CREDITS.md).

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
