# Tasks: Actions sur les colonnes de l'aperçu tabulaire

**Input**: Design documents from `/specs/001-preview-column-actions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/staging-api.yaml, quickstart.md

**Tests**: Explicitly requested for data-manipulation (unit tests) and frontend (unit tests per component/service).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Backend/library work is foundational (Phases 2-3), frontend work is per-story (Phases 4-9).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Architecture Summary

**Filter + exclusion → SQL level** (inside `read_data_from_postgis`):
- `build_sql_column_ops(columns, table)` returns `(select_cols, where_clauses)`: SELECT list omits excluded columns; WHERE clauses apply active filters via `cast(col, Text)` using **SQLAlchemy native comparison operators** (`.like()`, `==`) which auto-bind values — no string interpolation of user input.
- The resulting `Select` object is passed **directly** to `gpd.read_postgis(query, con=engine, ...)` / `pd.read_sql(query, engine)` — **never compiled to a string with `literal_binds=True`**, which would bypass parameter binding and risk SQL injection.
- Applied before `LIMIT` for preview (limit=10) and without `LIMIT` for process DAG (full dataset).

**Rename + cast → Python in-memory** (after data is fetched):
- `rename_columns()` and `cast_column_types()` operate on the DataFrame returned from the DB.
- Cast is optional for preview display (UI renders everything as strings); required for final write in process DAG.

## Notes

- Use Figma MCP to extract component specs from https://www.figma.com/design/IwMxmE9G9D9StF2QLlR1uE/ingestion-donn%C3%A9es?node-id=655-22462 during frontend implementation
- Use Tailwind CSS classes only (no custom CSS), geonetwork-ui components (gn-ui-button, gn-ui-text-input) where possible, Angular Material otherwise
- Git commit after each phase with a descriptive message
- Pause for manual review after each phase
- Remove all speckit implementation comments at the end
- Use skills if needed (.agents/skills)

---

## Phase 1: Setup

**Purpose**: Verify the development environment is ready and all tooling works.

### Infrastructure

- [X] T001a Start the full stack with `make up-full` (builds libs, starts all services including GeoServer/GeoNetwork). Verify gateway at http://localhost:8080/ (credentials: `testadmin/testadmin`), frontend at http://localhost:8080/datakern/, backend API docs at http://localhost:8080/datakern-backend/docs, Airflow at http://localhost:8080/airflow (credentials: `airflow/airflow`)

### Python (backend + data_manipulation + ELT)

- [X] T001b Run Python tests: `make test-libs` (data_manipulation) and `make test-backend` (backend) — both must pass
- [X] T001c Run Python linting and formatting checks: `make check-all-python` (runs `ruff check .`, `ruff format . --check`, `pyright .` across the monorepo workspace including backend, data_manipulation, and ELT)
- [X] T001d Verify Python auto-fix commands work: `make fix-all-python` (runs `ruff check . --fix`, `ruff format .`)

### Frontend

- [X] T001e Run frontend tests: `cd apps/frontend && npm run test:ut:ci` (vitest single run)
- [X] T001f Run frontend lint and format check: `cd apps/frontend && npm run lint && npm run format:check`
- [X] T001g Verify frontend format fix: `cd apps/frontend && npm run format`

**Checkpoint**: All services accessible via gateway URLs. All Python tests pass. All frontend tests pass. Linting/formatting checks pass for both Python and frontend.

---

## Phase 2: Foundational — Shared Library (data_manipulation)

**Purpose**: Extend the transformation models and functions in `libs/data_manipulation` to support column actions. **Architecture**: filter and exclusion are handled at the SQL level in `read_data_from_postgis` (both for preview with LIMIT 10 and process DAG without LIMIT); rename and cast are applied in-memory in Python after the data is read. This is the single source of truth for transformations used by both backend preview and ELT process DAG, guaranteeing US6 consistency (FR-021).

**⚠️ CRITICAL**: Backend and frontend work cannot begin until this phase is complete.

- [X] T002 Extend transformation models with `FilterOperator`, `CastType`, `ColumnFilter` enums/models and update `ColumnConfig` with `original_name`, `new_name`, `excluded`, `cast_type`, `filter` fields in `libs/data_manipulation/src/data_manipulation/models.py`
- [X] T003 Update public exports to include `FilterOperator`, `CastType`, `ColumnFilter`, `build_sql_column_ops`, and `read_and_transform_data` in `libs/data_manipulation/src/data_manipulation/__init__.py`
- [X] T004 Create in-memory column transformation functions (`rename_columns`, `cast_column_types`) in `libs/data_manipulation/src/data_manipulation/transformation/transform_columns.py`. **Filters and exclusion are not handled here** — they are applied at the SQL level via `read_data_from_postgis` (see T004a/T004b), both for preview (with `LIMIT`) and for the process DAG (without `LIMIT`). Only rename and cast operate on DataFrames already returned from the database.
- [X] T004a Create `build_sql_column_ops(columns: list[ColumnConfig], table: Table) -> tuple[list[Column], list[ColumnElement]]` in `libs/data_manipulation/src/data_manipulation/transformation/filter_sql.py`. Returns `(select_cols, where_clauses)` where: **select_cols** is the list of `table.c[original_name]` for every non-excluded column (excluded columns omitted from SELECT entirely); **where_clauses** contains one SQLAlchemy condition per non-excluded column with an active `filter`, using `cast(table.c[original_name], Text)` from `sqlalchemy` — **use SQLAlchemy's native operators which automatically create bound parameters**: `FilterOperator.EXACTLY` → `== filter.value`, `FilterOperator.CONTAINS` → `.like(f'%{filter.value}%')`, `FilterOperator.STARTS_WITH` → `.like(f'{filter.value}%')`. Never interpolate filter values into raw SQL fragments or use `text()` with f-strings. Returns `(all columns, [])` when `columns` is empty.
- [X] T004b Extend `read_data_from_postgis` in `libs/data_manipulation/src/data_manipulation/ingestion.py` to accept an optional `columns: list[ColumnConfig] | None = None` parameter. When provided, call `build_sql_column_ops(columns, table)` and: (1) build the SELECT with `select(*select_cols)` instead of `select(table)`; (2) apply `query = query.where(*where_clauses)`. Both before any `.limit(limit)`. **Security critical**: pass the final `Select` object **directly** to `gpd.read_postgis(query, con=engine, geom_col=...)` or `pd.read_sql(query, engine)` — both accept `Selectable` natively in SQLAlchemy 2.x. **Remove `literal_binds=True` compilation entirely** — pass `Select` directly in all paths; if driver issues surface they will be caught by T006a integration tests.
- [X] T004c Create `read_and_transform_data(table_name: str, engine: Engine, schema: str | None = None, config: IntegrityTransformation | None = None, limit: int | None = None) -> gpd.GeoDataFrame | pd.DataFrame` in `libs/data_manipulation/src/data_manipulation/ingestion.py`. This is the **single pipeline entry point** that combines `read_data_from_postgis(..., columns=config.columns if config else None, limit=limit)` with `apply_transformations(data, config)` in one call. When `config is None`, returns raw data unchanged. Both the backend GET preview (`limit=10`, `config` from DB) and the Airflow process DAG (`limit=None`, `config` from DAG params) call this function identically — this is the architectural guarantee for FR-021 consistency. Business logic stays in `data_manipulation`, the route handler only handles HTTP concerns.
- [X] T005 Update `apply_transformations` in `libs/data_manipulation/src/data_manipulation/transformation/transform.py` to call only `rename_columns` then `cast_column_types` (optionally). Filter and exclusion are no longer responsibilities of `apply_transformations` — they are handled at the SQL level inside `read_data_from_postgis`. `apply_transformations` is now an internal step called by `read_and_transform_data`; direct callers should migrate to `read_and_transform_data`.
- [X] T005b Update `read_transform_write_task` in `apps/elt/dags/task_groups/transformation.py` to call `read_and_transform_data(staging_table_name, engine, staging_schema, transformation_config, limit=None)` instead of the current two-step `read_data_from_postgis` + `apply_transformations`. Add `read_and_transform_data` to the `from data_manipulation import` statement and remove the separate `read_data_from_postgis` + `apply_transformations` calls.
- [X] T006 [P] Write unit tests for `build_sql_column_ops` in `libs/data_manipulation/tests/test_column_actions.py`: (1) each filter operator produces the correct SQLAlchemy expression type (BinaryExpression with `Cast(Text)` operand); (2) **verify no user value is inlined into the SQL text** — compile with `compile_kwargs={"literal_binds": False}` and assert the compiled SQL contains `:param` placeholders, not the literal filter value; (3) excluded columns absent from select_cols; (4) non-excluded columns without filter produce no where clause; (5) `excluded=True` columns generate no where clause even if they have a filter; (6) empty column list returns `(all_cols, [])`
- [X] T006a [P] Write integration-style unit tests for `read_data_from_postgis` with `columns` param in `libs/data_manipulation/tests/test_column_actions.py`: (1) with a SQLite/PostgreSQL test fixture, verify `limit` rows returned all match the active filter (not a pre-limited then filtered subset); (2) excluded columns absent from returned DataFrame; (3) `limit=None` returns all matching rows; (4) no `columns` param returns all rows; (5) **verify the underlying `pd.read_sql` / `gpd.read_postgis` call receives a `Select` object, not a compiled SQL string** — mock the read function and assert `isinstance(call_args[0], Select)`
- [X] T006b [P] Write unit tests for `read_and_transform_data` in `libs/data_manipulation/tests/test_column_actions.py`: (1) `config=None` returns unmodified raw data; (2) end-to-end: filter + exclude applied at SQL level, rename + cast applied in Python, matching result of calling `read_data_from_postgis` + `apply_transformations` separately; (3) same config with `limit=10` vs `limit=None` returns filtered subset vs full filtered dataset respectively — confirming LIMIT is applied after filters
- [X] T007 [P] Write unit tests for `rename_columns` and `cast_column_types` (rename changes column names; excluded columns are already absent — no-op; cast converts types boolean/numeric/text/date; `cast_type=None` leaves column unchanged; note: cast is **optional for preview display** but required for final write in process DAG) in `libs/data_manipulation/tests/test_column_actions.py`
- [X] T008 [P] Write unit tests for updated `apply_transformations` (rename+cast only; empty config returns unchanged data; backward compatibility with old ColumnConfig format; excluded columns not present in input DataFrame because already filtered at SQL level) in `libs/data_manipulation/tests/test_column_actions.py`.

**Checkpoint**: `uv run pytest libs/data_manipulation/tests/` passes. `build_sql_column_ops` returns correct SELECT column list and WHERE clauses. `read_data_from_postgis` with `columns` applies exclusion and filters at SQL level before LIMIT. `read_and_transform_data` end-to-end pipeline works for both preview (limit=10) and full-read (limit=None) modes. Airflow `transformation.py` uses `read_and_transform_data` (T005b). `rename_columns` and `cast_column_types` operate correctly on DataFrames. Backward compatibility preserved.

---

## Phase 3: Foundational — Backend API Refactoring

**Purpose**: Refactor the staging backend to separate configuration persistence (PUT metadata) from data preview (GET preview with `raw` param). Update Pydantic models to use explicit typed schemas instead of untyped dicts.

**⚠️ CRITICAL**: Frontend API regeneration and all frontend work depend on this phase.

- [X] T009 Update backend Pydantic models: replace `ColumnMetadata` with extended `ColumnConfig` (matching data_manipulation schema), add `FilterOperator`, `CastType`, `ColumnFilter` models, update `StagingMetadata` to use new `ColumnConfig` in `apps/backend/src/models/data_import.py`
- [X] T010 Add explicit Pydantic model type annotation for `integrity_transformation` field documentation in `apps/backend/src/models/integrity_link.py`
- [X] T011 Refactor PUT metadata endpoint to persist full transformation configuration (columns with rename/exclude/cast/filter + force_projection) to `integrity_link.integrity_transformation` on each call. Build a `TransformationConfiguration` from the `StagingMetadata` request body fields and serialize it to the DB. Return a clear error message (suitable for frontend alert-box display) when column name validation fails (empty or duplicate names) in `apps/backend/src/api/routes/ingestion/staging.py`
- [X] T012 Refactor GET preview endpoint in `apps/backend/src/api/routes/ingestion/staging.py`: **remove `projection`, `x_column`, `y_column` query parameters entirely** — ALL transformation configuration (columns AND force_projection) is loaded exclusively from `integrity_link.integrity_transformation` saved by PUT metadata, never from query parameters. Add `raw: bool = Query(False)` parameter. When `raw=false`: deserialize `TransformationConfiguration` from `integrity_link.integrity_transformation` and call `read_and_transform_data(staging_table_name, engine, schema, config, limit=10)` — this single call handles SQL-level exclusion and filtering (via `read_data_from_postgis`) plus in-memory rename, cast, and projection (via `apply_transformations`). The route handler only converts the result to tabular/GeoJSON response format. When `raw=true`: call `read_and_transform_data(staging_table_name, engine, schema, config=None, limit=10)` to return original data without transformations.
- [X] T013 Update GET metadata endpoint to include saved column configurations from `integrity_transformation` in the response in `apps/backend/src/api/routes/ingestion/staging.py`
- [X] T013b [P] The `DatasetConfigurationComponent` force_projection dropdown **stays in place** — no relocation or removal. Wire its change output into the existing config update signal in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` so that any change to the force_projection dropdown triggers PUT metadata (with the full config including updated `force_projection`) → GET preview, identical to how column actions flow.
- [X] T014 Regenerate frontend API client by running `curl http://localhost:8080/datakern-backend/openapi.json > apps/frontend/openapi.json && npm run generate-api` in `apps/frontend/` after the backend is updated and running

