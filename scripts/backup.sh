#!/usr/bin/env bash
# Back up the database and media of the running Docker deployment.
#
#   scripts/backup.sh [DEST_DIR]
#
# Runs `manage.py backup` inside the `web` container (consistent SQLite online backup + media,
# 14 newest archives kept in the data volume under /data/backups). With DEST_DIR the new archive
# is also copied to the host, e.g. for rsync/rclone off-site copies. Prints the archive path.
set -euo pipefail

cd "$(dirname "$0")/.."
DEST_DIR="${1:-}"

container_path="$(docker compose exec -T web python manage.py backup | tail -n 1 | tr -d '\r')"
if [ -z "$container_path" ]; then
  echo "backup failed: no archive path returned" >&2
  exit 1
fi

if [ -n "$DEST_DIR" ]; then
  mkdir -p "$DEST_DIR"
  docker compose cp "web:${container_path}" "$DEST_DIR/"
  echo "$DEST_DIR/$(basename "$container_path")"
else
  echo "web:${container_path}"
fi
