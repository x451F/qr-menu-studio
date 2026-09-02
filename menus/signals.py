"""Signal wiring: content version bumps and image file lifecycle.

* Category / Item / DailySpecial saved or deleted -> ``Restaurant.updated_at`` is bumped
  (invalidates the public page cache and ETag).
* Item photo replaced / cleared / Item deleted -> old file and WebP variants are removed.
* Restaurant logo replaced / cleared / Restaurant deleted -> old logo file is removed.
"""

from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .cache import touch_restaurant
from .images import delete_with_variants, ensure_variants
from .models import Category, DailySpecial, Item, Restaurant

_UNSET = object()


def _raw_name(instance, field: str):
    """Current stored file name without triggering a deferred-field query."""
    if field not in instance.__dict__:
        return _UNSET
    value = instance.__dict__[field]
    return getattr(value, "name", value) or ""


# -- content version ---------------------------------------------------------------------
@receiver([post_save, post_delete], sender=Category, dispatch_uid="menus.touch.category")
def _touch_for_category(sender, instance, **kwargs):
    touch_restaurant(instance.restaurant_id)


@receiver([post_save, post_delete], sender=DailySpecial, dispatch_uid="menus.touch.special")
def _touch_for_special(sender, instance, **kwargs):
    touch_restaurant(instance.restaurant_id)


@receiver([post_save, post_delete], sender=Item, dispatch_uid="menus.touch.item")
def _touch_for_item(sender, instance, **kwargs):
    restaurant_id = (
        Category.objects.filter(pk=instance.category_id).values_list("restaurant_id", flat=True).first()
    )
    touch_restaurant(restaurant_id)


# -- item photos -------------------------------------------------------------------------
@receiver(post_init, sender=Item, dispatch_uid="menus.photo.init")
def _remember_photo(sender, instance, **kwargs):
    instance._orig_photo = _raw_name(instance, "photo")


@receiver(post_save, sender=Item, dispatch_uid="menus.photo.save")
def _photo_saved(sender, instance, **kwargs):
    old = getattr(instance, "_orig_photo", _UNSET)
    new = _raw_name(instance, "photo")
    if new is _UNSET:
        return
    if old is not _UNSET and old and old != new:
        delete_with_variants(instance.photo.storage, old)
    if new and new != old:
        ensure_variants(instance.photo)
    instance._orig_photo = new


@receiver(post_delete, sender=Item, dispatch_uid="menus.photo.delete")
def _photo_deleted(sender, instance, **kwargs):
    name = _raw_name(instance, "photo")
    if name and name is not _UNSET:
        delete_with_variants(instance.photo.storage, name)


# -- restaurant logos --------------------------------------------------------------------
@receiver(post_init, sender=Restaurant, dispatch_uid="menus.logo.init")
def _remember_logo(sender, instance, **kwargs):
    instance._orig_logo = _raw_name(instance, "logo")


@receiver(post_save, sender=Restaurant, dispatch_uid="menus.logo.save")
def _logo_saved(sender, instance, **kwargs):
    old = getattr(instance, "_orig_logo", _UNSET)
    new = _raw_name(instance, "logo")
    if new is _UNSET:
        return
    if old is not _UNSET and old and old != new:
        delete_with_variants(instance.logo.storage, old)
    instance._orig_logo = new


@receiver(post_delete, sender=Restaurant, dispatch_uid="menus.logo.delete")
def _logo_deleted(sender, instance, **kwargs):
    name = _raw_name(instance, "logo")
    if name and name is not _UNSET:
        delete_with_variants(instance.logo.storage, name)
