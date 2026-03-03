# AI Agent Guide

This file is the entry point for AI agents working in this codebase. It points to the key resources needed to understand the project, its conventions, and active work.

---

## Constitution

The constitution is the primary reference for project principles, architecture decisions, coding standards, and workflow rules. **Read it before making any significant changes.**

- [.specify/memory/constitution.md](.specify/memory/constitution.md)

---

## Skills

Skills contain domain-specific instructions for working with particular technologies used in this project. Load the relevant skill before implementing in that domain.

| Skill                    | Description                                               | File                                                                                             |
| ------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `angular-datakern`       | Angular 20 frontend (components, NgRx, signals, Tailwind) | [.agents/skills/angular-datakern/SKILL.md](.agents/skills/angular-datakern/SKILL.md)             |
| `fastapi-expert`         | FastAPI backend (async, SQLAlchemy, JWT, Pydantic V2)     | [.agents/skills/fastapi-expert/SKILL.md](.agents/skills/fastapi-expert/SKILL.md)                 |
| `airflow-datakern`       | Airflow 3.x DAGs (TaskAPI, task groups, ELT pipelines)    | [.agents/skills/airflow-datakern/SKILL.md](.agents/skills/airflow-datakern/SKILL.md)             |
| `implement-design`       | Figma → code implementation with 1:1 fidelity             | [.agents/skills/implement-design/SKILL.md](.agents/skills/implement-design/SKILL.md)             |
| `tailwind-design-system` | Tailwind CSS v4 design system and component patterns      | [.agents/skills/tailwind-design-system/SKILL.md](.agents/skills/tailwind-design-system/SKILL.md) |
| `geopandas`              | Geospatial data processing with GeoPandas                 | [.agents/skills/geopandas/SKILL.md](.agents/skills/geopandas/SKILL.md)                           |
| `skill-creator`          | How to create or update a skill                           | [.agents/skills/skill-creator/SKILL.md](.agents/skills/skill-creator/SKILL.md)                   |

---

## Specs

Specs define features under active development. Each spec folder contains a structured breakdown of the feature.

| Spec                                                                  | Description                    |
| --------------------------------------------------------------------- | ------------------------------ |
| [specs/001-preview-column-actions](specs/001-preview-column-actions/) | Preview column actions feature |

### Spec file structure

Each spec folder typically contains:

- `spec.md` — feature specification and acceptance criteria
- `plan.md` — implementation plan
- `tasks.md` — actionable task breakdown
- `data-model.md` — data model changes
- `research.md` — research and prior art
- `quickstart.md` — quick orientation for the feature
- `contracts/` — API contracts (request/response schemas)
- `checklists/` — validation checklists

---

## Project structure

```
apps/
  backend/    # FastAPI application
  elt/        # Airflow DAGs and ELT pipelines
  frontend/   # Angular 20 application
libs/
  data_manipulation/  # Shared Python data processing library
specs/        # Feature specifications
.agents/
  skills/     # Domain-specific AI agent instructions
.specify/
  memory/     # Project memory and constitution
```
