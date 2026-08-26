import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolated_media_and_cache(settings, tmp_path):
    """Every test gets its own MEDIA_ROOT and an empty cache."""
    settings.MEDIA_ROOT = tmp_path / "media"
    cache.clear()
    yield
    cache.clear()
