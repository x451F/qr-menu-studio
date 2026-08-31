"""Consistent backup of the database and uploaded media.

    python manage.py backup [--keep 14] [--output-dir DIR]

Writes ``$DATA_DIR/backups/qrmenu-YYYYmmdd-HHMMSS.tar.gz`` containing ``db.sqlite3`` (made with
SQLite's online backup API, safe while the site is running) and ``media/``. Older archives beyond
``--keep`` are deleted. The archive path is the last line printed.
"""

import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PREFIX = "qrmenu-"


def sqlite_online_backup(dest: Path) -> None:
    connection.ensure_connection()
    target = sqlite3.connect(dest)
    try:
        connection.connection.backup(target)
    finally:
        target.close()


class Command(BaseCommand):
    help = "Back up db.sqlite3 + media/ into a timestamped tar.gz and prune old backups."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=14, help="Number of archives to keep (default 14).")
        parser.add_argument("--output-dir", default=str(Path(settings.DATA_DIR) / "backups"))

    def handle(self, *args, **opts):
        if opts["keep"] < 1:
            raise CommandError("--keep must be at least 1")
        out_dir = Path(opts["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = out_dir / f"{PREFIX}{stamp}.tar.gz"
        n = 1
        while archive.exists():  # two backups within the same second
            archive = out_dir / f"{PREFIX}{stamp}-{n}.tar.gz"
            n += 1

        media = Path(settings.MEDIA_ROOT)
        with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
            db_copy = Path(tmp) / "db.sqlite3"
            sqlite_online_backup(db_copy)
            partial = archive.with_suffix(".partial")
            with tarfile.open(partial, "w:gz") as tar:
                tar.add(db_copy, arcname="db.sqlite3")
                if media.exists():
                    tar.add(media, arcname="media")
            shutil.move(partial, archive)

        backups = sorted(out_dir.glob(f"{PREFIX}*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[opts["keep"] :]:
            old.unlink()
            self.stderr.write(f"Removed old backup {old.name}")
        self.stdout.write(str(archive))
