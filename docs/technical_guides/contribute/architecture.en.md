# Architecture

## Design principles

- The backend should, in theory, stay agnostic of the task orchestrator (Airflow today), GeoServer, GeoNetwork, or any other integrated service — these are integrations, not core assumptions. 
- DAGs should stay small: a small, narrowly-scoped DAG is easier to reason about, debug and retry than a large one. 
- Ingestion and transformation logic must live in `libs/data_manipulation/`, not in DAG task code, so the orchestrator stays a thin caller and the actual intelligence is testable and reusable independently of Airflow. 
- Finally, the application should, in theory, be usable API-first: the frontend is just one client of the backend REST API, and any operation it exposes should remain automatable through the API alone.

## Backend (`apps/backend/`)

FastAPI application. Exposes the REST API consumed by the frontend and by Airflow DAGs (via callbacks). Owns the
PostgreSQL database (`datafeeder` schema).

Layer rules: **routes → services → models/core** (dependencies flow downward only).

Key domains:

- **Ingestion routes** (`routes/ingestion/`): staging, process, recurrence, integrity links, empty dataset
- **Integration routes**: GeoNetwork metadata proxy, GeoServer publication, Airflow DAG status/control
- **Settings**: runtime configuration exposed via API
- **`IntegrityLink`** (central model): tracks a dataset's full state — source, staging table, final table,
  GeoNetwork/GeoServer publication status, transformation config, and schedule

## ELT (`apps/elt/`)

Airflow DAGs that execute the data pipelines. No direct HTTP dependency on the backend at runtime — they use the
shared database and call back to the backend via webhook URLs passed as DAG parameters.

Two main DAGs:

- **`staging_dag`**: ingests raw data from a source (FILE, URL, FTP, DATABASE, API/WFS/OGC) into a staging
  PostgreSQL table
- **`process_dag`**: applies transformations (column mapping, projection, filters) and writes to the final table;
  supports re-ingestion from source or reuse of an existing staging table

Both DAGs accept `success_callback_url` / `failure_callback_url` parameters and call them on completion, which lets
the backend update task status asynchronously.

Supported source types: `FILE`, `URL`, `FTP`, `DATABASE`, `API` (WFS / OGC API Features).

## Shared library: `libs/data_manipulation/`

Python package imported by both the backend and the ELT DAGs. Contains:

- Source-specific ingestion functions (file, URL, FTP, database, OGC services)
- Transformation pipeline (column remapping, projection reprojection, geometry handling, SQL filters)
- GeoServer write helpers
- Shared models (`IntegrityTransformation`, column config, etc.)

## Shared library: `libs/ai/`

Python package providing AI provider integrations shared across the monorepo.

## Frontend (`apps/frontend/`)

Angular 20 SPA (standalone components, signals, zoneless, `OnPush`). Communicates exclusively with the backend REST
API via a generated TypeScript client (`core/api/`).

Feature modules:

- **import**: dataset upload and source configuration wizard
- **integrity-link-list**: dataset lifecycle dashboard
- **metadata**: GeoNetwork metadata editing
- **events**: ingestion event log and recurrence management
- **authorizations**: permission management

State is managed via NgRx. Shared UI primitives live in `shared/`, singletons (auth, settings, layout) in `core/`.

The frontend depends on **[geonetwork-ui](https://github.com/geonetwork/geonetwork-ui)** (`geonetwork-ui` npm
package).

## IntegrityLink lifecycle

`IntegrityLink` is the central record tracking a dataset from import to deletion (one record = one dataset).

```
POST /staging        → creates IntegrityLink, triggers staging_dag (source → staging table)
                         success: records retrieve time
                         failure: deletes IntegrityLink + staging table

POST /process        → creates GN metadata record, triggers process_dag (staging → final table, with transformations)
                         success: publishes GeoServer layer, updates GN metadata record
                         failure: drops partial final table

(cron) ingestion_<uuid> → re-triggers process_dag on schedule (re-fetches from original source)

DELETE /integrity-link/{id} → unpublishes GeoServer layer, deletes GN record, drops tables, deletes row
```

**Empty dataset** (`POST /ingestion/empty-dataset`): creates an `IntegrityLink` and a skeleton GeoNetwork record
immediately — no DAG involved.
**Re-staging** (`PUT /ingestion/staging/{id}`): replaces source config and re-triggers `staging_dag`.
