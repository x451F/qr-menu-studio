"""Content version helpers.

The content version of a restaurant is ``Restaurant.updated_at``; it is bumped by
``Restaurant.save()`` and, for children, by the signal handlers in ``signals.py``.
The public view uses it (with language/theme/mode) as the page-cache key and ETag.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .models import Restaurant


def touch_restaurant(restaurant_id) -> None:
    """Bump the content version of a restaurant (no-op when it does not exist / is being deleted)."""
    if restaurant_id:
        Restaurant(pk=restaurant_id).touch()


def version_token(restaurant) -> str:
    """Microsecond timestamp of the content version."""
    ts = restaurant.updated_at
    return f"{int(ts.timestamp())}{ts.microsecond:06d}"


@lru_cache(maxsize=1)
def code_version() -> str:
    """Fingerprint of the code that renders the public page (templates + view code).

    Included in cache keys and ETags so that a deploy invalidates browser caches.
    Computed once per process from file sizes and mtimes.
    """
    base = Path(settings.BASE_DIR)
    parts = []
    roots = [base / "templates" / "public", base / "public"]
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in {".html", ".py", ".txt", ".css", ".js"}:
                st = path.stat()
                parts.append(f"{path.relative_to(base)}:{st.st_size}:{int(st.st_mtime)}")
    manifest = Path(settings.STATIC_ROOT) / "staticfiles.json"
    if manifest.exists():
        st = manifest.stat()
        parts.append(f"manifest:{st.st_size}:{int(st.st_mtime)}")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def page_cache_key(restaurant, lang: str, theme: str, mode: str) -> str:
    return f"menu:{code_version()}:{restaurant.id}:{version_token(restaurant)}:{lang}:{theme}:{mode}"


def make_etag(restaurant, lang: str, theme: str, mode: str) -> str:
    raw = page_cache_key(restaurant, lang, theme, mode)
    return '"' + hashlib.sha1(raw.encode()).hexdigest()[:24] + '"'
