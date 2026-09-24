# AI Agent Guide

## Project structure

```
apps/
  backend/            # FastAPI application
  elt/                # Airflow 3 DAGs and ELT pipelines
  frontend/           # Angular 20 application
libs/
  data_manipulation/  # Shared Python data processing library
```

## Commands

- `make up` / `make up-no-airflow`, `make down`: start/stop the stack
- `make test-backend`, `make test-libs`: Python tests
- `make fix-and-check-all-python`: lint and format Python
- In `apps/frontend/`: `npm run test:ut`, `npm run lint`, `npm run format`

## Skills

In [.agents/skills/](.agents/skills/). Not actively maintained: check the actual code before relying on them.

| Skill                                                                    | Use when                                            |
| ------------------------------------------------------------------------ | --------------------------------------------------- |
| [airflow-datafeeder](.agents/skills/airflow-datafeeder/SKILL.md)         | Writing Airflow DAGs                                |
| [angular-datafeeder](.agents/skills/angular-datafeeder/SKILL.md)         | Writing Angular components in `apps/frontend/`      |
| [fastapi-expert](.agents/skills/fastapi-expert/SKILL.md)                 | Writing FastAPI endpoints                           |
| [frontend-api-sync](.agents/skills/frontend-api-sync/SKILL.md)           | After any backend API change (regenerate TS client) |
| [implement-design](.agents/skills/implement-design/SKILL.md)             | Implementing Figma designs (requires Figma MCP)     |
| [tailwind-design-system](.agents/skills/tailwind-design-system/SKILL.md) | Working on Tailwind v4 design tokens and components |
