import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from menus.models import Category, DailySpecial, Item, Restaurant

from .conftest import HX, make_image


def age(restaurant):
    """Push updated_at into the past so a touch() is observable."""
    old = timezone.now() - timedelta(days=1)
    Restaurant.objects.filter(pk=restaurant.pk).update(updated_at=old)
    return old


def bumped(restaurant, old):
    restaurant.refresh_from_db()
    return restaurant.updated_at > old


# -- categories ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_category_add_with_preset_translation(client, restaurant):
    old = age(restaurant)
    resp = client.post(reverse("editor:category_add", args=[restaurant.pk]), {"name_fr": "Entrées"}, **HX)
    assert resp.status_code == 200
    cat = restaurant.categories.get()
    assert cat.name == {"fr": "Entrées", "en": "Starters"}
    assert f'id="cat-{cat.pk}"' in resp.content.decode()
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_category_add_requires_name(client, restaurant):
    resp = client.post(reverse("editor:category_add", args=[restaurant.pk]), {"name_fr": " "}, **HX)
    assert resp.status_code == 422
    assert resp["HX-Retarget"] == "#cat-add-error"
    assert restaurant.categories.count() == 0


@pytest.mark.django_db
def test_category_update_toggle_delete(client, restaurant, category):
    old = age(restaurant)
    client.post(reverse("editor:category_update", args=[category.pk]),
                {"name_fr": "Mains", "name_en": "Main courses", "description_fr": "Avec frites"}, **HX)
    category.refresh_from_db()
    assert category.name == {"fr": "Mains", "en": "Main courses"}
    assert category.description["fr"] == "Avec frites"
    assert bumped(restaurant, old)

    client.post(reverse("editor:category_toggle", args=[category.pk]), **HX)
    category.refresh_from_db()
    assert category.is_visible is False

    old = age(restaurant)
    client.post(reverse("editor:category_delete", args=[category.pk]), **HX)
    assert not Category.objects.filter(pk=category.pk).exists()
    assert bumped(restaurant, old)


# -- items --------------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_create_with_price(client, restaurant, category):
    old = age(restaurant)
    resp = client.post(reverse("editor:item_add", args=[category.pk]),
                       {"name_fr": "Tartare", "price_amount": "12€50"}, **HX)
    assert resp.status_code == 200
    item = category.items.get()
    assert item.name["fr"] == "Tartare"
    assert item.prices == [{"cents": 1250}]
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_item_create_positions_increment(client, category):
    url = reverse("editor:item_add", args=[category.pk])
    for n in ("A", "B", "C"):
        client.post(url, {"name_fr": n}, **HX)
    assert [i.name["fr"] for i in category.items.all()] == ["A", "B", "C"]
    assert [i.position for i in category.items.all()] == [0, 1, 2]


@pytest.mark.django_db
def test_item_create_errors(client, category):
    url = reverse("editor:item_add", args=[category.pk])
    resp = client.post(url, {"name_fr": "", "price_amount": "3"}, **HX)
    assert resp.status_code == 422
    assert resp["HX-Retarget"] == f"#qa-err-{category.pk}"
    resp = client.post(url, {"name_fr": "Soupe", "price_amount": "abc"}, **HX)
    assert resp.status_code == 422
    assert "isn't a valid price" in resp.content.decode()
    assert category.items.count() == 0


@pytest.mark.django_db
def test_item_update_fields(client, restaurant, item):
    old = age(restaurant)
    resp = client.post(
        reverse("editor:item_update", args=[item.pk]),
        {
            "name_fr": "Entrecôte", "name_en": "Ribeye",
            "description_fr": "Grillée", "description_en": "Grilled",
            "_chips": "1", "allergens": ["milk", "bogus"], "diets": ["gluten_free"],
            "price_label_fr": ["", "grande"], "price_label_en": ["", "large"],
            "price_amount": ["18,5", "24"],
        },
        **HX,
    )
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.name == {"fr": "Entrecôte", "en": "Ribeye"}
    assert item.description == {"fr": "Grillée", "en": "Grilled"}
    assert item.allergens == ["milk"]
    assert item.diets == ["gluten_free"]
    assert item.prices == [
        {"cents": 1850},
        {"cents": 2400, "label": {"fr": "grande", "en": "large"}},
    ]
    events = json.loads(resp["HX-Trigger"])
    assert events["pricesFormatted"]["values"] == ["18,50", "24,00"]
    assert "priceError" not in events
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_item_update_partial_post_keeps_other_fields(client, item):
    client.post(reverse("editor:item_update", args=[item.pk]), {"name_en": "Steak"}, **HX)
    item.refresh_from_db()
    assert item.name == {"fr": "Steak", "en": "Steak"}
    assert item.prices == [{"cents": 1800}]


