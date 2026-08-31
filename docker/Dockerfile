# syntax=docker/dockerfile:1
# Build context is the repository root (see docker-compose.yml).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    DATA_DIR=/data

# WeasyPrint 66 needs pango + harfbuzz (+ fontconfig, pulled in by pango) and some fonts for PDFs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
      fontconfig fonts-dejavu-core fonts-liberation2 shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app

# Dependencies first (cached unless pyproject.toml / uv.lock change).
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Non-root user; /data holds db.sqlite3, media/ and backups/ (a named volume in compose).
RUN useradd --system --uid 1000 --create-home app \
 && mkdir -p /data \
 && DJANGO_SECRET_KEY=build-only-dummy-secret DATA_DIR=/tmp/build-data \
      python manage.py collectstatic --noinput \
 && chown -R app:app /data /app/staticfiles

USER app
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
