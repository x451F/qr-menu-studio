import time

import pytest

from menus.models import Category, DailySpecial, Item, Restaurant
from menus.tests.factories import make_menu, make_restaurant


def _version(restaurant):
    return Restaurant.objects.values_list("updated_at", flat=True).get(pk=restaurant.pk)


@pytest.mark.django_db
def test_child_changes_bump_restaurant_version():
    restaurant, cat, items = make_menu()
    special = restaurant.specials.first()

    def bumped(action):
        before = _version(restaurant)
        time.sleep(0.002)
        action()
        after = _version(restaurant)
        assert after > before

    bumped(lambda: Item.objects.create(category=cat, name={"fr": "Nouveau"}))
    items[0].is_sold_out = True
    bumped(items[0].save)
    bumped(items[1].delete)
    bumped(lambda: Category.objects.create(restaurant=restaurant, name={"fr": "Desserts"}))
    cat.is_visible = False
    bumped(cat.save)
    special.is_active = False
    bumped(special.save)
    bumped(lambda: DailySpecial.objects.create(restaurant=restaurant, title={"fr": "X"}))
    bumped(special.delete)


@pytest.mark.django_db
def test_bump_only_affects_own_restaurant():
    a, cat_a, items_a = make_menu(make_restaurant("Alpha"))
    b, _, _ = make_menu(make_restaurant("Beta"))
    before_b = _version(b)
    items_a[0].is_sold_out = True
    items_a[0].save()
    assert _version(b) == before_b


@pytest.mark.django_db
def test_deleting_restaurant_with_children_does_not_error():
    restaurant, _, _ = make_menu()
    restaurant.delete()
    assert not Restaurant.objects.exists()
    assert not Item.objects.exists()
