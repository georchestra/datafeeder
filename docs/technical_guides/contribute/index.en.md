# Contribute

Datafeeder is a monorepo: a FastAPI backend, an Angular frontend, Airflow ELT DAGs, and shared Python libraries,
managed together with `uv` (Python workspace) and `npm`/`nx` (frontend).

See also the [Architecture](architecture.md) page for how the pieces fit together.

## Setting up a dev environment

See the [prerequisites](../installation/prerequisites.md) and [quick-start](../installation/quickstart.md) pages.
In short:

```bash
make install-python   # installs Python deps via uv, writes AIRFLOW_UID into .env
make up                # backend deps + docker compose (georchestra, airflow, geoserver, geonetwork)
make run-backend       # backend, with auto-reload
cd apps/frontend && npm install && npm start
```

`make help` lists every available target.

## Running the tests

```bash
make test-libs             # libs/data_manipulation, pytest
make test-backend          # apps/backend, pytest
make test-backend-coverage # apps/backend, pytest with html/term coverage report
```

Frontend tests (from `apps/frontend/`):

```bash
npm run test:ut      # unit tests (Vitest)
npm run test:e2e     # end-to-end tests (Cypress)
npm run test:e2e:ci  # headless mode, used by CI
```

## Linting and formatting

```bash
make fix-and-check-all-python   # ruff lint --fix, format, then check --verbose
```

Frontend formatting/linting is run via `npm run format` (see `apps/frontend/package.json`).

## Keeping the frontend API client in sync

The frontend's TypeScript API client is generated from the backend's OpenAPI schema and is **not** hand-written.
Any change to a backend route or model must be followed by regenerating it — see
[Regenerating the API client](../configuration/frontend.md#regenerating-the-api-client).

## AI agent skills

This repository ships domain-specific instructions for AI coding agents under `.agents/skills/` (Airflow DAGs,
Angular components, FastAPI endpoints, frontend/API sync, geospatial data handling, Figma-to-code, Tailwind design
systems). `agents.md` at the repository root is the entry point.
