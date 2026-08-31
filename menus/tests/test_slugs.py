import pytest
from django.core.exceptions import ValidationError

from menus.models import Restaurant


@pytest.mark.django_db
def test_slug_generated_from_name_with_accents():
    r = Restaurant.objects.create(name="Le Bistrot des Halles – Tulle")
    assert r.slug == "le-bistrot-des-halles-tulle"
    assert Restaurant.objects.create(name="Café de l'Été").slug == "cafe-de-lete"


@pytest.mark.django_db
def test_slug_fallback_for_unsluggable_name():
    assert Restaurant.objects.create(name="!!!").slug == "menu"
    assert Restaurant.objects.create(name="???").slug == "menu-2"


@pytest.mark.django_db
def test_slug_uniqueness_with_numeric_suffix():
    slugs = [Restaurant.objects.create(name="Chez Paul").slug for _ in range(3)]
    assert slugs == ["chez-paul", "chez-paul-2", "chez-paul-3"]


@pytest.mark.django_db
def test_slug_is_editable_before_publication():
    r = Restaurant.objects.create(name="Chez Paul")
    r.slug = "paul-et-fils"
    r.save()
    r.refresh_from_db()
    assert r.slug == "paul-et-fils"
    assert not r.slug_is_locked()


@pytest.mark.django_db
def test_slug_immutable_after_first_publication():
    r = Restaurant.objects.create(name="Chez Paul", is_published=True)
    assert r.first_published_at is not None
    assert r.slug_is_locked()
    r.slug = "autre-chose"
    r.name = "Nouveau nom"
    r.save()
    r.refresh_from_db()
    assert r.slug == "chez-paul"


@pytest.mark.django_db
def test_slug_stays_locked_after_unpublishing():
    r = Restaurant.objects.create(name="Chez Paul", is_published=True)
    r.is_published = False
    r.save()
    r.slug = "changed"
    r.save()
    r.refresh_from_db()
    assert r.slug == "chez-paul"
    assert r.slug_is_locked()


@pytest.mark.django_db
def test_clean_rejects_slug_change_when_published():
    r = Restaurant.objects.create(name="Chez Paul", is_published=True)
    r.slug = "autre"
    with pytest.raises(ValidationError) as exc:
        r.clean()
    assert "slug" in exc.value.message_dict


@pytest.mark.django_db
def test_public_url_uses_base_url(settings):
    settings.PUBLIC_BASE_URL = "https://menu.example.fr"
    r = Restaurant.objects.create(name="Chez Paul")
    assert r.public_url == "https://menu.example.fr/m/chez-paul/"
