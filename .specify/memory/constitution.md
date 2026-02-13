# DataKern Constitution

<!--
Sync Impact Report:
- Version: 1.0.0 → 1.1.0 (MINOR: Added Angular-specific frontend architecture guidance)
- Ratification: 2026-02-13
- Last Amendment: 2026-02-13
- Modified principles:
  * VI. Component Architecture → VI. Angular Frontend Component Architecture (expanded with Angular 20 specifics)
    - Added smart vs presentational component patterns
    - Added NgRx state management requirements
    - Added Angular-specific rules (OnPush, lifecycle hooks, signals, style guide)
    - Added geonetwork-ui integration guidance
    - Added TypeScript + HTML + SCSS size limits
  * VII. Minimal Comments Standard (renumbered, added rationale)
  * VIII-IX. Renumbered remaining principles for consistency
- Added sections: N/A (expansion of existing section VI)
- Removed sections: None
- Section numbering corrected: I-IX now sequential
- Templates requiring updates:
  ✅ constitution-template.md (used as base)
  ✅ plan-template.md (updated Angular architecture checkpoint in constitution checks)
  ✅ spec-template.md (reviewed - generic structure aligns with principles)
  ✅ tasks-template.md (reviewed - structure supports modular development)
  ✅ agent-file-template.md (reviewed - will auto-populate from plans)
- Follow-up TODOs: None - all templates aligned
-->

## Core Principles

### I. API-First Architecture

DataKern MUST be designed with an API-first approach. The backend REST API is the primary contract between all components and MUST be fully functional independent of any user interface or external tool. All features MUST be accessible via well-documented API endpoints before any UI implementation begins. This ensures tool independence and enables programmatic access to all functionality.

**Rationale**: Ensures interoperability, enables automation, and prevents vendor lock-in to specific tools or interfaces.

### II. Component Modularity & Independence

The system is composed of loosely coupled components with clear boundaries: Backend (API + database), Frontend (UI), ELT (Airflow workflows), and shared libraries. Each component MUST operate independently where feasible. GeoServer, GeoNetwork, and the Frontend are optional components that enhance functionality but MUST NOT be required for core ingestion operations. The Backend API and ELT workflows form the minimal viable system.

**Rationale**: Promotes maintainability, enables selective deployment, allows independent scaling, and reduces coupling.

### III. Monorepo Structure with Shared Libraries

The project is organized as a monorepo with distinct apps (backend, frontend, elt) and shared libraries (data_manipulation). Shared libraries MUST be self-contained, independently testable, versioned, and documented. Common data manipulation logic MUST reside in shared libraries to avoid duplication between backend and ELT workflows.

**Rationale**: Facilitates code reuse, ensures consistency across components, simplifies dependency management, and maintains a single source of truth for shared logic.

### IV. Testing & Quality Assurance

All components MUST include automated tests. Python applications use pytest with coverage reporting (target: >80% coverage for critical paths). Frontend applications use vitest for unit testing. Tests MUST be run before merging code. Integration tests are required for: API contract changes, inter-service communication, shared library modifications, and database schema changes.

**Rationale**: Prevents regressions, documents expected behavior, enables safe refactoring, and ensures reliability of the data ingestion pipeline.

### V. Code Quality & Standards

All code MUST adhere to project-wide linting and formatting standards. Python code uses Ruff (line length: 100, import sorting enabled) and Pyright for type checking. TypeScript/Angular code uses ESLint and Prettier. All code MUST pass linting, formatting, and type checks before merging. Use `make fix-all-python` and `npm run format` to auto-fix issues.

**Rationale**: Maintains codebase consistency, reduces cognitive load, prevents bugs through static analysis, and improves code reviewability.

### VI. Angular Frontend Component Architecture

_(Applies specifically to `apps/frontend` - Angular 20 application)_

Angular components MUST follow atomic design principles with clear separation of concerns. Components MUST be organized by feature modules. Smart (container) components MUST be separated from presentational (dumb) components. Component size MUST be limited to ≤200 lines including template (exceptions require explicit justification).

**Implementation Requirements**:

- **Atomic Structure**: atoms (basic UI elements) → molecules (composite components) → organisms (feature components)
- **Feature Modules**: Organize by domain (`app/features/ingestion/`, `app/features/monitoring/`, `app/shared/`)
- **Component Types**:
  - **Smart Components**: Inject services, manage state (NgRx Store), handle routing, delegate to presentational components
  - **Presentational Components**: Receive data via `@Input()`, emit events via `@Output()`, focus on display logic only
  - Standalone components preferred (Angular 20 best practice)
- **State Management**: Use NgRx for application state; smart components connect via selectors and dispatch actions
- **Component Size**: Maximum 200 lines total (TypeScript + HTML + SCSS) - split larger components
- **Naming Convention**: `*.component.ts`, `*.container.ts` (for smart components)
- **Testing**: Each component MUST have corresponding `.spec.ts` with vitest tests; use @angular/cdk/testing for robust component tests

**Angular-Specific Rules**:

