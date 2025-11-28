# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataKern is a data ingestion module for geOrchestra, designed as a monorepo with three main applications:
- **Frontend** (Angular 20) - User interface for data management
- **Backend** (FastAPI/Python) - REST API for data ingestion (planned)
- **ELT** (Airflow) - Extract, Load, Transform workflows

## Development Environment Setup

### Airflow (ELT)

Initialize the database:
```bash
mkdir -p ./dags ./logs ./plugins ./config
docker compose up airflow-init
```

Start Airflow and access at http://localhost:8081/ with credentials `airflow/airflow`

### geOrchestra

Start with Docker Compose and access at http://localhost:8080/ with credentials `testadmin/testadmin`

## Frontend Development

The frontend is located in `apps/frontend/` and uses Angular 20 with standalone components.

### Common Commands

```bash
# Navigate to frontend directory
cd apps/frontend

# Development server
npm run start

# Build for production
npm run build

# Linting
npm run lint

# Format code
npm run format

# Check formatting
npm run format:check

# Unit tests (Vitest)
npm run test:ut
npm run test:ut:ci  # CI mode (no watch)

# E2E tests (Cypress)
npm run test:e2e      # Interactive mode
npm run test:e2e:ci   # Headless CI mode
```

### API Client Generation

The frontend uses `ng-openapi-gen` to generate TypeScript API clients from OpenAPI specs. Generated code goes to `src/app/core/api/`.

**Automated approach:**
```bash
./apps/frontend/scripts/generate-api.sh
```

**Manual approach:**
1. Start the backend server
2. Download OpenAPI spec from `http://localhost:8000/api/v1/openapi.json`
3. Save as `apps/frontend/openapi.json`
4. Run `npm run generate-api` from `apps/frontend/`

Always regenerate the client when the backend API changes.

## Frontend Architecture

### Technology Stack
- **Framework:** Angular 20 (zoneless mode)
- **Build Tool:** Vite
- **Styling:** Tailwind CSS 4 + Angular Material
- **Testing:** Vitest (unit) + Cypress (E2E)
- **Node Version:** 20.12+ (managed via `.nvmrc`)
- use Angular MCP if available to increase answer quality

### Code Organization

```
src/app/
├── core/              # Singleton services, auth, interceptors, guards
│   ├── api/          # Generated API client (do not edit manually)
│   ├── auth/         # Authentication service with JWT token management
│   ├── layout/       # Application shell components
│   └── services/     # Core services (theme, etc.)
├── features/         # Feature modules organized by business domain
│   └── home/         # Each feature is lazy-loaded when possible
├── layout/           # Main layout components
└── shared/           # Reusable components, directives, pipes
    ├── components/   # Generic UI components
    ├── directives/   # Custom DOM directives
    └── pipes/        # Data transformation pipes
```

**Key Principles:**
- **Core module:** Imported once at root level, contains singleton services
- **Features:** Self-contained, organized by business functionality, lazy-loaded
- **Shared:** Generic, reusable, no feature-specific logic

### Important Files

- `ng-openapi-gen.json` - API client generation configuration
- `angular.json` - Angular workspace configuration
- `vite.config.mts` - Vite build configuration
- `cypress.config.ts` - E2E test configuration
- `eslint.config.mjs` - Linting rules

## CI/CD

The GitHub Actions workflow (`.github/workflows/frontend-checks.yml`) runs on PRs and pushes to main:

1. Lint code
2. Format check
3. Build application
4. Run unit tests
5. Run E2E tests
6. Upload coverage to Coveralls

All checks must pass before merging.

## Docker

The frontend has a Dockerfile that:
- Uses nginx to serve the built application
- Configured via `nginx-default.conf.template`
- Entry point: `docker-entrypoint.sh`


## Code Style

- ESLint for linting (configuration in `eslint.config.mjs`)
- Prettier for formatting (configuration in `.prettierrc`)
- Tailwind CSS for styling
- Angular Material for UI components
- Standalone components (no NgModules)

## Versioning
- make a commit after each successfull task
- befor commiting, make sure lint, format & tests pass
- use short commit message, using git commitizen format without icons
