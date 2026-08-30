"""Create demo restaurants (idempotent: demo restaurants are rebuilt by slug; others are untouched).

    python manage.py seed_demo [--admin-password PASSWORD] [--if-empty]

Photos and logos from menus/seed_assets/ go through the same pipeline as real uploads
(`process_photo` / `process_logo`), so WebP variants are generated too.
"""

import os
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from menus.formatting import parse_price
from menus.images import process_logo, process_photo
from menus.management.commands.create_admin import ensure_admin
from menus.models import Category, DailySpecial, Item, Restaurant
from menus.seed_data import DEMO_RESTAURANTS, LOGOS, photo_for

ASSETS = Path(__file__).resolve().parents[2] / "seed_assets"


def _tr(pair):
    fr, en = pair if isinstance(pair, tuple) else (pair, "")
    return {"fr": fr, "en": en}


def _prices(rows):
    return [
        ({"label": {"fr": lf, "en": le}} if lf else {}) | {"cents": parse_price(amount)}
        for lf, le, amount in rows
    ]


def _upload(path: Path, processor):
    with path.open("rb") as fh:
        return processor(ContentFile(fh.read(), name=path.name), path.name)


class Command(BaseCommand):
    help = "Seed demo restaurants (one per theme) with realistic French menus, photos and logos."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", ""))
        parser.add_argument("--admin-username", default=os.environ.get("ADMIN_USERNAME", "admin"))
        parser.add_argument(
            "--if-empty", action="store_true", help="Only seed when there are no restaurants at all."
        )

    def handle(self, *args, **opts):
        if opts["if_empty"] and Restaurant.objects.exists():
            self.stdout.write("Restaurants already exist; skipping demo data (--if-empty).")
        else:
            self._seed()
        if opts["admin_password"]:
            user, created = ensure_admin(opts["admin_username"], opts["admin_password"])
            self.stdout.write(f"  admin user '{user.username}' {'created' if created else 'updated'}")

    @transaction.atomic
    def _seed(self):
        for data in DEMO_RESTAURANTS:
            Restaurant.objects.filter(slug=data["slug"]).delete()  # signals remove old files
            r = Restaurant.objects.create(
                name=data["name"],
                slug=data["slug"],
                tagline=_tr(data["tagline"]),
                theme=data["theme"],
                color_mode=data.get("color_mode", "auto"),
                brand_color=data["brand_color"],
                accent_color=data.get("accent_color", ""),
                address=data["address"],
                phone=data["phone"],
                hours=_tr(data["hours"]),
                footer_note=_tr(data["footer_note"]),
                languages=data.get("languages", ["fr", "en"]),
                is_published=True,
            )
            logo = LOGOS.get(data["slug"])
            if logo:
                r.logo.save(logo, _upload(ASSETS / "logos" / logo, process_logo), save=True)
            for pos, (kind, t_fr, t_en, d_fr, d_en, prices) in enumerate(data["specials"]):
                DailySpecial.objects.create(
                    restaurant=r, kind=kind, title={"fr": t_fr, "en": t_en},
                    description={"fr": d_fr, "en": d_en}, prices=_prices(prices), position=pos,
                )
            photos = 0
            for cpos, (c_fr, c_en, cd_fr, cd_en, items) in enumerate(data["categories"]):
                cat = Category.objects.create(
                    restaurant=r, name={"fr": c_fr, "en": c_en}, description={"fr": cd_fr, "en": cd_en}, position=cpos
                )
                for ipos, (n_fr, n_en, d_fr, d_en, prices, allergens, diets, flags) in enumerate(items):
                    it = Item.objects.create(
                        category=cat, name={"fr": n_fr, "en": n_en}, description={"fr": d_fr, "en": d_en},
                        prices=_prices(prices), allergens=allergens, diets=diets,
                        is_sold_out="sold_out" in flags, position=ipos,
                    )
                    stem = photo_for(data["slug"], n_fr, flags)
                    if stem:
                        path = ASSETS / "photos" / f"{stem}.jpg"
                        it.photo.save(path.name, _upload(path, process_photo), save=True)
                        photos += 1
            n_items = Item.objects.filter(category__restaurant=r).count()
            self.stdout.write(
                f"  {r.name} [{r.theme}]: {n_items} items, {photos} photos, "
                f"{'logo' if logo else 'no logo'} -> {r.public_path}"
            )
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
