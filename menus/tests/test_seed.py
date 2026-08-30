from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management import call_command

from menus.constants import ALLERGENS, DIETS, THEMES
from menus.models import Category, DailySpecial, Item, Restaurant
from menus.seed_data import DEMO_RESTAURANTS, LOGOS, PHOTOS, photo_for
from menus.tests.factories import make_restaurant

ASSETS = Path(__file__).resolve().parents[1] / "seed_assets"


def seed(*args):
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def test_seed_data_is_consistent():
    assert {d["theme"] for d in DEMO_RESTAURANTS} == set(THEMES)
    assert len({d["slug"] for d in DEMO_RESTAURANTS}) == len(DEMO_RESTAURANTS)
    for data in DEMO_RESTAURANTS:
        names = []
        for _c_fr, _c_en, _d_fr, _d_en, items in data["categories"]:
            for it in items:
                names.append(it[0])
                assert set(it[5]) <= set(ALLERGENS), it[0]
                assert set(it[6]) <= set(DIETS), it[0]
                stem = photo_for(data["slug"], it[0], it[7])
                if stem:
                    assert (ASSETS / "photos" / f"{stem}.jpg").exists(), stem
        for prefix, _stem in PHOTOS.get(data["slug"], []):
            assert sum(n.startswith(prefix) for n in names) == 1, prefix
    for logo in LOGOS.values():
        assert (ASSETS / "logos" / logo).exists()
    for photo in (ASSETS / "photos").glob("*.jpg"):
        assert photo.stat().st_size <= 180 * 1024
        assert f"photos/{photo.stem}.jpg" in (ASSETS / "CREDITS.md").read_text()


@pytest.mark.django_db
def test_seed_creates_one_published_restaurant_per_theme():
    seed()
    assert Restaurant.objects.filter(is_published=True).count() == len(DEMO_RESTAURANTS)
    assert set(Restaurant.objects.values_list("theme", flat=True)) == set(THEMES)
    gino = Restaurant.objects.get(slug="chez-gino")
    assert Item.objects.filter(category__restaurant=gino).count() >= 75
    assert Restaurant.objects.get(slug="petit-kiosque").categories.first().items.count() == 5
    assert not Restaurant.objects.get(slug="petit-kiosque").logo
    assert Restaurant.objects.get(slug="bistrot-des-halles").logo
    vialle_items = Item.objects.filter(category__restaurant__slug="maison-vialle")
    assert vialle_items.count() and all(i.photo for i in vialle_items)
    assert Item.objects.filter(is_sold_out=True).exists()
    assert DailySpecial.objects.filter(restaurant=gino).exists()


@pytest.mark.django_db
def test_seed_runs_twice_idempotently_and_leaves_other_restaurants_alone():
    other = make_restaurant("Mon Resto")
    seed("--admin-password", "a-long-password-1")
    first_counts = (Restaurant.objects.count(), Category.objects.count(), Item.objects.count())
    photos_before = {i.photo.name for i in Item.objects.exclude(photo="")}
    seed("--admin-password", "a-long-password-2")
    assert (Restaurant.objects.count(), Category.objects.count(), Item.objects.count()) == first_counts
    assert Restaurant.objects.filter(pk=other.pk).exists()
    assert get_user_model().objects.filter(username="admin").count() == 1
    assert get_user_model().objects.get(username="admin").check_password("a-long-password-2")
    # old photo files were removed when the demo restaurants were rebuilt
    assert not any(default_storage.exists(n) for n in photos_before)
    for item in Item.objects.exclude(photo=""):
        assert default_storage.exists(item.photo.name)


@pytest.mark.django_db
def test_if_empty_skips_when_restaurants_exist():
    make_restaurant("Mon Resto")
    out = seed("--if-empty")
    assert "skipping" in out
    assert Restaurant.objects.count() == 1


@pytest.mark.django_db
def test_if_empty_seeds_when_empty_and_creates_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "x" * 12)
    seed("--if-empty", "--admin-password", "y" * 12)
    assert Restaurant.objects.count() == len(DEMO_RESTAURANTS)
    assert get_user_model().objects.get(username="admin").is_superuser


@pytest.mark.django_db
def test_create_admin_command():
    call_command("create_admin", "--password", "z" * 12, "--username", "chef", stdout=StringIO())
    user = get_user_model().objects.get(username="chef")
    assert user.is_staff and user.check_password("z" * 12)
    out = StringIO()
    call_command("create_admin", "--password", "", stdout=out)
    assert "untouched" in out.getvalue()
