from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from menus.models import Restaurant

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def fake_ai(settings):
    settings.AI_FAKE = True
    settings.AI_ENABLED = True
    return settings


@pytest.fixture
def no_ai(settings):
    settings.AI_FAKE = False
    settings.ANTHROPIC_API_KEY = ""
    settings.AI_ENABLED = False
    return settings


@pytest.fixture
def real_ai(settings):
    """Real-API code path (client is mocked by the tests); key is a dummy value."""
    settings.AI_FAKE = False
    settings.ANTHROPIC_API_KEY = "test-key-not-real"
    settings.AI_ENABLED = True
    settings.ANTHROPIC_MODEL = "claude-opus-5-5"
    return settings


@pytest.fixture
def sample_jpeg() -> bytes:
    return (FIXTURES / "sample_menu.jpg").read_bytes()


@pytest.fixture
def restaurant(db):
    return Restaurant.objects.create(name="Chez Test")


@pytest.fixture
def staff_client(client, db):
    user = get_user_model().objects.create_user("staff", password="pw-for-tests-123", is_staff=True)
    client.force_login(user)
    return client
