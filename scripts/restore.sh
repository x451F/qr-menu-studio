#!/usr/bin/env bash
# Restore a backup archive (made by scripts/backup.sh / `manage.py backup`) into the Docker deployment.
#
#   scripts/restore.sh path/to/qrmenu-YYYYmmdd-HHMMSS.tar.gz
#
# Stops `web`, replaces db.sqlite3 and media/ in the data volume (the previous versions are kept
# as db.sqlite3.pre-restore-* and media.pre-restore-*), then starts `web` again.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "usage: $0 path/to/qrmenu-YYYYmmdd-HHMMSS.tar.gz" >&2
  exit 2
fi
ARCHIVE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"

if ! tar -tzf "$ARCHIVE" db.sqlite3 >/dev/null 2>&1; then
  echo "error: $ARCHIVE does not look like a QR Menu Studio backup (no db.sqlite3)" >&2
  exit 1
fi

echo "Stopping web..."
docker compose stop web

echo "Restoring from $ARCHIVE ..."
docker compose run --rm --no-deps -T \
  -v "$ARCHIVE:/restore/backup.tar.gz:ro" \
  --entrypoint sh web -c '
    set -eu
    ts=$(date +%Y%m%d-%H%M%S)
    tmp=$(mktemp -d /data/.restore.XXXXXX)
    tar -xzf /restore/backup.tar.gz -C "$tmp"
    [ -f "$tmp/db.sqlite3" ] || { echo "no db.sqlite3 in archive" >&2; exit 1; }
    if [ -f /data/db.sqlite3 ]; then mv /data/db.sqlite3 "/data/db.sqlite3.pre-restore-$ts"; fi
    rm -f /data/db.sqlite3-wal /data/db.sqlite3-shm
    mv "$tmp/db.sqlite3" /data/db.sqlite3
    if [ -d /data/media ]; then mv /data/media "/data/media.pre-restore-$ts"; fi
    if [ -d "$tmp/media" ]; then mv "$tmp/media" /data/media; else mkdir -p /data/media; fi
    rm -rf "$tmp"
    echo "Previous data kept as *.pre-restore-$ts in the data volume."
  '

echo "Starting web..."
docker compose up -d web
echo "Restore complete."
