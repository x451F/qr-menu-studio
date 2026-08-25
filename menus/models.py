from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .constants import ALLERGENS, COLOR_MODES, DEFAULT_THEME, DIETS, SPECIAL_KINDS, THEMES
from .formatting import format_prices
from .i18n import tr

hex_color = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a hex colour like #7a2e2a.")


def tr_default():
    return {"fr": "", "en": ""}


def default_languages():
    return ["fr", "en"]


def upload_logo_to(instance, filename):
    return f"logos/{instance.slug or 'new'}/{filename}"


def upload_photo_to(instance, filename):
    return f"photos/{instance.category.restaurant_id}/{filename}"


class Restaurant(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    tagline = models.JSONField(default=tr_default, blank=True)
    logo = models.ImageField(upload_to=upload_logo_to, blank=True)

    brand_color = models.CharField(max_length=7, default="#7a2e2a", validators=[hex_color])
    accent_color = models.CharField(max_length=7, blank=True, validators=[hex_color])
    theme = models.CharField(max_length=20, choices=[(k, v["label"]) for k, v in THEMES.items()], default=DEFAULT_THEME)
    color_mode = models.CharField(max_length=10, choices=list(COLOR_MODES.items()), default="auto")

    address = models.TextField(blank=True)
    maps_url = models.URLField(blank=True, help_text="Optional; defaults to a map search for the address.")
    phone = models.CharField(max_length=30, blank=True)
    hours = models.JSONField(default=tr_default, blank=True, help_text="Multi-line text per language.")
    footer_note = models.JSONField(default=tr_default, blank=True)
    languages = models.JSONField(default=default_languages)

    is_published = models.BooleanField(default=False)
    first_published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, help_text="Content version; bumped on any change.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    # -- slug is the permanent QR target -------------------------------------------------
    def slug_is_locked(self) -> bool:
        return self.first_published_at is not None

    def _unique_slug(self) -> str:
        base = slugify(self.name)[:70] or "menu"
        slug, n = base, 2
        while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def clean(self):
        if self.pk:
            old = Restaurant.objects.filter(pk=self.pk).values("slug", "first_published_at").first()
            if old and old["first_published_at"] and old["slug"] != self.slug:
                raise ValidationError({"slug": "The address of a published menu can never change (printed QR codes point to it)."})

    def save(self, *args, **kwargs):
        if self.pk:
            old = Restaurant.objects.filter(pk=self.pk).values("slug", "first_published_at").first()
            if old and old["first_published_at"]:
                self.slug = old["slug"]  # hard guarantee: never change a published slug
        if not self.slug:
            self.slug = self._unique_slug()
        else:
            self.slug = slugify(self.slug)[:80] or self._unique_slug()
        if self.is_published and not self.first_published_at:
            self.first_published_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def touch(self):
        """Bump the content version (call after changing categories/items/specials)."""
        self.updated_at = timezone.now()
        Restaurant.objects.filter(pk=self.pk).update(updated_at=self.updated_at)

    # -- helpers --------------------------------------------------------------------------
    @property
    def public_path(self) -> str:
        return reverse("public:menu", args=[self.slug])

    @property
    def public_url(self) -> str:
        return settings.PUBLIC_BASE_URL + self.public_path

    @property
    def maps_link(self) -> str:
        if self.maps_url:
            return self.maps_url
        if not self.address:
            return ""
        from urllib.parse import quote

        return "https://www.google.com/maps/search/?api=1&query=" + quote(" ".join(self.address.split()))

    @property
    def phone_href(self) -> str:
        digits = "".join(ch for ch in self.phone if ch.isdigit() or ch == "+")
        if digits.startswith("0") and len(digits) == 10:
            digits = "+33" + digits[1:]
        return f"tel:{digits}" if digits else ""

    def enabled_languages(self) -> list[str]:
        langs = [lang for lang in (self.languages or []) if lang in ("fr", "en")]
        if "fr" not in langs:
            langs.insert(0, "fr")
        return langs


class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="categories")
    name = models.JSONField(default=tr_default)
    description = models.JSONField(default=tr_default, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "id"]
        verbose_name_plural = "categories"

    def __str__(self):
        return tr(self.name) or f"Category {self.pk}"


def validate_prices(value):
    if not isinstance(value, list):
        raise ValidationError("Prices must be a list.")
    for p in value:
        if not isinstance(p, dict) or not isinstance(p.get("cents"), int) or p["cents"] < 0:
            raise ValidationError("Each price needs integer 'cents' >= 0.")


def _validate_codes(value, allowed):
    if not isinstance(value, list) or any(code not in allowed for code in value):
        raise ValidationError(f"Unknown code in {value!r}")


def validate_allergens(value):
    _validate_codes(value, ALLERGENS)


def validate_diets(value):
    _validate_codes(value, DIETS)


class Item(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.JSONField(default=tr_default)
    description = models.JSONField(default=tr_default, blank=True)
    prices = models.JSONField(default=list, blank=True, validators=[validate_prices])
    photo = models.ImageField(upload_to=upload_photo_to, blank=True)
    allergens = models.JSONField(default=list, blank=True, validators=[validate_allergens])
    diets = models.JSONField(default=list, blank=True, validators=[validate_diets])
    is_sold_out = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return tr(self.name) or f"Item {self.pk}"

    def price_display(self, lang="fr") -> str:
        return format_prices(self.prices, lang)


class DailySpecial(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="specials")
    kind = models.CharField(max_length=20, choices=[(k, v["fr"]) for k, v in SPECIAL_KINDS.items()], default="plat")
    title = models.JSONField(default=tr_default)
    description = models.JSONField(default=tr_default, blank=True)
    prices = models.JSONField(default=list, blank=True, validators=[validate_prices])
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"{SPECIAL_KINDS[self.kind]['fr']}: {tr(self.title)}"
