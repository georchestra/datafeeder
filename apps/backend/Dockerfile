# syntax=docker/dockerfile:1
ARG UV_VERSION=0.12.4
ARG PYTHON_VERSION=3.13
# Base of the `production-local` target (GDAL >= 3.13 isn't packaged by Debian).
# ubuntu-small rather than ubuntu-full (~400 MB vs ~2.5 GB): it has the PostgreSQL
# driver, and the only missing one, Parquet, is built as a plugin below.
ARG GDAL_VERSION=3.13.2
ARG GDAL_IMAGE=ghcr.io/osgeo/gdal:ubuntu-small-${GDAL_VERSION}

# Named stage for the uv binary so later `COPY --from=uv` works on BuildKit
# versions that don't support variable expansion in `--from`.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ============================================================================
# Base stage: Common setup for all targets
# ============================================================================
FROM python:3.13-slim AS base

# Install required dependencies with APT
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=uv /uv /uvx /bin/

# - Silence uv complaining about not being able to use hard links,
# - tell uv to byte-compile packages for faster application startups,
# - prevent uv from accidentally downloading isolated Python builds,
# - pick a Python (use `/usr/bin/python3.13` on uv 0.5.0 and later),
# - declare `/app` as the target for `uv sync`.
# - declare a cache directory for uv to use
# - disable uv caching to ensure fresh installs in CI/CD environments
# - enable frozen installs to ensure reproducible builds
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python3.13 \
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


# ============================================================================
FROM ${GDAL_IMAGE} AS gdal-parquet-plugin
ARG GDAL_VERSION

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    build-essential cmake curl ca-certificates libarrow-dev libparquet-dev

RUN curl -fsSL https://github.com/OSGeo/gdal/releases/download/v${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz \
        | tar xz -C /tmp && \
    cmake -S /tmp/gdal-${GDAL_VERSION}/ogr/ogrsf_frmts/parquet -B /tmp/build \
        -DCMAKE_BUILD_TYPE=Release && \
    cmake --build /tmp/build -j"$(nproc)" && \
    mkdir /plugins && cp /tmp/build/ogr_Parquet.so /plugins/

# ============================================================================
# Production stage for TASK_EXECUTOR=LOCAL: staging/processing run inside the
# backend process, so ogr2ogr must be on PATH. Built on the GDAL image rather
# than python:slim, with the interpreter fetched by uv.
# Ubuntu-small plus the Parquet plugin built above.
# ============================================================================
FROM ${GDAL_IMAGE} AS local-executor
ARG PYTHON_VERSION

COPY --from=uv /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=manual \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON=${PYTHON_VERSION} \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_NO_CACHE=1 \
    UV_FROZEN=1

# git: uv resolves the geoservercloud dependency from a git URL.
# libarrow/libparquet: runtime of the Parquet plugin, whose major version must
# match the libarrow-dev it was built with.
RUN --mount=type=bind,from=gdal-parquet-plugin,source=/plugins,target=/plugins \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends git curl libarrow2300 libparquet2300 && \
    rm -rf /var/lib/apt/lists/* && \
    cp /plugins/ogr_Parquet.so "$(gdal-config --plugindir)/"

# Ubuntu (the GDAL image's base) doesn't package the pinned Python version.
# Installed outside /root so the non-root user can read it.
RUN uv python install ${PYTHON_VERSION} && \
    chmod -R a+rX /opt/python
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

ARG UID=10000
ARG GID=10001
RUN groupadd --gid ${GID} georchestra_user && \
    useradd georchestra_user --uid ${UID} --gid ${GID} --home-dir /app \
        --shell /bin/sh --no-create-home

COPY pyproject.toml uv.lock ./
COPY libs/data_manipulation ./libs/data_manipulation
COPY apps/backend ./apps/backend

# chown in the same layer as the sync, so the venv isn't stored twice.
RUN uv sync --no-dev --package datafeeder-backend && \
    chown -R georchestra_user:georchestra_user /app
USER georchestra_user

# ogr2ogr is local: no docker exec wrapper.
ENV TASK_EXECUTOR=LOCAL \
    BACKEND_INTERNAL_URL=http://localhost:8000 \
    DATAFEEDER_GDAL_DOCKER_EXEC_TARGET=""

WORKDIR /app/apps/backend
EXPOSE 8000

CMD ["sh", "-c", "/app/.venv/bin/alembic upgrade head && exec /app/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000"]
