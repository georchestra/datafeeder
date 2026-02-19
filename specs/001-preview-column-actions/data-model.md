# Data Model: Actions sur les colonnes de l'aperçu tabulaire

**Feature Branch**: `001-preview-column-actions`
**Date**: 2026-02-18

## Entities

### 1. ColumnFilter (new — `data_manipulation`)

Represents a filter applied to a single column.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `operator` | `FilterOperator` (enum) | Required. One of: `exactly`, `contains`, `starts_with` | Filter comparison operator |
| `value` | `str` | Required. Non-empty. | Filter value to match against |

**Enum `FilterOperator`**: `exactly`, `contains`, `starts_with`

---

### 2. ColumnConfig (extended — `data_manipulation`)

Represents the transformation configuration for a single column. Extends existing `ColumnConfig` which only has `name`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `original_name` | `str` | Required. Immutable reference to original column. | Original column name from staging table |
| `new_name` | `str \| None` | Optional. Must not be empty if provided. Must be unique across all columns. | Renamed column name. `None` = keep original name. |
| `excluded` | `bool` | Default: `False` | Whether the column is excluded from output |
| `cast_type` | `CastType \| None` | Optional. One of: `boolean`, `numeric`, `text`, `date` | Target data type for casting. `None` = keep original type. |
| `filter` | `ColumnFilter \| None` | Optional. | Active filter on this column. `None` = no filter. |

**Enum `CastType`**: `boolean`, `numeric`, `text`, `date`

**Validation rules**:
- `new_name` must not be empty string (if provided)
- `new_name` uniqueness is enforced at the `IntegrityTransformation` level (cross-column validation)
- `excluded=True` disables all other actions (rename, cast, filter should be ignored for excluded columns during transformation)
- `filter` is ignored if `excluded=True`

**State transitions**:
- Active → Excluded: `excluded` set to `True`. Existing `new_name`, `cast_type`, `filter` are preserved in config but not applied.
- Excluded → Active: `excluded` set to `False`. Previously configured actions resume effect.

---

### 3. IntegrityTransformation (extended — `data_manipulation`)

Top-level transformation configuration. Stored in `IntegrityLink.integrity_transformation` as JSON.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `columns` | `list[ColumnConfig] \| None` | Optional. If `None`, all columns are included with no modifications. | Per-column transformation configuration |
| `force_projection` | `ForceProjection \| None` | Optional. Existing field. | Projection/CRS configuration |

**Validation rules**:
- All `original_name` values must be unique across `columns`
- All effective output names (= `new_name ?? original_name` for non-excluded columns) must be unique

---

### 4. TransformationConfiguration (new — backend `data_import.py`)

Backend Pydantic model built from the `StagingMetadata` request body. Extracts the transformation-relevant fields (`columns`, `force_projection`) from the full metadata and persists them to `integrity_link.integrity_transformation`. This is what both the backend preview and the ELT process DAG deserialize and pass to `apply_transformations`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `columns` | `list[ColumnConfig] \| None` | Optional | Column configurations (backend-side model) |
| `force_projection` | `ForceProjection \| None` | Optional | Projection config |

**Relationship to StagingMetadata**: `StagingMetadata` is the PUT request body (contains `title`, `file_type`, `columns`, `force_projection`). `TransformationConfiguration` is constructed from the `columns` and `force_projection` fields of `StagingMetadata` before being serialized to the DB. They are not the same model — `StagingMetadata` is API-facing, `TransformationConfiguration` is persistence-facing.

**Note**: `original_projection` is informational and read-only — it lives in `StagingMetadataResponse` only, never in `StagingMetadata` (the request body).

---

### 5. IntegrityLink (unchanged schema — backend model)

No DDL changes. The `integrity_transformation` JSON column already stores arbitrary JSON.

| Field | Type | Notes |
|-------|------|-------|
| `integrity_transformation` | `dict[str, Any] \| None` | Now stores serialized `TransformationConfiguration` instead of ad-hoc dict |

**Migration**: No database migration needed. The column is already `JSON`/`JSONB`. The change is in the Pydantic validation layer only.

---

## Relationships

```
IntegrityLink
  └── integrity_transformation (JSON column)
       └── TransformationConfiguration
            ├── columns: list[ColumnConfig]
            │     ├── original_name
            │     ├── new_name
            │     ├── excluded
            │     ├── cast_type (CastType enum)
            │     └── filter: ColumnFilter
            │           ├── operator (FilterOperator enum)
            │           └── value
            └── force_projection: ForceProjection
                  ├── type
                  ├── x_column
                  └── y_column
```

## Transformation Processing Order

When transformation is applied (both preview via `read_and_transform_data` and final ingestion via the Airflow process DAG):

1. **SQL — Exclude columns**: SELECT list omits columns where `excluded=True` (handled by `build_sql_column_ops` inside `read_data_from_postgis`).
2. **SQL — Filter rows**: WHERE clauses apply active filters via `cast(col, Text)` using auto-bound parameters (handled by `build_sql_column_ops`). Cumulate across columns (AND / intersection).
3. **SQL — LIMIT**: Applied after exclusion and filtering (preview only — process DAG reads full dataset with `limit=None`).
4. **Python — Rename columns**: Apply `new_name` where specified (handled by `rename_columns` in `apply_transformations`).
5. **Python — Cast types**: Apply `cast_type` conversions (handled by `cast_column_types` in `apply_transformations`; optional for preview display, required for final write).
6. **Python — Projection**: Apply `force_projection` (existing logic — geometry creation from x/y or CRS reprojection).

This order ensures:
- SQL steps reduce data volume before it reaches Python (excluded columns never fetched, filtered rows never transferred)
- LIMIT is applied to the already-filtered, already-narrowed result set (correct rows for preview)
- Renames happen before casts (cast operates on renamed columns, though column identity is by `original_name`)
- Projection is last (operates on the final column set)
