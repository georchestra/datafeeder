## Why

The ingestion tunnel currently supports file upload, URL, and FTP as data source types. Users who already have data in a PostgreSQL database cannot ingest it without first exporting to a file. Adding a database source type lets users point directly at an existing schema + table, removing unnecessary export/import friction and aligning with the architecture principle that all source types (file, service, database) flow through the same raw → staging → final pipeline.

## What Changes

- **New radio-button option "Database"** in the ingestion tunnel step 1 (source selector), shown only when the platform has a database connection configured.
- **Schema + table text inputs** replacing the file/URL/FTP fields when the database source type is selected. Both fields are mandatory.
- **Backend configuration**: new optional environment variables (`POSTGRES_SOURCE_*`) for the external source database connection string. When not set, the database source type is hidden from the UI.
- **Backend settings endpoint** (`GET /settings`) exposes a new `database_source` feature flag in `enabled_features` so the frontend knows whether to show the option.
- **Backend staging endpoint** (`POST /PUT /ingestion/staging`) accepts `ImportType.DATABASE` with `db_schema` and `db_table` form fields, persists them on the IntegrityLink, and triggers the staging DAG with the appropriate source type.
- **IntegrityLink model** gets two new optional fields: `source_db_schema` and `source_db_table`.
- **User-friendly title**: for database sources, the default title is the table name (instead of the file name).
- **Dashboard navigation rules** (GSMEL-944) continue to apply unchanged — a database-sourced IntegrityLink behaves identically to file/URL/FTP sources from step 2 onward.
- **Re-edit flow**: when re-editing an existing database-sourced import, the schema and table fields are pre-filled.

## Capabilities

### New Capabilities
- `database-source-selection`: Frontend UI for selecting the database source type (radio button conditional on feature flag), entering schema and table name, and submitting to the backend.
- `database-source-backend`: Backend handling of the database source type — configuration, feature flag exposure, staging endpoint support, IntegrityLink persistence of schema/table, and Airflow DAG triggering with source type DATABASE.

### Modified Capabilities
<!-- No existing spec-level requirements are changing. The ingestion recurrence, dashboard navigation, and permission enforcement specs remain untouched. -->

## Impact

- **Frontend**: `DataSourceSelectorComponent` (+ template), `SourceData` interface, `DataImportWizardComponent` (title derivation), i18n translation files, settings service usage.
- **Backend**: `config.py` (new `POSTGRES_SOURCE_*` env vars), `settings_service.py` (new feature flag), `staging.py` (handle `ImportType.DATABASE`), `integrity_link.py` (new fields), `data_import.py` (new form fields).
- **Database**: Alembic migration adding `source_db_schema` and `source_db_table` columns to `integrity_link`.
- **ELT/Airflow**: Staging DAG changes are out of scope (GSMEL-869). The backend passes `source_type=DATABASE` and the schema/table info; the DAG is expected to handle it.
- **Dev environment**: A new connection line in docker-compose for the source database, plus a seed script with fake data.
- **No breaking API changes** — new fields are additive; existing source types are unaffected.