@pytest.mark.django_db
@pytest.mark.parametrize("raw", ["abc", "12,345", "1,2,3", "--3"])
def test_price_parsing_errors_keep_old_prices(client, item, raw):
    resp = client.post(reverse("editor:item_update", args=[item.pk]),
                       {"name_fr": "Renamed", "price_amount": [raw]}, **HX)
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.prices == [{"cents": 1800}]  # not overwritten
    assert item.name["fr"] == "Renamed"  # the rest still saved
    events = json.loads(resp["HX-Trigger"])
    assert events["priceError"]["rows"] == [0]
    assert "isn't a valid price" in events["validation"]["message"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("raw", "cents"), [("12,50", 1250), ("12.5", 1250), ("12 €", 1200), ("12€50", 1250), ("8", 800)]
)
def test_price_formats_accepted(client, item, raw, cents):
    client.post(reverse("editor:item_update", args=[item.pk]), {"price_amount": [raw]}, **HX)
    item.refresh_from_db()
    assert item.prices == [{"cents": cents}]


@pytest.mark.django_db
def test_empty_price_rows_are_ignored_and_clear_prices(client, item):
    resp = client.post(reverse("editor:item_update", args=[item.pk]), {"price_amount": [""]}, **HX)
    item.refresh_from_db()
    assert item.prices == []
    assert "priceError" not in json.loads(resp["HX-Trigger"])


@pytest.mark.django_db
def test_sold_out_and_visibility_toggle(client, restaurant, item):
    old = age(restaurant)
    url = reverse("editor:item_toggle", args=[item.pk, "is_sold_out"])
    resp = client.post(url, **HX)
    item.refresh_from_db()
    assert item.is_sold_out is True
    assert "is-on" in resp.content.decode()
    assert bumped(restaurant, old)
    client.post(url, **HX)
    item.refresh_from_db()
    assert item.is_sold_out is False
    client.post(reverse("editor:item_toggle", args=[item.pk, "is_visible"]), **HX)
    item.refresh_from_db()
    assert item.is_visible is False
    assert client.post(reverse("editor:item_toggle", args=[item.pk, "name"]), **HX).status_code == 400


@pytest.mark.django_db
def test_item_move_via_category_select(client, item, category2):
    resp = client.post(reverse("editor:item_update", args=[item.pk]), {"category": category2.pk}, **HX)
    item.refresh_from_db()
    assert item.category_id == category2.pk
    assert json.loads(resp["HX-Trigger"])["itemMoved"] == {"item": item.pk, "category": category2.pk}


@pytest.mark.django_db
def test_item_duplicate(client, restaurant, item):
    old = age(restaurant)
    other = Item.objects.create(category=item.category, name={"fr": "Zed"}, position=1)
    resp = client.post(reverse("editor:item_duplicate", args=[item.pk]), **HX)
    assert resp.status_code == 200
    names = [i.name["fr"] for i in item.category.items.all()]
    assert names == ["Steak", "Steak (copy)", "Zed"]
    copy = item.category.items.all()[1]
    assert copy.prices == item.prices and copy.pk not in (item.pk, other.pk)
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_item_delete_and_undo(client, restaurant, item, category):
    Item.objects.create(category=category, name={"fr": "Second"}, position=1)
    old = age(restaurant)
    resp = client.post(reverse("editor:item_delete", args=[item.pk]), **HX)
    assert resp.status_code == 200
    assert not Item.objects.filter(pk=item.pk).exists()
    assert "Undo" in resp.content.decode()
    assert bumped(restaurant, old)

    old = age(restaurant)
    resp = client.post(reverse("editor:item_undo", args=[restaurant.pk]), **HX)
    assert resp.status_code == 200
    assert resp["HX-Retarget"] == f"#items-{category.pk}"
    assert [i.name["fr"] for i in category.items.all()] == ["Steak", "Second"]
    assert category.items.first().prices == [{"cents": 1800}]
    assert bumped(restaurant, old)
    # nothing left to undo
    resp = client.post(reverse("editor:item_undo", args=[restaurant.pk]), **HX)
    assert resp.status_code == 200
    assert category.items.count() == 2


