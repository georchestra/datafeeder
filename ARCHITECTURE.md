# Datafeeder Architecture

## Overview

Datafeeder is a data ingestion module for geOrchestra built as a monorepo. It manages the full datasets lifecycle (geospatial or not): upload/sourcing → staging → transformation → publication.

## Project Structure

```
datafeeder/
├── apps/
│   ├── backend/          # FastAPI REST API — ingestion orchestration & lifecycle
│   ├── frontend/         # Angular SPA — user interface
│   └── elt/              # Airflow DAGs — data processing pipelines
├── libs/
│   └── data_manipulation/  # Shared Python lib — ingestion, transformation, GeoServer I/O
├── Makefile
└── docker-compose.yml
```

## Components

### Backend (`apps/backend/`)

FastAPI application. Exposes the REST API consumed by the frontend and by Airflow DAGs (via callbacks). Owns the PostgreSQL database (`datafeeder` schema).

Layer rules: **routes → services → models/core** (dependencies flow downward only).

Key domains:
- **Ingestion routes** (`routes/ingestion/`): staging, process, recurrence, integrity links, empty dataset
- **Integration routes**: GeoNetwork metadata, GeoServer publication, Airflow DAG status/control
- **Settings**: runtime configuration exposed via API
- **IntegrityLink** (central model): tracks a dataset's full state — source, staging table, final table, GeoNetwork/GeoServer publication status, transformation config, and schedule

### ELT (`apps/elt/`)

Airflow DAGs that execute the data pipelines. No direct HTTP dependency on the backend at runtime — they use the shared database and call back to the backend via webhook URLs passed as DAG parameters.

Two main DAGs:
- **`staging_dag`**: ingests raw data from a source (FILE, URL, FTP, DATABASE, API/WFS/OGC) into a staging PostgreSQL table
- **`process_dag`**: applies transformations (column mapping, projection, filters) and writes to the final table; supports re-ingestion from source or reuse of an existing staging table

Both DAGs accept `success_callback_url` / `failure_callback_url` parameters and call them on completion, which lets the backend update task status asynchronously.

Supported source types: `FILE`, `URL`, `FTP`, `DATABASE`, `API` (WFS / OGC API Features).

### Shared Library (`libs/data_manipulation/`)

Python package imported by both the backend and the ELT DAGs. Contains:
- Source-specific ingestion functions that stream into PostGIS via `ogr2ogr`/GDAL (file, URL, FTP, database, OGC services)
- SQL-native transformation pipeline (column remapping, projection, geometry handling, filters) executed server-side — data never leaves PostgreSQL except a bounded preview
- GeoServer write helpers
- Shared models (`IntegrityTransformation`, column config, etc.)

### Frontend (`apps/frontend/`)

Angular 20 SPA (standalone components, signals, zoneless, OnPush). Communicates exclusively with the backend REST API via a generated TypeScript client (`core/api/`).

Feature modules:
- **import**: dataset upload and source configuration wizard
- **integrity-link-list**: dataset lifecycle dashboard
- **metadata**: GeoNetwork metadata editing
- **events**: ingestion event log and recurrence management
- **authorizations**: permission management

State managed via NgRx. Shared UI primitives in `shared/`, singletons (auth, settings, layout) in `core/`.

The frontend depends on **[geonetwork-ui](https://github.com/geonetwork/geonetwork-ui)** (`geonetwork-ui` npm package) for two distinct purposes:
- **UI component library**: `ButtonComponent`, `DropdownSelectorComponent`, `TextInputComponent`, `MapContainerComponent`, `ConfirmationDialogComponent`, `SpinningLoaderComponent`, etc. — used throughout the app as the base design system.
- **Metadata editor**: `EditorFacade`, `RecordFormComponent`, `RecordsRepositoryInterface`, `findConverterForDocument` — power the full ISO 19139 metadata editing flow in the `metadata` feature.

## IntegrityLink Lifecycle

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

**Empty dataset** (`POST /ingestion/empty-dataset`): creates an `IntegrityLink` and a skeleton GeoNetwork record immediately — no DAG involved.  
**Re-staging** (`PUT /ingestion/staging/{id}`): replaces source config and re-triggers `staging_dag`.

## Minimal Runtime

The minimum viable deployment requires:
- **Backend** + its PostgreSQL database
- **Airflow** with the ELT DAGs deployed

GeoServer and GeoNetwork are optional — they enrich published datasets but are not required for core ingestion. The frontend is also optional; the backend REST API is fully functional independently.
