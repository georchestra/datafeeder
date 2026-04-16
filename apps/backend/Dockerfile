# syntax=docker/dockerfile:1

# ============================================================================
# Base stage: Common setup for all targets
# ============================================================================
FROM python:3.12-slim AS base

# Install required dependencies with APT
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.15 /uv /uvx /bin/

# - Silence uv complaining about not being able to use hard links,
# - tell uv to byte-compile packages for faster application startups,
# - prevent uv from accidentally downloading isolated Python builds,
# - pick a Python (use `/usr/bin/python3.12` on uv 0.5.0 and later),
# - declare `/app` as the target for `uv sync`.
# - declare a cache directory for uv to use
# - disable uv caching to ensure fresh installs in CI/CD environments
# - enable frozen installs to ensure reproducible builds
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.12 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_NO_CACHE=1 \
    UV_FROZEN=1

# ============================================================================
# Development stage: Full environment with dev dependencies
# ============================================================================
FROM base AS development

WORKDIR /app

# Copy workspace configuration and libs
COPY pyproject.toml uv.lock ./
COPY libs/data_manipulation ./libs/data_manipulation
COPY apps/backend ./apps/backend

# Install dependencies from root of workspace (editable for hot-reload)
RUN uv sync --editable

WORKDIR /app/apps/backend
EXPOSE 8000

# Run migrations then start with hot-reload
CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app"]

# ============================================================================
# Production stage: Minimal image without dev dependencies
# ============================================================================
FROM base AS production

WORKDIR /app

# Create non-root user
ARG UID=10000
ARG GID=10001
RUN addgroup --gid ${GID} georchestra_user && \
    adduser georchestra_user --uid ${UID} --disabled-password --home /app \
        --shell /bin/sh --ingroup georchestra_user

# Copy workspace configuration and libs
COPY pyproject.toml uv.lock ./
COPY libs/data_manipulation ./libs/data_manipulation
COPY apps/backend ./apps/backend

# Install production dependencies only, from root of workspace
# Install all workspace members (backend and its dependencies) without dev dependencies
RUN uv sync --no-dev --package datafeeder-backend

RUN chown -R georchestra_user:georchestra_user /app
USER georchestra_user

WORKDIR /app/apps/backend
EXPOSE 8000

# Run migrations then start the server
CMD ["sh", "-c", "/app/.venv/bin/alembic upgrade head && exec /app/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000"]
