# syntax=docker/dockerfile:1.7
# Build context: apps/api

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# --- deps + project into a venv (cached separately from source changes) ---------------
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# --- slim runtime: venv + migrations only, non-root ----------------------------------
FROM base AS runtime
RUN useradd --create-home --uid 1000 app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8000\")}/health')"
# PORT is honoured for PaaS hosts (Heroku/Render) that inject it.
CMD ["sh", "-c", "exec uvicorn windsight.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --no-access-log"]
