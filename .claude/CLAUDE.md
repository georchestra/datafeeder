# DataFeeder

Data-ingestion & lifecycle-management module for geOrchestra. Monorepo: backend + frontend + ELT + shared lib.

## Stack

| App | Tech | Path |
|-----|------|------|
| Backend | Python 3.12, FastAPI, SQLModel, PostgreSQL, async | `apps/backend/` |
| Frontend | Angular 20 (standalone, signals, zoneless, OnPush), NgRx, Tailwind 3 | `apps/frontend/` |
| ELT | Airflow 3.x, TaskAPI decorators | `apps/elt/` |
| Shared lib | Python data processing | `libs/data_manipulation/` |

## Tooling

**Python** (all packages managed via uv workspace):
- **uv** — package manager & virtualenv. `uv sync --all-packages` installs everything.
- **poethepoet** (poe) — task runner. Tasks defined in each `pyproject.toml` under `[tool.poe.tasks]`.
- **Ruff** — linter + formatter (100 char lines). Config: `ruff.toml` at root, extended per package.
- **Pyright** — type checker. Config: `pyrightconfig.json` at root, extended per package.
- **pytest** — test runner. `pytest-asyncio` for async tests, `pytest-cov` for coverage.
- **hatchling** — build backend for `libs/data_manipulation` and `apps/backend`.

**Frontend** (npm):
- **Angular CLI** (ng) — build, serve, generate.
- **ESLint** — linter. **Prettier** — formatter.
- **vitest** — unit tests. **Cypress** — e2e tests.
- **ng-openapi-gen** — generates TS API client from backend OpenAPI spec.
- **ngx-translate-extract** — extracts i18n keys to JSON translation files.

**Infrastructure**:
- **Docker Compose** — orchestrates backend, frontend, PostgreSQL, Airflow, and optionally GeoServer/GeoNetwork.

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

## Token Efficiency

- Be terse. No preamble, no recap, no trailing summaries. Lead with the action or answer.
- Read only the lines you need — use `offset` and `limit` on large files.
- Prefer Glob/Grep over Agent for simple lookups. Use Agent only for multi-step exploration.
- Batch independent tool calls in a single message.
- Don't re-read files already in context. Don't echo back code the user can see in the diff.
- When explaining changes, one sentence per change is enough. Skip unchanged files.
- Don't generate plans or lists unless asked. Just do the work.
- When fixing errors, show only the fix, not a diagnosis of what went wrong unless non-obvious.

## Workflow

Agent skills available here : `.agents/skills`
Spec Driven Development via OpenSpec :
- OpenSpec skills: `.claude/skills/`.
- OpenSpec config: `openspec/config.yaml`