# -- photos -------------------------------------------------------------------------------


@pytest.mark.django_db
def test_item_photo_upload_and_remove(client, restaurant, item):
    old = age(restaurant)
    url = reverse("editor:item_photo", args=[item.pk])
    resp = client.post(url, {"photo": make_image(size=(3000, 2000), name="big.png")}, **HX)
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.photo.name.endswith(".jpg")
    assert max(item.photo.width, item.photo.height) <= 1600
    assert f'id="thumb-{item.pk}"' in resp.content.decode()
    assert bumped(restaurant, old)

    resp = client.post(url, {"remove": "1"}, **HX)
    item.refresh_from_db()
    assert not item.photo
    assert resp.status_code == 200


@pytest.mark.django_db
def test_item_photo_rejects_garbage(client, item):
    from django.core.files.uploadedfile import SimpleUploadedFile

    resp = client.post(reverse("editor:item_photo", args=[item.pk]),
                       {"photo": SimpleUploadedFile("x.jpg", b"nope", content_type="image/jpeg")}, **HX)
    assert resp.status_code == 422
    item.refresh_from_db()
    assert not item.photo
    resp = client.post(reverse("editor:item_photo", args=[item.pk]), {}, **HX)
    assert resp.status_code == 422


# -- ordering -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_reorder_categories(client, restaurant, category, category2):
    old = age(restaurant)
    resp = client.post(reverse("editor:reorder_categories", args=[restaurant.pk]),
                       {"order": f"{category2.pk},{category.pk}"}, **HX)
    assert resp.status_code == 204
    assert [c.pk for c in restaurant.categories.all()] == [category2.pk, category.pk]
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_reorder_items_within_category(client, restaurant, category):
    a, b, c = (Item.objects.create(category=category, name={"fr": n}, position=i)
               for i, n in enumerate("ABC"))
    resp = client.post(reverse("editor:reorder_items", args=[restaurant.pk]),
                       {"category": category.pk, "order": f"{c.pk},{a.pk},{b.pk}"}, **HX)
    assert resp.status_code == 204
    assert [i.name["fr"] for i in category.items.all()] == ["C", "A", "B"]


@pytest.mark.django_db
def test_reorder_items_across_categories(client, restaurant, category, category2):
    a = Item.objects.create(category=category, name={"fr": "A"}, position=0)
    b = Item.objects.create(category=category, name={"fr": "B"}, position=1)
    x = Item.objects.create(category=category2, name={"fr": "X"}, position=0)
    old = age(restaurant)
    resp = client.post(reverse("editor:reorder_items", args=[restaurant.pk]),
                       {"category": category2.pk, "order": f"{x.pk},{a.pk}"}, **HX)
    assert resp.status_code == 204
    a.refresh_from_db()
    assert a.category_id == category2.pk
    assert [i.name["fr"] for i in category2.items.all()] == ["X", "A"]
    assert [i.name["fr"] for i in category.items.all()] == ["B"]
    assert b.category_id == category.pk
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_reorder_rejects_foreign_ids(client, restaurant, category):
    other = Restaurant.objects.create(name="Other")
    ocat = Category.objects.create(restaurant=other, name={"fr": "O"})
    oitem = Item.objects.create(category=ocat, name={"fr": "Foreign"})
    resp = client.post(reverse("editor:reorder_items", args=[restaurant.pk]),
                       {"category": category.pk, "order": str(oitem.pk)}, **HX)
    assert resp.status_code == 400
    oitem.refresh_from_db()
    assert oitem.category_id == ocat.pk
    resp = client.post(reverse("editor:reorder_items", args=[restaurant.pk]),
                       {"category": ocat.pk, "order": ""}, **HX)
    assert resp.status_code == 404
    resp = client.post(reverse("editor:reorder_categories", args=[restaurant.pk]),
                       {"order": f"{ocat.pk}"}, **HX)
    assert resp.status_code == 400
    resp = client.post(reverse("editor:reorder_items", args=[restaurant.pk]),
                       {"category": category.pk, "order": "1,x"}, **HX)
    assert resp.status_code == 400


