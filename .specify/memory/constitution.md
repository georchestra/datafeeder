# DataKern Constitution

<!--
Sync Impact Report:
- Version: 1.3.0 → 1.4.0 (MINOR: Added Design System & UI Mockups section)
- Ratification: 2026-02-13
- Last Amendment: 2026-02-16
- Modified principles: None
- Added sections:
  * "Design System & UI Mockups" — new top-level section documenting:
    - Official Figma design file URL (ingestion-données)
    - Figma MCP tool usage for implementation
    - Design workflow (before/during/after implementation)
    - Design compliance requirements and deviation policy
    - Design token management (colors, spacing, typography)
    - Rationale for design-driven development
- Removed sections: None
- Templates requiring updates:
  ✅ plan-template.md (updated — added Design Compliance checkpoint
     to constitution checks for frontend features)
  ✅ spec-template.md (reviewed — user scenarios can reference
     Figma screens for acceptance criteria)
  ✅ tasks-template.md (reviewed — implementation tasks can include
     "Extract component specs from Figma using MCP")
- Follow-up TODOs: None — all templates aligned
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

## Functional Vision

DataKern delivers a complete data-ingestion and lifecycle-management
module for the geOrchestra platform. At the end of the ingestion
process a dataset MUST be referenced in the platform catalogue,
diffused via platform services, and available for consultation,
download, and preview according to defined access rules. Users and
administrators MUST be able to revisit any published dataset at any
time to modify source configuration, recurrence, and metadata.

### Functional Architecture

The application is composed of two functional modules:

1. **Ingestion Tunnel** — guided workflow for connecting a data
   source, previewing and transforming the data, and triggering
   initial ingestion.
2. **Data Publisher** — dashboard and editor for managing existing
   datasets (metadata, access rights, harvesting recurrence, event
   journal).

### User Scenario 1: Creating a Dataset from a Data Source

1. The user accesses the ingestion module via the "Import" menu
   entry. The module MUST retain the platform header bar so that
   navigation to other modules remains available at all times.
2. The user selects a source type. The platform MUST support at
   minimum:
   - Local file upload
   - Remote file via HTTP
   - Remote file via FTP
   - OGC service or OGC API
   - Table from a pre-configured PostgreSQL database
3. The user MAY provide access credentials (basic auth) if required
   and MAY test connectivity before proceeding.
4. Optionally, the user MAY skip source configuration entirely and
   proceed directly to metadata editing.
5. Upon successful source validation the system displays a tabular
   preview of a data extract. The user MAY:
   - Configure the dataset title
   - Set a harvesting recurrence
   - Override encoding and projection
   - Select or exclude columns
   - Apply simple row filters (exact match, starts-with, contains)
   - Rename columns
6. If the data contains a geographic component, the user MAY toggle
   to a cartographic preview to verify projection accuracy and
   correct it if needed.
7. After source configuration the user enters the metadata editor
   (leaving the ingestion tunnel).

### User Scenario 2: Modifying an Existing Dataset

1. The user accesses "My Data" from the main menu and sees a
   dashboard listing all datasets they have published or have
   editing rights on, with a search field for quick retrieval.
2. From the dashboard (or from the dataset detail view) the user
   MAY navigate to:
   - Metadata editing
   - Access rights management
   - Harvesting recurrence configuration
   - Source (re)configuration (reopens the ingestion tunnel with
     pre-filled values)
3. The user MAY create a metadata record without associating a
   data source immediately.
4. Deleting a dataset (with confirmation) is irreversible and MUST
   remove the source configuration, associated data services, and
   all metadata simultaneously.

### Metadata Editing

When editing metadata (either after source configuration in the
ingestion tunnel or from the data dashboard), the user accesses the
metadata editor which MUST offer a progressive form with at least
these fields: Title, Description, Preview, Keywords, Themes,
Temporal extent, Spatial extent, Supplementary resources, Access &
use conditions, Data & metadata contacts.

The user MAY save work-in-progress without publishing, or publish
the dataset and its descriptive information at any time.

### Access Rights Management

By default, a newly ingested dataset MUST be visible only to its
author (metadata) and accessible via data services only to platform
administrators. The access-rights tab MUST allow:

- **Metadata**: grant read or write access to specific user groups;
  optionally make metadata publicly accessible.
- **Data**: grant read or write access to specific roles; optionally
  open data access to everyone (open data).

