## 1. Backend Configuration & Model (foundation)

- [ ] 1.1 [P] Add `POSTGRES_SOURCE_*` env vars to `apps/backend/src/core/config.py` — `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB` (all optional, default `None`)
- [ ] 1.2 [P] Add `"database_source"` feature flag in `apps/backend/src/services/settings_service.py` — check `POSTGRES_SOURCE_HOST` is set and non-empty
- [ ] 1.3 [P] Add `source_db_schema` and `source_db_table` nullable VARCHAR(63) fields to `IntegrityLink` model in `apps/backend/src/models/integrity_link.py`, with SQL-injection-safe validators (pattern `^[a-z][a-z0-9_]{0,62}$`)
- [ ] 1.4 Create Alembic migration adding `source_db_schema` and `source_db_table` columns to `integrity_link` table

---
**Checkpoint:** Backend config, model, and migration are in place. `GET /settings` returns `database_source` when configured.

## 2. Backend Staging Endpoint

- [ ] 2.1 Add `db_schema` and `db_table` optional Form parameters to `submit_staging` and `edit_staging` in `apps/backend/src/api/routes/ingestion/staging.py`
- [ ] 2.2 Implement `ImportType.DATABASE` case in `_process_import_source` — validate both fields required, set `source` to `db://{schema}/{table}`, set `source_file_name` to table name, no auth encryption
- [ ] 2.3 Persist `source_db_schema` and `source_db_table` on IntegrityLink creation in `submit_staging`
- [ ] 2.4 Persist `source_db_schema` and `source_db_table` on IntegrityLink update in `edit_staging`, clear them when switching away from database type
- [ ] 2.5 Update title fallback in `get_staging_metadata` — use `source_db_table` when `source_import_type == DATABASE` and no `integrity_title` or `source_file_name`

---
**Checkpoint:** Backend accepts `type=database` with schema/table, persists, and triggers staging DAG. API can be tested with curl.

## 3. Backend Tests

- [ ] 3.1 [P] Unit test for `settings_service` — verify `"database_source"` in `enabled_features` when `POSTGRES_SOURCE_HOST` is set, absent when not set
- [ ] 3.2 [P] Unit test for IntegrityLink model — validate `source_db_schema` and `source_db_table` validators accept valid names and reject invalid ones
- [ ] 3.3 [P] Integration test for `POST /ingestion/staging` with `type=database` — verify IntegrityLink creation with correct fields
- [ ] 3.4 [P] Integration test for `PUT /ingestion/staging/{id}` — verify edit from file to database and database to file clears/sets fields correctly
- [ ] 3.5 [P] Integration test for `GET /ingestion/staging/{id}/metadata` — verify title fallback to table name for database source

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
- [ ] 5.2 Update wizard "Next" button validation — disable when type is `database` and schema or table is empty/whitespace
- [ ] 5.3 Update title pre-fill logic in step 3 — use table name as default for database sources
- [ ] 5.4 Handle re-edit: when loading an existing database-sourced IntegrityLink, pre-fill radio selection and schema/table fields
- [ ] 5.5 Regenerate or update OpenAPI client types if needed (`apps/frontend/src/app/core/api/`)

---
**Checkpoint:** Full frontend flow works end-to-end (source selection → staging → preview → process).

## 6. Frontend Tests

- [ ] 6.1 [P] Vitest for `DataSourceSelectorComponent` — database radio hidden when feature flag absent, shown when present
- [ ] 6.2 [P] Vitest for `DataSourceSelectorComponent` — schema/table fields shown/hidden on radio change, values emitted correctly
- [ ] 6.3 [P] Vitest for `DataSourceSelectorComponent` — switching between source types clears previous fields
- [ ] 6.4 [P] Vitest for wizard — Next button disabled when schema/table empty, enabled when filled
- [ ] 6.5 [P] Vitest for wizard — re-edit pre-fills database fields correctly

---
**Checkpoint:** Frontend is fully tested.

## 7. Dev Environment

- [ ] 7.1 Add `POSTGRES_SOURCE_*` env vars to docker-compose / `.env` pointing to the shared PostgreSQL container
- [ ] 7.2 Create SQL seed script (e.g., `scripts/seed_source_db.sql`) that creates a source schema with fake geospatial data (at least one table with a geometry column)
- [ ] 7.3 Wire seed script into docker-compose init (or document manual execution)

---
**Checkpoint:** Developer can run `docker-compose up` and test the full database source flow locally.