- Use OnPush change detection strategy by default for performance
- Implement proper lifecycle hooks (OnInit, OnDestroy with takeUntil pattern for subscriptions)
- Use Angular signals where appropriate (Angular 20 reactive primitives)
- Avoid direct DOM manipulation; use Angular directives and Renderer2 when needed
- Follow Angular style guide for file structure and naming
- Use Tailwind CSS 3 utility classes (configured in project) for styling
- Leverage geonetwork-ui component library (version 2.9.0) for geospatial UI elements

**Rationale**: Atomic architecture enhances reusability, simplifies testing, improves code navigation, enables parallel development, and aligns with Angular best practices for scalable applications.

### VII. Minimal Comments Standard

**MUST** write self-documenting code that requires minimal comments. Comments **MUST** explain "why" not "what". Comments **MUST NOT** duplicate information already expressed in code. Comments **MUST NOT** reference user stories, task IDs, or implementation metadata in production code.

**Rationale**: Self-documenting code reduces maintenance burden, prevents comment drift, and improves code clarity through better naming and structure.

### VIII. Dependency Management & Build Reproducibility

Python dependencies are managed using uv with workspace support for the monorepo structure. The project requires Python 3.12 exactly. Frontend requires Node.js 22.20.0+. All dependencies MUST be pinned to specific versions (or narrow ranges) to ensure reproducible builds. Lock files MUST be committed and kept up-to-date.

**Rationale**: Ensures consistent development and production environments, prevents dependency conflicts, and enables reliable deployments.

### IX. Containerization & Environment Parity

All services MUST be containerized using Docker with docker-compose orchestration. Development, testing, and production environments MUST maintain parity through containerization. The Makefile provides standardized commands for environment setup, testing, and deployment. Developers MUST be able to run the full stack locally with `make up-full` or individual services with `make up-light`.

**Rationale**: Eliminates "works on my machine" issues, simplifies onboarding, ensures production-like testing, and standardizes deployment.

## Security & Authentication

DataKern integrates with geOrchestra's security infrastructure via a gateway that handles authentication and authorization. The Backend MUST respect user identity and organization context provided by the gateway. Users MUST only access resources belonging to their organization unless they have administrator privileges. All sensitive configuration MUST be externalized via environment variables or properties files (never committed to version control).

**Rationale**: Ensures data isolation, complies with organizational access policies, and protects sensitive information.

## Data Integrity & Traceability

The `datakern.integrity_link` table is the source of truth linking staging data, final datasets, and metadata. Every ingestion operation MUST create an integrity_link record tracking: source information, staging table, final table, timestamps, ownership, and processing status. DAG workflows MUST update integrity_link records via backend callbacks on success or failure. This ensures full traceability from raw ingestion through final publication.

**Rationale**: Enables auditing, facilitates debugging, supports data lineage tracking, and ensures accountability.

## Observability & Monitoring

All services MUST emit structured logs (JSON format preferred for production). Airflow DAGs MUST use callback URLs to notify the Backend of task completion status. The Backend MUST expose endpoints for monitoring DAG execution status. Critical errors MUST be surfaced to users through appropriate channels (UI notifications, API error responses, logs).

**Rationale**: Enables troubleshooting, supports operational monitoring, facilitates debugging of distributed workflows, and improves user experience.

## Versioning & Breaking Changes

The project uses semantic versioning (MAJOR.MINOR.PATCH) at the monorepo level and for individual components where appropriate. API endpoints SHOULD maintain backward compatibility whenever possible; breaking changes MUST be versioned (e.g., /api/v1/, /api/v2/). Shared libraries MUST follow semantic versioning strictly: MAJOR for incompatible API changes, MINOR for backward-compatible additions, PATCH for bug fixes. Database migrations MUST be backward-compatible or include rollback procedures.

**Rationale**: Enables safe upgrades, prevents breaking dependent systems, and communicates change impact clearly.

## Documentation & Onboarding

All components MUST include a README with: purpose, setup instructions, API documentation (for backend/libraries), and usage examples. The root README provides quick-start instructions with Docker. API endpoints MUST be documented using OpenAPI/Swagger (accessible at /docs). Architecture decisions and workflows MUST be documented in dedicated files (ARCHITECTURE.md, technical vision docs). New contributors MUST be able to run the full stack locally by following README instructions.

**Rationale**: Reduces onboarding friction, serves as living documentation, enables self-service, and captures architectural knowledge.

## Governance

This constitution supersedes all other development practices and conventions. All code reviews, pull requests, and architectural decisions MUST verify compliance with these principles. Violations require explicit justification and team consensus. Amendments to this constitution require:

1. Documented rationale with examples
2. Review by project maintainers
3. Migration plan for affected code (if applicable)
4. Communication to all contributors

Version changes follow semantic versioning:

- **MAJOR**: Backward-incompatible principle removals or fundamental redefinitions
- **MINOR**: New principles added or material expansions
- **PATCH**: Clarifications, refinements, or corrections without semantic change

All team members MUST review this constitution during onboarding and revisit it when making architectural decisions.

**Version**: 1.1.0 | **Ratified**: 2026-02-13 | **Last Amended**: 2026-02-13
