"""Settings for pytest: dev defaults (insecure local key), isolated data dir."""

import os
import tempfile

os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="qrmenu-test-"))

from .settings import *  # noqa: E402, F403
