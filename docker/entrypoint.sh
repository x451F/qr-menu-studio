#!/bin/sh
# Container entrypoint: migrate, optional demo data / admin account, then gunicorn.
set -eu

mkdir -p "${DATA_DIR:-/data}/media" "${DATA_DIR:-/data}/backups"

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
