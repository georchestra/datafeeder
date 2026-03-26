## 1. Backend Configuration (foundation)

- [ ] 1.1 [P] Add `POSTGRES_SOURCE_*` env vars to `apps/backend/src/core/config.py` — `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB` (all optional, default `None`)
- [ ] 1.2 [P] Add `"database_source"` feature flag in `apps/backend/src/services/settings_service.py` — check that ALL five `POSTGRES_SOURCE_*` vars are set and non-empty (not just HOST)

---
**Checkpoint:** `GET /settings` returns `database_source` in `enabled_features` when all five env vars are configured.

## 2. Backend Staging Endpoint

- [ ] 2.1 Add `db_schema` and `db_table` optional Form parameters to `submit_staging` and `edit_staging` in `apps/backend/src/api/routes/ingestion/staging.py`
- [ ] 2.2 Implement `ImportType.DATABASE` case in `_process_import_source` — validate both fields required and matching regex `^[a-z][a-z0-9_]{0,62}$`, set `source` and `url` to `db://{schema}/{table}`, set `source_file_name=None`, `source_file_type=None`, `auth_enabled=False`
- [ ] 2.3 Guard `delete_temp_file` in `dag_success_callback` — only call it when `source_import_type != ImportType.DATABASE` (database sources store `db://` URI in `source_url`, not a file path)
- [ ] 2.4 On edit (`edit_staging`): when switching from database to file/URL/FTP, the new source URL naturally replaces the `db://` URI in `source_url`. When switching to database, `source_url` is set to `db://{schema}/{table}` and `source_file_type` is cleared.
- [ ] 2.5 Update title fallback in `get_staging_metadata` — extend the fallback chain to: `integrity_title` → `source_file_name` → table name parsed from `source_url` (when `source_import_type == DATABASE`, parse `db://{schema}/{table}`) → `""`

---
**Checkpoint:** Backend accepts `type=database` with schema/table, persists via `source_url`, and triggers staging DAG. API can be tested with curl.

## 3. Backend Tests

- [ ] 3.1 [P] Unit test for `settings_service` — verify `"database_source"` in `enabled_features` when ALL five `POSTGRES_SOURCE_*` vars are set, absent when any is missing
- [ ] 3.2 [P] Unit test for schema/table regex validation — accept valid names (`public`, `my_data_table`), reject invalid ones (`Public`, `123table`, `my-schema`, empty)
- [ ] 3.3 [P] Integration test for `POST /ingestion/staging` with `type=database` — verify IntegrityLink created with `source_url=db://{schema}/{table}`, `source_import_type=database`, `source_file_name=None`, `source_file_type=None`, no encrypted credentials
- [ ] 3.4 [P] Integration test for `PUT /ingestion/staging/{id}` — verify edit from file to database (source_url becomes `db://`), and database to file (source_url becomes file path)
- [ ] 3.5 [P] Integration test for `GET /ingestion/staging/{id}/metadata` — verify title fallback to table name parsed from `source_url` for database source
- [ ] 3.6 [P] Integration test for `dag_success_callback` — verify `delete_temp_file` is NOT called when `source_import_type == DATABASE`

---
**Checkpoint:** Backend is fully tested.

## 4. Frontend Source Selector

- [ ] 4.1 Extend `SourceData` interface in `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` — add `type: 'database'`, `dbSchema?: string`, `dbTable?: string`
- [ ] 4.2 Add `database` option to the radio form group, conditionally rendered based on `database_source` feature flag from `SettingsService`
- [ ] 4.3 Add schema and table text input fields to template `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html`, shown when `database` radio is selected
- [ ] 4.4 Add form controls for `dbSchema` and `dbTable` to the reactive form, emit via `sourceChanged`
- [ ] 4.5 Handle radio change to/from `database` — clear irrelevant fields on switch
- [ ] 4.6 Add i18n translation keys for database source labels (schema, table, radio label) in translation files

---
**Checkpoint:** Source selector UI shows database option when feature flag is present.

## 5. Frontend Wizard Integration

- [ ] 5.1 Update `DataImportWizardComponent` (`apps/frontend/src/app/shared/components/data-import-wizard/`) to pass `db_schema` and `db_table` in the FormData when submitting to staging endpoint
- [ ] 5.2 Extend `validSource` computed property to handle `type === 'database'`: return `true` when both `dbSchema` and `dbTable` are non-empty after trimming. This gates the "Next" button via `cantConfigureDataset()`.
- [ ] 5.3 Update title pre-fill logic in step 3 — use table name as default for database sources
- [ ] 5.4 Handle re-edit: when loading an existing database-sourced IntegrityLink, parse `source_url` (`db://{schema}/{table}`) to pre-fill radio selection and schema/table fields. **Important:** when re-editing a database-sourced IntegrityLink but the `database_source` feature flag is no longer in `enabled_features`, the database radio button must still be shown for that edit session (check both the feature flag AND the existing IntegrityLink's `source_import_type`).
- [ ] 5.5 Regenerate or update OpenAPI client types if needed (`apps/frontend/src/app/core/api/`)

---
**Checkpoint:** Full frontend flow works end-to-end (source selection → staging → preview → process).

## 6. Frontend Tests

- [ ] 6.1 [P] Vitest for `DataSourceSelectorComponent` — database radio hidden when feature flag absent, shown when present
- [ ] 6.2 [P] Vitest for `DataSourceSelectorComponent` — schema/table fields shown/hidden on radio change, values emitted correctly
- [ ] 6.3 [P] Vitest for `DataSourceSelectorComponent` — switching between source types clears previous fields
- [ ] 6.4 [P] Vitest for wizard — `validSource` returns true only when both schema and table are non-empty/non-whitespace for database type
- [ ] 6.5 [P] Vitest for wizard — re-edit pre-fills database fields correctly (parsed from `source_url`)
- [ ] 6.6 [P] Vitest for wizard — re-edit shows database radio even when feature flag is absent (existing database-sourced IntegrityLink)

---
**Checkpoint:** Frontend is fully tested.

## 7. Dev Environment

- [ ] 7.1 Add `POSTGRES_SOURCE_*` env vars (all five: HOST, PORT, USER, PASSWORD, DB) to docker-compose / `.env` pointing to the shared PostgreSQL container
- [ ] 7.2 Create SQL seed script (e.g., `scripts/seed_source_db.sql`) that creates a source schema with fake geospatial data (at least one table with a geometry column)
- [ ] 7.3 Wire seed script into docker-compose init (or document manual execution)

---
**Checkpoint:** Developer can run `docker-compose up` and test the full database source flow locally.
