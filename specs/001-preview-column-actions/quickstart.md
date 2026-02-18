# Quickstart: Actions sur les colonnes de l'aperçu tabulaire

**Feature Branch**: `001-preview-column-actions`
**Date**: 2026-02-18

## Overview

This feature adds column-level actions (rename, remove, change type, filter) to the tabular preview in the data ingestion wizard. Users can configure transformations directly from the column headers, and the same transformation is applied during both preview and final ingestion.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  DataImportWizardComponent                                  │
│    ├── DatasetPreviewTableComponent (extended)              │
│    │     ├── ColumnHeaderComponent (new)                    │
│    │     │     ├── editable name input                      │
│    │     │     └── action button / restore icon             │
│    │     ├── ColumnActionMenuComponent (new)                │
│    │     │     ├── Remove action                            │
│    │     │     ├── Change type action                       │
│    │     │     └── Filter action                            │
│    │     └── ColumnFilterFormComponent (new)                │
│    └── DatasetConfigurationComponent (existing)             │
│                                                             │
│  Flow: user action → update config signal → debounce →      │  
│        PUT /metadata → GET /preview                         │
└─────────────────────────────────────────────────────────────┘
                          │   ▲
                    PUT   │   │ GET (raw=false|true)
                          ▼   │
┌─────────────────────────────────────────────────────────────┐
│                         Backend                             │
│  PUT /staging/{id}/metadata                                 │
│    → saves TransformationConfiguration to                   │
│      integrity_link.integrity_transformation                │
│                                                             │
│  GET /staging/{id}/preview?raw=false                        │
│    → reads saved config from DB                             │
│    → apply_transformations(data, config)                    │
│    → returns transformed preview                            │
│                                                             │
│  GET /staging/{id}/preview?raw=true                         │
│    → returns original staging data (no transformations)     │
└─────────────────────────────────────────────────────────────┘
                          │
            Same IntegrityTransformation config
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     ELT (Airflow)                           │
│  process_dag → read_transform_write_task                    │
│    → reads integrity_transformation from DAG params         │
│    → IntegrityTransformation(**dict)                        │
│    → apply_transformations(data, config)                    │
│    → writes to final table                                  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Data Layer (`data_manipulation` library)

**Files to modify**:
- `libs/data_manipulation/src/data_manipulation/models.py` — Extend `ColumnConfig`, add `FilterOperator`, `CastType`, `ColumnFilter` enums/models
- `libs/data_manipulation/src/data_manipulation/transformation/transform.py` — Add column action processing (filter, exclude, rename, cast)

**Files to create**:
- `libs/data_manipulation/src/data_manipulation/transformation/transform_columns.py` — Column filtering, exclusion, renaming, and type casting functions
- `libs/data_manipulation/tests/test_column_actions.py` — Unit tests for all column action transformations

**Key changes**:
1. Add `FilterOperator`, `CastType`, `ColumnFilter` to models
2. Extend `ColumnConfig` with `original_name`, `new_name`, `excluded`, `cast_type`, `filter`
3. Implement `apply_column_filters()`, `exclude_columns()`, `rename_columns()`, `cast_column_types()` in new transform_columns module
4. Update `apply_transformations()` to call column action functions before projection

### Phase 2: Backend API

**Files to modify**:
- `apps/backend/src/models/data_import.py` — Update `ColumnMetadata`→`ColumnConfig`, add `ColumnFilter`, `FilterOperator`, `CastType` models, update `StagingMetadata` to use new column config
- `apps/backend/src/api/routes/ingestion/staging.py` — Refactor PUT metadata and GET preview endpoints

**Key changes**:
1. PUT metadata: accept full transformation config, persist to `integrity_transformation`
2. GET preview: remove `projection`/`x_column`/`y_column` query params, add `raw` boolean param, read config from DB
3. GET metadata: include saved column configurations in response

### Phase 3: Frontend

**Files to modify**:
- `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` — Update config flow (PUT on each change, GET preview with raw fallback)
- `apps/frontend/src/app/shared/components/dataset-preview-table/dataset-preview-table.component.ts` — Add column headers with actions
- `apps/frontend/src/app/shared/components/dataset-configuration/dataset-configuration.component.ts` — Remove projection config from here (now in column actions if needed)

**Files to create**:
- `apps/frontend/src/app/shared/components/column-header/column-header.component.ts` — Editable column name + action button
- `apps/frontend/src/app/shared/components/column-action-menu/column-action-menu.component.ts` — Dropdown with remove/type/filter actions
- `apps/frontend/src/app/shared/components/column-filter-form/column-filter-form.component.ts` — Filter operator + value form

**Key changes**:
1. Regenerate API client (`npm run generate-api` after backend changes)
2. Column header with editable name (debounced) and action menu button
3. Action menu with remove, change type, filter options + visual indicators
4. Filter form with operator select, value input, validate/delete buttons
5. Update wizard to chain PUT metadata → GET preview on each config change
6. Error handling: fallback to `raw=true` preview on transformation errors

## Development Workflow

```bash
# 1. Start the stack
make up-full

# 2. Implement data_manipulation changes
cd libs/data_manipulation
# ... edit models.py, transform.py, transform_columns.py
uv run pytest tests/

# 3. Implement backend changes
cd apps/backend
# ... edit data_import.py, staging.py
uv run pytest tests/

# 4. Regenerate frontend API client
cd apps/frontend
npm run generate-api

# 5. Implement frontend components
npm run start
npm run test:ut
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Column config per-column (not per-action) | Simpler state model, easier to track which actions apply to which column |
| Preview reads saved config from DB | Guarantees preview = ingestion transformation (FR-021) |
| `raw` param on GET preview | Error recovery — display original data when config breaks preview |
| Filter operates on text representation | Matches spec: operators (exactly, contains, starts_with) are text-based |
| Processing order: filter → exclude → rename → cast → projection | Filters on original data, excludes before wasted computation, rename before cast for clarity |
| No NgRx — Angular signals only | Wizard state is transient, not global app state |
