# DataFeeder

Data-ingestion & lifecycle-management module for geOrchestra. Monorepo: backend + frontend + ELT + shared lib.

## Stack

| App | Tech | Path |
|-----|------|------|
| Backend | Python 3.12, FastAPI, SQLModel, PostgreSQL, async | `apps/backend/` |
| Frontend | Angular 20 (standalone, signals, zoneless, OnPush), NgRx, Tailwind 3, vitest | `apps/frontend/` |
| ELT | Airflow 3.x, TaskAPI decorators | `apps/elt/` |
| Shared lib | Python data processing | `libs/data_manipulation/` |

## Architecture

**Backend**: routes (HTTP only) -> services (business logic) -> models/core (down only).
**Frontend**: core/ (singletons) | shared/ (reusable) | features/ (self-contained modules). Atomic design, smart/presentational split, <=200 LOC/component.
**Linting**: Ruff + Pyright (Python, 100 char lines) | ESLint + Prettier (TS).

## Commands

```sh
# Python
make install-python              # Install all deps (uv)
make fix-all-python              # Ruff + format fixes
make check-all-python            # Lint + format check + Pyright
make test-backend                # pytest apps/backend
make test-backend-coverage       # pytest + coverage report
make test-libs                   # pytest libs/data_manipulation

# Frontend
cd apps/frontend && npm run format        # Prettier
cd apps/frontend && npm run lint          # ESLint
cd apps/frontend && npm run test:ut       # vitest
cd apps/frontend && npm run generate-api  # Regenerate TS client from OpenAPI
cd apps/frontend && npm run i18n:extract  # Extract translation keys

# Docker
make up-light                    # Docker compose (core)
make down                        # Stop all services
make down-v                      # Stop + remove volumes
```

**Never run these** — ask the user to run them (long-running, token expensive & user own responsability):
`make up-full`, `make up-light`, `make down`, `make down-v` `make run-backend`, `cd apps/frontend && npm run start`

## Workflow

Spec Driven Development via OpenSpec. See `agents.md` for skills and full workflow.
Agent skills: `.agents/skills/` | OpenSpec skills: `.claude/skills/` | OpenSpec config: `openspec/config.yaml`
