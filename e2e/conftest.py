"""E2E fixtures: a real Django server on 127.0.0.1:8010 with a throwaway DATA_DIR, plus Playwright.

Run with ``uv run pytest e2e`` (see e2e/README.md).
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8010
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_USER = "qa-admin"
ADMIN_PASS = "qa-password-12345"
SAMPLE_MENU = ROOT / "ai" / "fixtures" / "sample_menu.jpg"


def _server_env(data_dir: str, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "AI_FAKE")}
    env.update(
        DATA_DIR=data_dir,
        DJANGO_DEBUG="1",
        AI_FAKE="1",
        PUBLIC_BASE_URL=BASE,
        ADMIN_USERNAME=ADMIN_USER,
        ADMIN_PASSWORD=ADMIN_PASS,
        DJANGO_SETTINGS_MODULE="config.settings",
        PYTHONUNBUFFERED="1",
    )
    env.update(extra)
    return env


def _manage(env, *args):
    subprocess.run(
        [sys.executable, "manage.py", *args], cwd=ROOT, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


@pytest.fixture(scope="session")
def server():
    data_dir = tempfile.mkdtemp(prefix="qrmenu-e2e-")
    env = _server_env(data_dir)
    _manage(env, "migrate", "--noinput")
    _manage(env, "create_admin")
    log = open(Path(data_dir) / "server.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 40
        while True:
            try:
                if urllib.request.urlopen(f"{BASE}/healthz", timeout=2).status == 200:
                    break
            except Exception:
                if proc.poll() is not None:
                    raise RuntimeError(Path(data_dir, "server.log").read_text()) from None
                if time.time() > deadline:
                    raise RuntimeError("server did not start") from None
                time.sleep(0.2)
        yield BASE
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
        shutil.rmtree(data_dir, ignore_errors=True)


def _chromium_paths():
    base = os.path.expanduser("~/Library/Caches/ms-playwright")
    pats = [
        f"{base}/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
        f"{base}/chromium_headless_shell-*/chrome-*/headless_shell",
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]
    found = []
    for p in pats:
        found += sorted(glob.glob(p), reverse=True)
    return found


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception:
            b = None
            for path in _chromium_paths():
                try:
                    b = pw.chromium.launch(executable_path=path)
                    break
                except Exception:
                    continue
            if b is None:
                raise
        yield b
        b.close()


@pytest.fixture
def make_context(browser, server):
    """Factory: make_context(width=375) -> fresh BrowserContext (own cookies)."""
    created = []

    def factory(width=375, height=None, **kw):
        ctx = browser.new_context(
            viewport={"width": width, "height": height or (800 if width < 600 else 900)},
            base_url=BASE,
            **kw,
        )
        ctx.set_default_timeout(15000)
        created.append(ctx)
        return ctx

    yield factory
    for c in created:
        c.close()


def login(page, username=ADMIN_USER, password=ADMIN_PASS):
    page.goto("/admin/login/")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.click("button[type=submit]")
    page.wait_for_url("**/admin/")


@pytest.fixture
def admin_ctx(make_context):
    ctx = make_context(375)
    login(ctx.new_page())
    return ctx


@pytest.fixture
def make_restaurant(admin_ctx):
    """Create a restaurant through the UI; returns (pk, page)."""

    def factory(name):
        page = admin_ctx.new_page()
        page.goto("/admin/r/new/")
        page.fill("input[name=name]", name)
        page.click("text=Create and add dishes")
        page.wait_for_url("**/admin/r/*/")
        pk = int(page.url.rstrip("/").rsplit("/", 1)[1])
        return pk, page

    return factory
