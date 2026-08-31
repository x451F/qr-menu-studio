import os
import sqlite3
import tarfile
from io import StringIO

import pytest
from django.core.management import call_command

from menus import images
from menus.models import Item
from menus.tests.factories import image_file, make_menu


def run_backup(tmp_path, *args):
    out = StringIO()
    call_command("backup", "--output-dir", str(tmp_path / "backups"), *args, stdout=out, stderr=StringIO())
    return out.getvalue().strip().splitlines()[-1]


@pytest.mark.django_db(transaction=True)
def test_backup_archive_contains_database_and_media(tmp_path):
    restaurant, cat, _ = make_menu(n_items=0)
    item = Item.objects.create(category=cat, name={"fr": "Photo"})
    item.photo.save("a.jpg", images.process_photo(image_file()), save=True)

    path = run_backup(tmp_path)
    assert path.endswith(".tar.gz") and os.path.exists(path)
    assert os.path.basename(path).startswith("qrmenu-")

    with tarfile.open(path) as tar:
        names = tar.getnames()
        assert "db.sqlite3" in names
        assert any(n.startswith("media/photos/") and n.endswith(".jpg") for n in names)
        assert any(n.endswith(".960.webp") for n in names)
        tar.extract("db.sqlite3", tmp_path / "restore", filter="data")
    conn = sqlite3.connect(tmp_path / "restore" / "db.sqlite3")
    try:
        assert conn.execute("select name from menus_restaurant").fetchone()[0] == restaurant.name
        assert conn.execute("pragma integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


@pytest.mark.django_db(transaction=True)
def test_backup_prunes_old_archives(tmp_path):
    paths = [run_backup(tmp_path, "--keep", "3") for _ in range(5)]
    remaining = sorted((tmp_path / "backups").glob("qrmenu-*.tar.gz"))
    assert len(remaining) == 3
    assert paths[-1] in {str(p) for p in remaining}
    assert not list((tmp_path / "backups").glob("*.partial"))


@pytest.mark.django_db(transaction=True)
def test_backup_works_without_media_dir(tmp_path):
    path = run_backup(tmp_path)
    with tarfile.open(path) as tar:
        assert tar.getnames() == ["db.sqlite3"]