**Checkpoint**: Backend endpoints work with new schema. Frontend API client regenerated. Manual test: PUT metadata with column config (including force_projection) → GET preview (`raw=false`) calls `read_and_transform_data` and returns transformed data; GET preview (`raw=true`) returns original data. No `projection`/`x_column`/`y_column` query params exist. force_projection dropdown change also triggers PUT → GET preview flow. PUT with empty/duplicate column name returns clear error message.

---

## Phase 4: US5 — Accéder au menu des actions d'une colonne (Priority: P1)

**Goal**: Users can click an action button in each column header to open a dropdown menu listing available actions (remove, change type, filter). Visual indicators show when actions are configured. The wizard config flow is refactored to chain PUT metadata → GET preview on each change.

**Independent Test**: Click the action button in a column header → dropdown menu appears with action labels. No actions configured → no indicator on button. Close menu → menu disappears.

### Tests for US5

- [ ] T015 [P] [US5] Write unit tests for `ColumnActionMenuComponent`: menu renders action labels (remove, change type, filter); emits action selection event; shows indicator dot per configured action in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.spec.ts`
- [ ] T016 [P] [US5] Write unit tests for `ColumnHeaderComponent`: renders action button; shows indicator dot when actions configured; emits menu open event in `apps/frontend/src/app/shared/components/column-header/column-header.component.spec.ts`
- [ ] T017 [P] [US5] Write unit tests for refactored config flow in `DataImportWizardComponent`: PUT metadata called on config change; GET preview called after PUT; `raw=true` fallback on error in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.spec.ts`

