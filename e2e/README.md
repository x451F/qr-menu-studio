# End-to-end tests

Playwright (Python) against a real server. The `server` fixture creates a temp `DATA_DIR`, runs
`migrate` + `create_admin`, and starts `runserver 127.0.0.1:8010 --noreload` with `DJANGO_DEBUG=1`,
`AI_FAKE=1`, `PUBLIC_BASE_URL=http://127.0.0.1:8010`; it is stopped and deleted at the end.

```bash
uv run playwright install chromium     # once (optional: fixtures fall back to any chromium in
                                       # ~/Library/Caches/ms-playwright if versions don't match)
uv run pytest e2e                      # port 8010 must be free
uv run pytest e2e -k main_flow         # just the main flow (375 px and 1280 px)
```

`testpaths` in pyproject does not include `e2e`, so always pass the path.
QR codes are decoded with `zxing-cpp` (dev dependency) and compared with the public URL.
Known app bugs are marked `xfail` with their id (see `docs/qa/`).