### Harvesting Recurrence

The recurrence tab MUST allow the user to:

- Trigger an immediate harvest
- Modify the update frequency
- Suspend harvesting (last data preserved, updates paused)

### Event Journal

The event-journal tab MUST display the date and status of recent
harvest runs for the dataset. When an error occurs during retrieval
or transformation, the type and detail of the error MUST be shown so
that the user can diagnose or escalate the issue.

**Rationale**: Codifying the functional vision in the constitution
ensures that all contributors share a common understanding of what
DataKern delivers to end users and that design decisions stay aligned
with the intended user experience.

## Application Architecture

This section documents the mandatory code structure for both backend and frontend applications. All new features MUST respect these architectural patterns to maintain consistency and enable team scalability.

### Backend Architecture (`apps/backend`)

The backend follows a **layered architecture** with clear separation between API routes, business logic, data models, and infrastructure concerns.

**Directory Structure**:

```
apps/backend/src/
├── main.py                    # FastAPI application entry point
├── api/                       # API layer (routes, dependencies)
│   ├── main.py               # Router registration
│   ├── deps.py               # Reusable dependencies (DB sessions, auth context)
│   ├── internal.py           # Internal/admin routes
│   └── routes/               # Feature-based route modules
│       ├── ingestion/        # Ingestion-related endpoints
│       │   ├── integrity_link.py    # Single integrity link operations
│       │   ├── integrity_links.py   # List/query operations
│       │   ├── staging.py           # Staging DAG triggers
│       │   └── process.py           # Processing DAG triggers
│       ├── airflow.py        # Airflow API proxy endpoints
│       ├── geonetwork.py     # GeoNetwork integration
│       ├── settings.py       # Settings/configuration endpoints
│       ├── internal_files.py # File management
│       └── utils.py          # Route utilities
├── models/                    # SQLModel data models (ORM + Pydantic)
│   ├── integrity_link.py     # IntegrityLink model
│   ├── data_import.py        # DataImport model
│   └── user.py               # User/context models
├── services/                  # Business logic layer
│   ├── airflow_client.py     # Airflow API client
│   ├── airflow_logs.py       # Airflow log retrieval
│   ├── geoserver.py          # GeoServer client
│   ├── metadata_service.py   # Metadata management
│   ├── georchestra.py        # geOrchestra integration
│   ├── console_service.py    # Console API client
│   ├── settings_service.py   # Settings management
│   └── files.py              # File handling service
├── core/                      # Infrastructure/cross-cutting concerns
│   ├── config.py             # Application configuration
│   ├── db.py                 # Database session management
│   ├── security.py           # Authentication/authorization
│   ├── encryption.py         # Encryption utilities
│   ├── logging.py            # Logging configuration
│   ├── paths.py              # Path constants
│   └── callback.py           # Callback handling
├── plugins/                   # Extension mechanisms
│   └── PropertiesConfigSettingsSource.py  # Custom config source
└── tests/                     # Test suite (mirrors src structure)
    ├── api/                  # API route tests
    ├── models/               # Model tests
    └── services/             # Service tests
```

**Layering Rules (Backend)**:

1. **API Layer** (`api/`) - MUST only handle HTTP concerns: request validation, response formatting, dependency injection, error handling. Business logic MUST be delegated to services.
2. **Service Layer** (`services/`) - MUST contain all business logic, external service integration, and orchestration. Services MUST be framework-agnostic (no FastAPI dependencies).
3. **Model Layer** (`models/`) - MUST define data structures using SQLModel (combines Pydantic + SQLAlchemy). Models serve as both ORM entities and API schemas.
4. **Core Layer** (`core/`) - MUST provide infrastructure: configuration, database sessions, security context, logging. These are cross-cutting concerns available to all layers.
5. **Plugins** (`plugins/`) - MUST extend framework functionality without modifying core code.

**Dependency Flow**: API → Services → Models/Core (downward only; no circular dependencies)

**File Organization**:

- Group related endpoints by feature/domain in `api/routes/`
- One service file per external system or business domain
- Keep route files focused: 1-2 related endpoints per file for complex operations, grouped endpoints for CRUD

### Frontend Architecture (`apps/frontend`)

The frontend follows **Angular feature-module architecture** with strict separation between core infrastructure, shared utilities, and feature-specific code.