### Implementation for US5

- [ ] T018 [P] [US5] Create `ColumnActionMenuComponent` (presentational, OnPush): dropdown menu with action items (remove, change type, filter), indicator dots per action, emits selected action via `@Output()` in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.ts`
- [ ] T019 [P] [US5] Create `ColumnHeaderComponent` (presentational, OnPush): action button with indicator dot, `@Input()` for column config, `@Output()` for action events in `apps/frontend/src/app/shared/components/column-header/column-header.component.ts`
- [ ] T020 [US5] Refactor `DatasetPreviewTableComponent` to use `ColumnHeaderComponent` in column headers, pass column config and handle action events in `apps/frontend/src/app/shared/components/dataset-preview-table/dataset-preview-table.component.ts`
- [ ] T021 [US5] Refactor `DataImportWizardComponent` config flow: build column config signal from metadata, chain PUT metadata → GET preview with `switchMap`, implement `raw=true` fallback on preview error (pipe through `timeout(5000)`; on `TimeoutError` or HTTP error call GET preview with `raw=true` and display raw data + error message — do NOT roll back the PUT already persisted). The config signal includes all transformation fields: `columns` AND `force_projection` (from `DatasetConfigurationComponent`). On preview error, show raw data + error message without reverting the config panel. In `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts`

**Checkpoint**: Action button visible in each column header. Clicking opens dropdown with action labels. No actions trigger changes yet (actions wired in subsequent phases). Config flow chains PUT→GET correctly.

---

## Phase 5: US1 — Renommer une colonne (Priority: P1)

**Goal**: Users can rename a column directly from the header by editing an inline text input. Rename is debounced (400ms) before triggering PUT metadata → GET preview. No visual indicator for rename. No undo mechanism.

**Independent Test**: Edit a column name in the header input → after 400ms debounce → preview refreshes with renamed column. Empty name rejected. Duplicate name rejected.

### Tests for US1

- [ ] T022 [P] [US1] Write unit tests for inline rename in `ColumnHeaderComponent`: input displays column name; emits rename event on change; rejects empty name; rejects duplicate name in `apps/frontend/src/app/shared/components/column-header/column-header.component.spec.ts`
- [ ] T023 [P] [US1] Write unit tests for debounce behavior: rename triggers PUT after 400ms debounce; rapid typing only sends last value in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.spec.ts`

