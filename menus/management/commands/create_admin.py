"""Create or update the admin (staff + superuser) account.

    python manage.py create_admin [--username admin] [--password ...]

Defaults come from ADMIN_USERNAME / ADMIN_PASSWORD. Does nothing (exit 0) without a password.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


def ensure_admin(username: str, password: str):
    """Create/update the admin user. Returns (user, created)."""
    User = get_user_model()
    user, created = User.objects.get_or_create(username=username)
    user.is_staff = user.is_superuser = True
    user.is_active = True
    user.set_password(password)
    user.save()
    return user, created


class Command(BaseCommand):
    help = "Create or update the admin account from --password or ADMIN_PASSWORD."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME", "admin"))
        parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", ""))

    def handle(self, *args, **opts):
        if not opts["password"]:
            self.stdout.write("No ADMIN_PASSWORD given; admin account left untouched.")
            return
        user, created = ensure_admin(opts["username"], opts["password"])
        self.stdout.write(f"Admin user '{user.username}' {'created' if created else 'updated'}.")
