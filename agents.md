# AI Agent Guide

This file is the entry point for AI agents working in this codebase. It points to the key resources needed to understand the project, its conventions, active work and mistakes to avoid. Development is mainly done following Spec Driven Development, either using OpenSpec or spec-kit:

---

## Skills

Domain-specific agent instructions: [.agents/skills/](.agents/skills/) 

| Skill                                                                    | Purpose                                                                          |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| [airflow-datafeeder](.agents/skills/airflow-datafeeder/SKILL.md)         | Build Airflow 3.x DAGs following Datafeeder patterns (TaskAPI, XCom, PostgreSQL) |
| [angular-datafeeder](.agents/skills/angular-datafeeder/SKILL.md)         | Build Angular 20 components and features in `apps/frontend/`                     |
| [fastapi-expert](.agents/skills/fastapi-expert/SKILL.md)                 | Build async FastAPI endpoints with SQLAlchemy, Pydantic V2, OpenAPI              |
| [frontend-api-sync](.agents/skills/frontend-api-sync/SKILL.md)           | Regenerate the frontend TypeScript client after backend API changes              |
| [geopandas](.agents/skills/geopandas/SKILL.md)                           | Work with geospatial data: Shapefile, GeoJSON, spatial joins, reprojection       |
| [implement-design](.agents/skills/implement-design/SKILL.md)             | Translate Figma designs into production-ready code (requires Figma MCP)          |
| [tailwind-design-system](.agents/skills/tailwind-design-system/SKILL.md) | Build design systems with Tailwind CSS v4, design tokens, component libraries    |

---

## Commands & Config

| What       | Where                                                                          | Purpose                                                               |
| ---------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| Makefile   | [Makefile](Makefile)                                                           | Top-level commands: `make up-*`, `make test-*`, `make fix-and-check-all-python` |
| Backend    | [apps/backend/pyproject.toml](apps/backend/pyproject.toml)                     | Python deps & scripts                                                 |
| Frontend   | [apps/frontend/package.json](apps/frontend/package.json)                       | `npm start`, `npm test`, `npm run format`                             |
| ELT        | [apps/elt/pyproject.toml](apps/elt/pyproject.toml)                             | Airflow DAG deps                                                      |
| Shared lib | [libs/data_manipulation/pyproject.toml](libs/data_manipulation/pyproject.toml) | Shared Python library                                                 |
| Root       | [pyproject.toml](pyproject.toml)                                               | Monorepo workspace config                                             |

---

## Project structure

```
apps/
  backend/    # FastAPI application
  elt/        # Airflow DAGs and ELT pipelines
  frontend/   # Angular 20 application
libs/
  data_manipulation/  # Shared Python data processing library
.agents/
  skills/             # Domain-specific AI agent instructions
```