### Implementation for US1

- [ ] T024 [US1] Add inline editable name input (text field visible by default) to `ColumnHeaderComponent` with name validation (empty, duplicate). Display validation errors using `alert-box-component` (same pattern as other validation errors in the wizard) in `apps/frontend/src/app/shared/components/column-header/column-header.component.ts`
- [ ] T025 [US1] Implement rename debounce (400ms via `debounceTime`) and wire rename events to column config update → PUT metadata → GET preview. On PUT error (e.g. duplicate/empty name), display the backend error message in the alert-box in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts`

**Checkpoint**: Column names are editable inline. Debounced rename triggers preview refresh. Empty/duplicate names are rejected with alert-box error message from backend.

---

## Phase 6: US2 — Retirer et restaurer une colonne (Priority: P1)

**Goal**: Users can remove a column via the action menu. Removed columns appear greyed out with a restore icon replacing the action button. All actions (including inline rename) are disabled on removed columns. Restoring re-enables all actions.

**Independent Test**: Open menu → click "Remove" → column greyed out, action button becomes restore icon, name not editable. Click restore icon → column active again, menu available.

### Tests for US2

- [ ] T026 [P] [US2] Write unit tests for remove/restore behavior: excluded column renders greyed; action button shows restore icon; inline name input disabled for excluded column; restore emits event in `apps/frontend/src/app/shared/components/column-header/column-header.component.spec.ts`
- [ ] T027 [P] [US2] Write unit tests for excluded column in preview table: greyed-out styling applied to column cells; remove action triggers config update in `apps/frontend/src/app/shared/components/dataset-preview-table/dataset-preview-table.component.spec.ts`

### Implementation for US2

- [ ] T028 [US2] Add "remove" action handler to `ColumnActionMenuComponent` and implement greyed-out column state (Tailwind `opacity-50` + `pointer-events-none` on data cells). Handle edge case where all columns are excluded: display a warning message in the preview area (FR edge case EC3) in `apps/frontend/src/app/shared/components/dataset-preview-table/dataset-preview-table.component.ts`
- [ ] T029 [US2] Implement restore icon replacing action button when column is excluded, disable inline name editing for excluded columns in `apps/frontend/src/app/shared/components/column-header/column-header.component.ts`
- [ ] T030 [US2] Wire remove/restore events to column config update (`excluded: true/false`) → PUT metadata → GET preview in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts`

