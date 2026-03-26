## Context

The ingestion tunnel currently supports three source types: file upload, URL, and FTP. The `ImportType` enum already includes `DATABASE` but the backend returns 501 for it. The frontend `DataSourceSelectorComponent` only knows about `file`, `url`, and `ftp`.

The platform already has two PostgreSQL connection configurations: `POSTGRES_DATAFEEDER_*` (metadata DB) and `POSTGRES_DATA_*` (staging/final DB). The database source type requires a third connection — pointing at the **external** database where the user's source data lives.

A `GET /settings` endpoint already returns `enabled_features` to the frontend, currently used for `scheduling` and `events` feature flags.

Figma mockup: `node-id=979-19443` in the ingestion design file.

## Goals / Non-Goals

**Goals:**
- Allow users to select "Database" as a source type when the platform has a source DB connection configured
- Accept schema + table name as free-text inputs (no live DB introspection)
- Encode schema/table in `source_url` as `db://{schema}/{table}` and pass them to the staging DAG
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

**Decision:** The `SettingsService` checks whether all five `POSTGRES_SOURCE_*` env vars (`HOST`, `PORT`, `USER`, `PASSWORD`, `DB`) are set and non-empty. If so, it adds `"database_source"` to `enabled_features`. The frontend reads this flag to conditionally show the database radio button.

**Rationale:** Reuses the existing `GET /settings` → `enabled_features` pattern. No new endpoint needed. Requiring all five vars avoids confusing errors when partial config is deployed (user sees the option but staging always fails due to missing connection fields). No connection test, keeping startup fast.

**Alternatives considered:**
- Dedicated `/capabilities` endpoint: unnecessary indirection for a single boolean.
- Frontend config file: would duplicate backend config and go stale.

### D3: No new IntegrityLink columns — encode schema/table in `source_url`

**Decision:** Do NOT add dedicated columns for schema and table. Instead, encode them in the existing `source_url` field as `db://{schema}/{table}`. Parse them back when needed (title fallback, re-edit pre-fill, DAG conf).

**Rationale:** Keeps the model unchanged — no schema migration, no SQL init script changes. The `db://` URI is a simple, parseable format (`schema, table = source_url[5:].split("/")`) that avoids adding columns for a single source type. No existing deployments to migrate, and for local dev the SQL init script stays untouched.

**Trade-off:** Consumers must know the `db://` URI convention. Acceptable for V1 with a single consumer (staging DAG). If querying by schema/table becomes important later, columns can be added.

### D4: Staging endpoint — extend existing `POST/PUT /ingestion/staging`

**Decision:** Add `db_schema` and `db_table` as optional `Form(...)` parameters to both `submit_staging` and `edit_staging`. When `type=database`, they are required (validated in `_process_import_source` with regex `^[a-z][a-z0-9_]{0,62}$`). The `_ImportSourceResult` fields are set as follows:
- `.source` = `db://{schema}/{table}` (informational trace)
- `.url` = `db://{schema}/{table}` (stored as `source_url` on IntegrityLink)
- `.source_file_name` = `None` (not a file)
- `.source_file_type` = `None`
- `.auth_enabled` = `False` (credentials are platform-level, not per-import)

No file upload or URL handling occurs.

**Rationale:** Reuses existing endpoints (API-first, same pipeline). The `source_url` string serves as both tracing identifier and the source of truth for schema/table. No auth encryption needed since credentials come from platform config, not user input.

**File changes:**
- `apps/backend/src/api/routes/ingestion/staging.py` — extend `_process_import_source` and both route handlers
- `apps/backend/src/models/data_import.py` — no changes needed (ImportType.DATABASE already exists)

### D4b: Guard `delete_temp_file` in `dag_success_callback`

**Decision:** In `dag_success_callback`, guard the `delete_temp_file(integrity_link.source_url)` call with an import type check: only call it when `source_import_type != ImportType.DATABASE`. Database sources store `db://{schema}/{table}` in `source_url`, which is not a file path.

**Rationale:** Without this guard, `delete_temp_file` would attempt to delete a non-existent path `db://...` on every successful database import. The existing try/except would catch it silently, but it's a code smell that logs spurious errors.

### D5: Frontend — extend `DataSourceSelectorComponent`

**Decision:** Add a `'database'` option to the radio group in `DataSourceSelectorComponent`. When selected, show two text inputs (schema, table). The `SourceData` interface gets `type: 'database'`, `dbSchema?: string`, `dbTable?: string`. The radio button is only rendered when `enabled_features` includes `"database_source"`.

**Rationale:** Keeps all source selection logic in the existing component. The settings service is already injected in the app config; the component just needs to check the feature flag.

**File changes:**
- `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` — extend form, interface, logic
- `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html` — add radio + inputs
- `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` — pass `db_schema`/`db_table` in FormData, set title from table name
- i18n files for new labels

### D6: User-friendly title defaults to table name (parsed from `source_url`)

**Decision:** In `get_staging_metadata`, the title fallback chain becomes: `integrity_title` → `source_file_name` → table name parsed from `source_url` (when `source_import_type == DATABASE`) → `""`. The table name is extracted by parsing the `db://{schema}/{table}` URI. In the frontend wizard step 3, the title is pre-filled with the table name.

**Rationale:** `source_file_name` is `None` for database sources (it's not a file), so the fallback reads the table name from `source_url` instead. This avoids repurposing `source_file_name` for non-file semantics. Consistent with how file sources use the file name as default title.

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

- **[No schema migration needed]** Schema/table are encoded in the existing `source_url` field, so no new columns and no migration. The SQL init script (`130-datafeeder.sql`) is unchanged.

- **[Recurrence for database sources]** Database sources are treated as remote sources and will show the recurrence selector (same as URL/FTP). This is intentional — the source table may receive new data over time. Note: recurring execution depends on the staging DAG supporting DATABASE source type (GSMEL-869).
