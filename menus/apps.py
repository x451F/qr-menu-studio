from django.apps import AppConfig


class MenusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "menus"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