**Checkpoint**: Removing a column greys it out. Restore icon appears. Inline editing disabled. Restoring re-enables everything. Preview refreshes on each action.

---

## Phase 7: US3 — Changer le type d'une colonne (Priority: P2)

**Goal**: Users can change a column's data type via the action menu by selecting from a predefined list (boolean, numeric, text, date). Type change is immediate (no debounce). Visual indicators show configured type on action button and menu item.

**Independent Test**: Open menu → click "Change type" → type list appears → select "numeric" → preview refreshes with cast applied. Indicator dot visible on action button.

### Tests for US3

- [ ] T031 [P] [US3] Write unit tests for type selection: type list shows 4 options (boolean, numeric, text, date); selecting type emits event; indicator shows current type in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.spec.ts`

### Implementation for US3

- [ ] T032 [US3] Add type selection submenu to `ColumnActionMenuComponent` with predefined types (boolean, numeric, text, date) and indicator for current selection in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.ts`
- [ ] T033 [US3] Wire type change event to column config update (`cast_type`) → PUT metadata → GET preview in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts`

**Checkpoint**: Type selection works. Indicator visible on action button and menu item. Preview shows cast data.

---

## Phase 8: US4 — Filtrer une colonne (Priority: P2)

**Goal**: Users can filter a column via the action menu. Filter form shows operator selector (exactly, contains, starts_with) and value input. Filter requires explicit validation (button click). Validated filters are read-only with a delete button. New filter replaces existing. Filters across columns cumulate (AND/intersection). Visual indicator on action button when filter is active.

**Independent Test**: Open menu → click "Filter" → select "contains" → type value → click validate → preview shows filtered rows. Apply filter on second column → only matching rows shown. Delete filter → preview returns to unfiltered. Empty result shows empty state.

### Tests for US4

- [ ] T034 [P] [US4] Write unit tests for `ColumnFilterFormComponent`: renders operator dropdown and value input; validate button emits filter; validated filter is read-only; delete button emits remove event; new filter replaces old in `apps/frontend/src/app/shared/components/column-filter-form/column-filter-form.component.spec.ts`
- [ ] T035 [P] [US4] Write unit tests for filter integration: filter action in menu opens filter form; active filter shows indicator; cumulative filters across columns in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.spec.ts`

