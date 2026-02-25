# AI Agent Guide

---

## OpenSpec (Change Management)

Config & project context: `openspec/config.yaml` | Docs: [openspec.dev](https://openspec.dev)

| Action      | Skill                                                                  |
| ----------- | ---------------------------------------------------------------------- |
| **Propose** | [openspec-propose](.github/skills/openspec-propose/SKILL.md)           |
| **Apply**   | [openspec-apply-change](.github/skills/openspec-apply-change/SKILL.md) |
| **Explore** | [openspec-explore](.github/skills/openspec-explore/SKILL.md)           |
| **Archive** | [openspec-archive-change](.github/skills/openspec-archive-change/SKILL.md) |

### Active Changes

| Change | Status |
| ------ | ------ |
| [enforce-permissions](openspec/changes/enforce-permissions/) — Backend 403 + frontend conditional nav | Ready to apply |

---

## Skills

Domain-specific agent instructions: [.agents/skills/](.agents/skills/) | OpenSpec skills: [.github/skills/](.github/skills/)

---

## Speckit (Feature Specifications)

Constitution & memory: [.specify/memory/constitution.md](.specify/memory/constitution.md)

| Spec                                                                  | Description                    | Status               |
| --------------------------------------------------------------------- | ------------------------------ | -------------------- |
| [specs/001-preview-column-actions](specs/001-preview-column-actions/) | Preview column actions feature | Implemented          |
| [specs/002-enforce-permissions](specs/002-enforce-permissions/)       | Enforce permissions (original) | Migrated to OpenSpec |

---

## Commands & Config

| What          | Where                                                  | Purpose                                         |
| ------------- | ------------------------------------------------------ | ------------------------------------------------ |
| Makefile      | [Makefile](Makefile)                                   | Top-level commands: `make up-*`, `make test-*`, `make fix-all-python` |
| Backend       | [apps/backend/pyproject.toml](apps/backend/pyproject.toml) | Python deps & scripts                       |
| Frontend      | [apps/frontend/package.json](apps/frontend/package.json)   | `npm start`, `npm test`, `npm run format`   |
| ELT           | [apps/elt/pyproject.toml](apps/elt/pyproject.toml)         | Airflow DAG deps                            |
| Shared lib    | [libs/data_manipulation/pyproject.toml](libs/data_manipulation/pyproject.toml) | Shared Python library         |
| Root          | [pyproject.toml](pyproject.toml)                       | Monorepo workspace config                        |

---

## Project structure

```
apps/
  backend/    # FastAPI application
  elt/        # Airflow DAGs and ELT pipelines
  frontend/   # Angular 20 application
libs/
  data_manipulation/  # Shared Python data processing library
openspec/
  config.yaml         # Project context & artifact rules
  changes/            # Active changes (proposal → specs → design → tasks)
  specs/              # Main specs (living truth after archive)
specs/                # Feature specifications (speckit)
.agents/
  skills/             # Domain-specific AI agent instructions
.github/
  skills/             # OpenSpec workflow skills
.specify/
  memory/             # Project memory and constitution (speckit)
```
