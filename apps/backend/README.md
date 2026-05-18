# Datafeeder Backend

REST API for Datafeeder, built with FastAPI.

It exposes the endpoints used by the frontend and orchestrates ingestion by triggering Airflow DAGs and persisting their results in the database.

## Layout

```
src/
  api/        # HTTP routes (no business logic)
  services/   # Business logic
  models/     # SQLModel entities
  core/       # Config, db session, security, utilities
  plugins/    # Optional integrations (GeoServer, GeoNetwork)
  main.py     # FastAPI app entry point
alembic/      # Migrations
tests/        # Pytest suite
```

Architecture rule: `api → services → models/core` (down only). Routes contain no business logic.

## Install

From the repository root:

```bash
uv sync --all-packages
```

## Run

```bash
make run-backend
# or, for a Docker-only setup
make up-light
```

The API is then available at:

- http://localhost:8000/ (direct)
- http://localhost:8080/datafeeder-backend/ (through the geOrchestra gateway)
- http://localhost:8000/docs — interactive OpenAPI docs

## Test

```bash
make test-backend            # run pytest
make test-backend-coverage   # with coverage report
```

## Database migrations

```bash
cd apps/backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Lint & type-check

From the repository root:

```bash
make fix-and-check-all-python    # ruff + format fixes
```