### Implementation for US4

- [ ] T036 [US4] Create `ColumnFilterFormComponent` (presentational, OnPush): operator dropdown (exactly, contains, starts_with), value text input, validate button, read-only display for active filter, delete button in `apps/frontend/src/app/shared/components/column-filter-form/column-filter-form.component.ts`
- [ ] T037 [US4] Add filter action to `ColumnActionMenuComponent` linking to `ColumnFilterFormComponent`, show active filter indicator in `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.ts`
- [ ] T038 [US4] Wire filter validate/delete events to column config update → PUT metadata → GET preview, handle empty result state (FR-020) in `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts`

**Checkpoint**: Filter form works with all 3 operators. Validated filters are read-only. Delete removes filter. Cumulative filters across columns work. Empty result shows message. Indicator on button when filter active.

---

## Phase 9: US6 — Cohérence de la transformation + Polish (Priority: P1)

**Purpose**: Verify end-to-end consistency between preview and final ingestion. Clean up code.

- [ ] T039 [US6] Verify transformation consistency: configure rename + type change + filter + remove in preview, trigger process DAG, verify final table in GeoServer matches preview transformations exactly (manual integration test)
- [ ] T040 Remove all speckit-specific implementation comments from all modified files across `libs/data_manipulation/`, `apps/backend/src/`, and `apps/frontend/src/`
- [ ] T041 Run linting and formatting: `make fix-all-python` for backend and data_manipulation, `npm run format` and `npm run lint` for frontend
- [ ] T042 Run all test suites: `uv run pytest libs/data_manipulation/tests/`, `uv run pytest apps/backend/tests/`, `npm run test:ut` in `apps/frontend/`
- [ ] T043 Run quickstart.md validation scenario end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — verify environment first
- **Phase 2 (Shared Library)**: Depends on Phase 1 — **BLOCKS all subsequent phases**
- **Phase 3 (Backend API)**: Depends on Phase 2 — **BLOCKS all frontend phases**
- **Phase 4 (US5 — Menu)**: Depends on Phase 3 — **BLOCKS US2, US3, US4** (they need the menu)
- **Phase 5 (US1 — Rename)**: Depends on Phase 4 (needs ColumnHeaderComponent + wizard config flow)
- **Phase 6 (US2 — Remove)**: Depends on Phase 4 (needs menu for remove action)
- **Phase 7 (US3 — Type)**: Depends on Phase 4 (needs menu for type submenu)
- **Phase 8 (US4 — Filter)**: Depends on Phase 4 (needs menu for filter action)
- **Phase 9 (US6 + Polish)**: Depends on all previous phases

