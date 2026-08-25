"""Create demo restaurants (idempotent: existing demo restaurants are rebuilt).

    python manage.py seed_demo [--admin-password PASSWORD]
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from menus.formatting import parse_price
from menus.models import Category, DailySpecial, Item, Restaurant
from menus.seed_data import DEMO_RESTAURANTS


def _tr(pair):
    fr, en = pair if isinstance(pair, tuple) else (pair, "")
    return {"fr": fr, "en": en}


def _prices(rows):
    return [
        ({"label": {"fr": lf, "en": le}} if lf else {}) | {"cents": parse_price(amount)}
        for lf, le, amount in rows
    ]


class Command(BaseCommand):
    help = "Seed demo restaurants with realistic French menus."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", ""))
        parser.add_argument("--admin-username", default=os.environ.get("ADMIN_USERNAME", "admin"))

    @transaction.atomic
    def handle(self, *args, **opts):
        for data in DEMO_RESTAURANTS:
            Restaurant.objects.filter(slug=data["slug"]).delete()
            r = Restaurant.objects.create(
                name=data["name"],
                slug=data["slug"],
                tagline=_tr(data["tagline"]),
                theme=data["theme"],
                brand_color=data["brand_color"],
                accent_color=data.get("accent_color", ""),
                address=data["address"],
                phone=data["phone"],
                hours=_tr(data["hours"]),
                footer_note=_tr(data["footer_note"]),
                is_published=True,
            )
            for pos, (kind, t_fr, t_en, d_fr, d_en, prices) in enumerate(data["specials"]):
                DailySpecial.objects.create(
                    restaurant=r, kind=kind, title={"fr": t_fr, "en": t_en},
                    description={"fr": d_fr, "en": d_en}, prices=_prices(prices), position=pos,
                )
            for cpos, (c_fr, c_en, cd_fr, cd_en, items) in enumerate(data["categories"]):
                cat = Category.objects.create(
                    restaurant=r, name={"fr": c_fr, "en": c_en}, description={"fr": cd_fr, "en": cd_en}, position=cpos
                )
                for ipos, (n_fr, n_en, d_fr, d_en, prices, allergens, diets, flags) in enumerate(items):
                    Item.objects.create(
                        category=cat, name={"fr": n_fr, "en": n_en}, description={"fr": d_fr, "en": d_en},
                        prices=_prices(prices), allergens=allergens, diets=diets,
                        is_sold_out="sold_out" in flags, position=ipos,
                    )
            self.stdout.write(f"  {r.name}: {r.public_path}")

        password = opts["admin_password"]
        if password:
            User = get_user_model()
            user, _ = User.objects.get_or_create(username=opts["admin_username"])
            user.is_staff = user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(f"  admin user '{user.username}' ready")
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