# -- specials -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_special_crud_and_toggle(client, restaurant):
    old = age(restaurant)
    resp = client.post(reverse("editor:special_add", args=[restaurant.pk, "formule"]), **HX)
    assert resp.status_code == 200
    sp = restaurant.specials.get()
    assert sp.kind == "formule" and sp.is_active
    assert bumped(restaurant, old)
    assert client.post(reverse("editor:special_add", args=[restaurant.pk, "nonsense"]), **HX).status_code == 400

    old = age(restaurant)
    resp = client.post(
        reverse("editor:special_update", args=[sp.pk]),
        {
            "title_fr": "Formule midi", "title_en": "Lunch set",
            "description_fr": "Du mardi au vendredi",
            "price_label_fr": ["Entrée + plat", "Entrée + plat + dessert"],
            "price_label_en": ["Starter + main", ""],
            "price_amount": ["19,50", "23,90 €"],
            "kind": "formule",
        },
        **HX,
    )
    assert resp.status_code == 200
    sp.refresh_from_db()
    assert sp.title == {"fr": "Formule midi", "en": "Lunch set"}
    assert [p["cents"] for p in sp.prices] == [1950, 2390]
    assert sp.prices[0]["label"] == {"fr": "Entrée + plat", "en": "Starter + main"}
    assert bumped(restaurant, old)

    client.post(reverse("editor:special_toggle", args=[sp.pk]), **HX)
    sp.refresh_from_db()
    assert sp.is_active is False

    old = age(restaurant)
    client.post(reverse("editor:special_delete", args=[sp.pk]), **HX)
    assert not DailySpecial.objects.filter(pk=sp.pk).exists()
    assert bumped(restaurant, old)


@pytest.mark.django_db
def test_special_price_error(client, special):
    resp = client.post(reverse("editor:special_update", args=[special.pk]),
                       {"title_fr": "Nouveau", "price_amount": ["zzz"]}, **HX)
    special.refresh_from_db()
    assert special.prices == []
    assert special.title["fr"] == "Nouveau"
    assert "priceError" in json.loads(resp["HX-Trigger"])


@pytest.mark.django_db
def test_reorder_specials(client, restaurant):
    a = DailySpecial.objects.create(restaurant=restaurant, title={"fr": "a"}, position=0)
    b = DailySpecial.objects.create(restaurant=restaurant, title={"fr": "b"}, position=1)
    resp = client.post(reverse("editor:reorder_specials", args=[restaurant.pk]),
                       {"order": f"{b.pk},{a.pk}"}, **HX)
    assert resp.status_code == 204
    assert [s.pk for s in restaurant.specials.all()] == [b.pk, a.pk]


# -- translations counter -----------------------------------------------------------------


@pytest.mark.django_db
def test_missing_english_counter(client, restaurant, category, item, special):
    from editor.services import missing_english_count

    # category "Plats", item "Steak", special "Blanquette": all lack English
    assert missing_english_count(restaurant) == 3
    client.post(reverse("editor:item_update", args=[item.pk]), {"name_en": "Steak"}, **HX)
    assert missing_english_count(restaurant) == 2
    resp = client.post(reverse("editor:item_update", args=[item.pk]), {"description_fr": "Bon"}, **HX)
    assert "missing English" in resp.content.decode()
    assert missing_english_count(restaurant) == 3  # description now needs a translation
