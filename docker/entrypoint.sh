#!/bin/sh
# Container entrypoint: migrate, optional demo data / admin account, then gunicorn.
set -eu

mkdir -p "${DATA_DIR:-/data}/media" "${DATA_DIR:-/data}/backups"

# A public (https) deployment must not run with the local-demo defaults from docker-compose.yml.
case "${PUBLIC_BASE_URL:-}" in
  https://*)
    case "${DJANGO_SECRET_KEY:-}" in
      ""|insecure-*|change-me*) echo "Refusing to start: set a real DJANGO_SECRET_KEY in .env (see docs/DEPLOYMENT.md)." >&2; exit 1 ;;
    esac
    case "${ADMIN_PASSWORD:-}" in local-admin-password|change-me*)
      echo "Refusing to start: set your own ADMIN_PASSWORD in .env, or leave it empty (see docs/DEPLOYMENT.md)." >&2; exit 1 ;;
    esac
    ;;
esac

python manage.py migrate --noinput

if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_demo --if-empty
fi

if [ -n "${ADMIN_PASSWORD:-}" ]; then
  python manage.py create_admin
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 330 \
  --access-logfile - \
  --error-logfile -
