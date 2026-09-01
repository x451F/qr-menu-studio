import io

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from PIL import Image

from menus.images import process_photo
from menus.models import Category, Item, Restaurant


def _jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 100, 50)).save(buf, "JPEG")
    return ContentFile(buf.getvalue(), name="dish.jpg")


@pytest.mark.django_db
def test_undo_restores_photo_file(client, django_user_model, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    user = django_user_model.objects.create_user("admin", password="x" * 12, is_staff=True)
    client.force_login(user)
    r = Restaurant.objects.create(name="Undo Test")
    cat = Category.objects.create(restaurant=r, name={"fr": "Plats"})
    item = Item.objects.create(category=cat, name={"fr": "Steak"})
    item.photo.save("dish.jpg", process_photo(_jpeg(), "dish.jpg"), save=True)
    name = item.photo.name

    client.post(reverse("editor:item_delete", args=[item.pk]))
    assert default_storage.exists(name)
    client.post(reverse("editor:item_undo", args=[r.pk]))
    restored = Item.objects.get(category=cat)
    assert restored.photo.name == name and default_storage.exists(name)

    # A second delete without undo, followed by another delete, discards the kept file.
    other = Item.objects.create(category=cat, name={"fr": "Salade"})
    client.post(reverse("editor:item_delete", args=[restored.pk]))
    client.post(reverse("editor:item_delete", args=[other.pk]))
    assert not default_storage.exists(name)
