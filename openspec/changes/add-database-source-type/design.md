## Context

The ingestion tunnel currently supports three source types: file upload, URL, and FTP. The `ImportType` enum already includes `DATABASE` but the backend returns 501 for it. The frontend `DataSourceSelectorComponent` only knows about `file`, `url`, and `ftp`.

The platform already has two PostgreSQL connection configurations: `POSTGRES_DATAFEEDER_*` (metadata DB) and `POSTGRES_DATA_*` (staging/final DB). The database source type requires a third connection — pointing at the **external** database where the user's source data lives.

A `GET /settings` endpoint already returns `enabled_features` to the frontend, currently used for `scheduling` and `events` feature flags.

Figma mockup: `node-id=979-19443` in the ingestion design file.

## Goals / Non-Goals

**Goals:**
- Allow users to select "Database" as a source type when the platform has a source DB connection configured
- Accept schema + table name as free-text inputs (no live DB introspection)
- Persist schema/table on the IntegrityLink and pass them to the staging DAG
- Reuse the same pipeline from step 2 onward (preview, transform, process)

**Non-Goals:**
- Airflow staging DAG implementation for DATABASE source (GSMEL-869)
- Schema/table auto-completion or validation against the source DB at submission time (fail-fast is handled at staging DAG level)
- Connection testing from the backend
- Support for multiple source DB connections (V1: single connection)
- Support for custom SQL queries (only schema.table)

## Decisions

### D1: Source DB connection configuration via new env vars

**Decision:** Add `POSTGRES_SOURCE_*` env vars (`HOST`, `PORT`, `USER`, `PASSWORD`, `DB`) to `Settings` in `apps/backend/src/core/config.py`. All are optional and default to `None`.

**Rationale:** Follows the existing pattern for `POSTGRES_DATA_*`. The connection string is not stored per-user or per-import — it's a platform-level config, consistent with V1 constraint of a single DB connection. In production, the password comes from a k8s secret mounted as an env var.

**Alternatives considered:**
- Store connection per IntegrityLink: over-engineered for V1, and credential management per-import is complex.
- Reuse `POSTGRES_DATA_*`: conflates the staging/final DB with the source DB. They are conceptually different and often different servers.

### D2: Feature flag via existing `enabled_features` mechanism

**Decision:** The `SettingsService` checks whether `POSTGRES_SOURCE_HOST` is set (non-null). If so, it adds `"database_source"` to `enabled_features`. The frontend reads this flag to conditionally show the database radio button.

**Rationale:** Reuses the existing `GET /settings` → `enabled_features` pattern. No new endpoint needed. Existence check only — no connection test, keeping startup fast.

**Alternatives considered:**
- Dedicated `/capabilities` endpoint: unnecessary indirection for a single boolean.
- Frontend config file: would duplicate backend config and go stale.

### D3: IntegrityLink model — new `source_db_schema` and `source_db_table` columns

**Decision:** Add two nullable `VARCHAR(63)` columns to `integrity_link`: `source_db_schema` and `source_db_table`. They are populated only when `source_import_type = 'database'`.

**Rationale:** The existing `source_url` / `source_file_name` / `source_file_type` fields don't map well to a database source. Schema and table are distinct identifiers that the staging DAG needs. Keeping them as separate columns (vs. encoding in `source_url`) makes them queryable and avoids parsing.

**Migration:** Alembic migration adds two nullable columns — no data backfill needed, fully backwards-compatible.

### D4: Staging endpoint — extend existing `POST/PUT /ingestion/staging`

**Decision:** Add `db_schema` and `db_table` as optional `Form(...)` parameters to both `submit_staging` and `edit_staging`. When `type=database`, they are required (validated in `_process_import_source`). The `_ImportSourceResult.source` field is set to a synthetic identifier `db://{schema}/{table}` for logging/tracing purposes. No file upload or URL handling occurs.

**Rationale:** Reuses existing endpoints (API-first, same pipeline). The `source` string passed to Airflow is informational — the DAG reads schema/table from the IntegrityLink or from DAG conf params. No auth encryption needed since credentials come from platform config, not user input.

**File changes:**
- `apps/backend/src/api/routes/ingestion/staging.py` — extend `_process_import_source` and both route handlers
- `apps/backend/src/models/data_import.py` — no changes needed (ImportType.DATABASE already exists)

### D5: Frontend — extend `DataSourceSelectorComponent`

**Decision:** Add a `'database'` option to the radio group in `DataSourceSelectorComponent`. When selected, show two text inputs (schema, table). The `SourceData` interface gets `type: 'database'`, `dbSchema?: string`, `dbTable?: string`. The radio button is only rendered when `enabled_features` includes `"database_source"`.

**Rationale:** Keeps all source selection logic in the existing component. The settings service is already injected in the app config; the component just needs to check the feature flag.

**File changes:**
- `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` — extend form, interface, logic
- `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html` — add radio + inputs
- `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` — pass `db_schema`/`db_table` in FormData, set title from table name
- i18n files for new labels

### D6: User-friendly title defaults to table name

**Decision:** In `get_staging_metadata`, when `source_import_type == DATABASE`, the title falls back to `source_db_table` (instead of `source_file_name`). In the frontend wizard step 3, the title is pre-filled with the table name.

**Rationale:** Consistent with how file sources use the file name as default title. The table name is the most meaningful identifier for the user.

### D7: Dev environment — reuse shared DB with new connection line

**Decision:** In docker-compose, define a new `POSTGRES_SOURCE_*` env block pointing to the same PostgreSQL container but with a dedicated schema (e.g., `source_data`) containing seed tables. A SQL seed script creates the schema and populates it with fake geospatial data.

**Rationale:** Avoids adding another PostgreSQL container. The seed script is committed so any developer can reproduce the setup.

**File changes:**
- `docker-compose.yml` or `.env` — add `POSTGRES_SOURCE_*` env vars
- `scripts/` or `docker/` — SQL seed script for fake data

## Risks / Trade-offs

- **[No validation at submission]** The user can type any schema/table name. If it doesn't exist, the staging DAG will fail and the failure callback deletes the IntegrityLink. → Mitigation: This is intentional (fail-fast at staging). The user sees a clear error and can retry. Matches the stated architecture choice.

- **[Single connection per platform]** All users share the same source DB connection. → Mitigation: V1 constraint, documented as non-goal. Can be extended later with per-org or per-import connections.

- **[Schema/table SQL injection]** User-provided schema and table names could be injected into SQL. → Mitigation: Validate both fields with the existing `validate_table_name` pattern (alphanumeric + underscores, max 63 chars). The DAG should also validate before using them in queries.

- **[Migration on existing deployments]** Adding nullable columns is safe and non-breaking. → Mitigation: Standard Alembic `op.add_column` with nullable=True, no downtime.