### User Story Dependencies

- **US5 (Menu)**: No story dependency — foundational UI infrastructure
- **US1 (Rename)**: Depends on US5 (shares ColumnHeaderComponent + wizard config flow)
- **US2 (Remove/Restore)**: Depends on US5 (needs menu for remove action)
- **US3 (Type Change)**: Depends on US5 (needs menu for type submenu); independent of US1, US2
- **US4 (Filter)**: Depends on US5 (needs menu for filter action); independent of US1, US2, US3
- **US6 (Consistency)**: No frontend dependency — satisfied by shared library (Phase 2); verified after all stories

### Parallel Opportunities (after Phase 4)

Once Phase 4 (US5) is complete:

- **US1** (rename) can run in parallel with **US2** (remove) — they edit different aspects of ColumnHeaderComponent
- **US3** (type) can run in parallel with **US4** (filter) — they add different submenus
- **US5** → then **US1 ∥ US2** → then **US3 ∥ US4** → then **US6 + Polish**

### Within Each Phase

- Tests (when included) are written first but can be created in parallel (marked [P])
- Implementation tasks follow test creation
- Wizard integration (config flow wiring) is always the last task in each story phase

---

## Parallel Example: Phase 4 (US5)

```bash
# Launch test creation in parallel:
Task T015: "Unit tests for ColumnActionMenuComponent"
Task T016: "Unit tests for ColumnHeaderComponent"
Task T017: "Unit tests for DataImportWizardComponent config flow"

# Then launch component creation in parallel:
Task T018: "Create ColumnActionMenuComponent"
Task T019: "Create ColumnHeaderComponent"

# Then sequential integration:
Task T020: "Refactor DatasetPreviewTableComponent"
Task T021: "Refactor DataImportWizardComponent config flow"
```

---

## Implementation Strategy

### MVP First (Phases 1-5: Setup + Library + Backend + US5 + US1)

1. Complete Phase 1: Setup — verify environment
2. Complete Phase 2: Shared library — column action models + transforms + tests
3. Complete Phase 3: Backend — API refactoring + client regeneration
4. Complete Phase 4: US5 — Column action menu + wizard config flow
5. Complete Phase 5: US1 — Inline rename with debounce
6. **STOP and VALIDATE**: Test renaming columns end-to-end. Preview shows renamed columns. Config persists across page reloads.

### Incremental Delivery

1. Phases 1-3 → Foundation ready (all backend/library work done)
2. - Phase 4 (US5) → Menu infrastructure visible in UI
3. - Phase 5 (US1) → Rename works → **First usable MVP**
4. - Phase 6 (US2) → Remove/restore works → Structural editing complete
5. - Phase 7 (US3) → Type change works → Data quality features added
6. - Phase 8 (US4) → Filter works → Full feature complete
7. - Phase 9 (US6 + Polish) → Consistency verified, code cleaned up