**Directory Structure**:

```
apps/frontend/src/
├── main.ts                    # Application bootstrap
├── index.html                 # HTML entry point
├── styles.scss               # Global styles
├── app/
│   ├── app.ts                # Root component
│   ├── app.routes.ts         # Application routing configuration
│   ├── app.config.ts         # Application-level providers and configuration
│   ├── core/                 # Core module (singleton services, app-wide concerns)
│   │   ├── api/              # Generated API client (ng-openapi-gen)
│   │   ├── auth/             # Authentication services
│   │   ├── layout/           # Global layout components (header, navigation)
│   │   └── settings/         # Application settings service
│   ├── shared/               # Shared module (reusable components, pipes, directives)
│   │   ├── components/       # Presentation components (buttons, forms, tables)
│   │   ├── directives/       # Reusable directives
│   │   ├── pipes/            # Reusable pipes (transforms)
│   │   ├── types/            # TypeScript interfaces/types
│   │   └── utils/            # Utility functions
│   ├── features/             # Feature modules (domain-specific functionality)
│   │   ├── import/           # Ingestion tunnel feature
│   │   ├── integrity-link-list/  # Dataset list/dashboard feature
│   │   ├── metadata/         # Metadata editor feature
│   │   └── events/           # Event journal feature
│   └── layout/               # Layout orchestration
└── translations/             # i18n JSON files (en, fr, de, etc.)
```

**Module Rules (Frontend)**:

1. **Core Module** (`app/core/`) - MUST contain singleton services, authentication, global layout, and app-wide state. MUST be imported once in `app.config.ts`. Components here are NOT feature-specific.
2. **Shared Module** (`app/shared/`) - MUST contain reusable presentational components, pipes, directives, and utilities. MUST NOT contain feature-specific logic or services. Can be imported by any feature module.
3. **Feature Modules** (`app/features/`) - MUST be self-contained with their own routing, components, services, and state. Features SHOULD communicate via services or store, not direct component coupling.
4. **Layout** (`app/layout/`) - MUST handle page layout composition (header, sidebar, content area orchestration).

**Naming Conventions**:

- Presentational components: `*.component.ts`
- Services: `*.service.ts`

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

## Design System & UI Mockups

All frontend user interface development MUST reference the official Figma design mockups to ensure visual consistency and alignment with UX specifications. The design file serves as the single source of truth for visual design, component specifications, user flows, and interaction patterns.

**Design Resources**:

- **Figma Design File**: [DataKern - Ingestion données](https://www.figma.com/design/IwMxmE9G9D9StF2QLlR1uE/ingestion-donn%C3%A9es)
  - **Note**: This design file contains all UI components and screens organized by code sprints, allowing developers to reference the appropriate sprint section when implementing features
- **Implementation Tool**: Figma MCP (Model Context Protocol) - Use Figma MCP tools to extract component specifications, styles, and assets directly from the design file during implementation

**Design Workflow**:

1. **Before Implementation**: Review relevant Figma screens/components for the feature being developed
2. **During Implementation**: Use Figma MCP to:
   - Extract component structure and properties
   - Generate code scaffolding aligned with designs
   - Retrieve design tokens (colors, spacing, typography)
   - Export assets (icons, images) at correct resolutions
3. **After Implementation**: Verify UI implementation matches Figma designs (spacing, colors, typography, interactions)

**Design Compliance Requirements**:

- Frontend features MUST match Figma mockups for layout, spacing, colors, and typography
- Deviations from designs MUST be justified (technical constraints, accessibility improvements) and documented
- New UI components not present in Figma SHOULD follow established design patterns from existing components
- Design feedback loops: if implementation reveals design issues, flag them for designer review before proceeding with workarounds

**Design Tokens**:

- Colors, spacing, typography, and other design tokens SHOULD be extracted from Figma and centralized in the codebase
- Use Tailwind CSS configuration to align utility classes with Figma design tokens
- Maintain consistency between Figma styles and CSS variables/Tailwind config

**Rationale**: Referencing official design mockups ensures visual consistency, reduces implementation ambiguity, improves collaboration between designers and developers, and maintains a professional user experience. The Figma MCP tool bridges design and code, reducing manual translation errors and accelerating development.

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

**Version**: 1.4.0 | **Ratified**: 2026-02-13 | **Last Amended**: 2026-02-16
