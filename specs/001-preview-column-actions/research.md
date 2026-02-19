# Research: Actions sur les colonnes de l'aperçu tabulaire

**Feature Branch**: `001-preview-column-actions`
**Date**: 2026-02-18

## R1: Current `integrity_transformation` JSON Structure

**Decision**: Create an explicit Pydantic model `TransformationConfiguration` that replaces the untyped `dict[str, Any]` currently used in `IntegrityLink.integrity_transformation`.

**Rationale**: The current `integrity_transformation` column is a raw JSON dict with no schema validation. It currently stores `{ "columns": [...], "force_projection": {...} }` but needs to also store column actions (rename, remove, type cast, filter). An explicit model ensures validation at the API boundary and consistency between preview and final ingestion.

**Current state**:
- `IntegrityLink.integrity_transformation` is `dict[str, Any] | None` (untyped JSON column)
- Backend `edit_staging_metadata` stores `columns` and `force_projection` into it
- Backend `get_staging_preview` builds `IntegrityTransformation` from **query parameters** (`projection`, `x_column`, `y_column`), NOT from the saved config
- Process DAG receives `integrity_transformation` dict and deserializes it into `IntegrityTransformation(columns, force_projection)` in the ELT task group
- `data_manipulation.IntegrityTransformation` has `columns: list[ColumnConfig] | None` and `force_projection: ForceProjection | None`
- `ColumnConfig` currently only has `name: str` — no rename, type, remove, or filter fields

**Alternatives considered**:
- Keep untyped dict: rejected because it leads to drift between preview and ingestion configs
- Store each action separately (multiple DB columns): rejected because the config is inherently nested and a JSON column is more flexible

---

## R2: Separation Between Configuration Persistence and Data Preview

**Decision**: Refactor the PUT metadata and GET preview endpoints to implement a clear separation:
- **PUT metadata** persists the full `TransformationConfiguration` JSON to `integrity_transformation` on each user modification
- **GET preview** reads the saved configuration from DB and applies it; adds a `raw` query parameter (`raw=false` default → transformed preview, `raw=true` → original data without transformations)
- Remove transformation query parameters (`projection`, `x_column`, `y_column`) from the GET preview endpoint

**Rationale**: Currently, the preview endpoint receives transformation parameters as query params, creating a split between what's saved (PUT) and what's previewed (GET params). This makes it impossible to guarantee FR-021 (preview transformation = ingestion transformation). By reading from the same saved config, both preview and process DAG use the same source of truth.

**Alternatives considered**:
- Keep query params on preview and add `raw` param: rejected because it maintains the split between saved config and preview config
- Send full config as POST body for preview: rejected because GET is semantically correct for read-only preview and allows URL sharing/caching

---

## R3: Column Actions Data Model

**Decision**: Extend `ColumnConfig` with `original_name`, `new_name`, `excluded`, `cast_type`, and `filter` fields. The transformation pipeline will process these actions during both preview and final ingestion.

**Rationale**: The spec requires four column actions: rename, remove, change type, and filter. Each action is per-column and must be stored in the transformation configuration. Using a flat per-column model keeps the structure simple and aligns with the existing `columns` list pattern.

**Model design**:
```python
class FilterOperator(str, Enum):
    EXACTLY = "exactly"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"

class ColumnFilter(BaseModel):
    operator: FilterOperator
    value: str

class ColumnConfig(BaseModel):
    original_name: str          # original column name (immutable reference)
    new_name: str | None        # renamed column name (None = keep original)
    excluded: bool = False       # True = column removed from output
    cast_type: str | None       # "boolean", "numeric", "text", "date" or None
    filter: ColumnFilter | None  # active filter or None
```

**Alternatives considered**:
- Separate lists for renames, excludes, type changes, filters: rejected because it's harder to track which actions apply to which column
- Action log (list of operations): rejected because it's harder to reconcile — per-column state is simpler

---

## R4: `apply_transformations` Extension in `data_manipulation`

**Decision**: Refactor the processing pipeline so that filter and exclusion are SQL-level operations in `read_data_from_postgis`, and only rename and cast remain as in-memory Python operations in `apply_transformations`. A new function `build_sql_column_ops` builds the SELECT column list (excluding removed columns) and WHERE clauses (filter conditions on text cast) from the `ColumnConfig` list.

**Rationale**: Applying filter and exclusion at SQL level guarantees that LIMIT is applied to already-filtered, already-narrowed rows — both for the preview (LIMIT 10) and the process DAG (no LIMIT). This is correct-by-construction: the backend and the DAG both call `read_data_from_postgis(columns=config.columns)` and get back a DataFrame that already reflects filters and exclusion. Python only handles rename and cast, which are cheap in-memory operations.

**Processing order**:
1. SQL: Exclude columns from SELECT list (non-excluded columns only)
2. SQL: Apply filters as WHERE clauses (text-cast comparison: exactly / contains / starts_with)
3. SQL: Apply LIMIT (preview only — process DAG reads full dataset)
4. Python: Rename columns (`new_name` replaces `original_name` in DataFrame)
5. Python: Cast types (boolean / numeric / text / date) — optional for preview display, required for final write
6. Python: Apply projection/geometry transformations (existing logic)

**Note on cast for preview**: Since the preview displays data as strings in the UI, skipping cast for preview is acceptable. Cast is required in the process DAG where the final table needs properly-typed columns.

**Security implementation notes**:
- Filter values are passed to SQLAlchemy's native comparison operators (`.like()`, `==`) which **automatically create bound parameters** — the full `%value%` string becomes a positional/named bind parameter, never interpolated into the SQL text.
- Never use `text()` with f-strings for filter conditions.
- The resulting `Select` object is passed **directly** to `gpd.read_postgis(query, con=engine, ...)` or `pd.read_sql(query, engine)` (both accept `Selectable` natively in SQLAlchemy 2.x / pandas 2.x). **Do not compile with `literal_binds=True`** when user-provided filter values are present — this inlines values into the SQL string and bypasses parameter binding.

**Alternatives considered**:
- Apply filter and exclusion as Python DataFrame operations: rejected because it causes LIMIT to be applied before filtering, returning wrong rows
- Apply column actions in the backend only (not in data_manipulation): rejected because it would break Constitution §III (shared library) and FR-021 (transformation consistency)

---

## R5: Frontend Architecture for Column Actions

**Decision**: Implement column actions as a sub-component of the existing `DatasetPreviewTableComponent`, with a column header action menu using Angular Material overlays. State management will use Angular signals (no NgRx needed for this per-wizard transient state).

**Rationale**: The wizard is transient (not global app state), and signals are sufficient for component-local state management. The column actions are tightly coupled to the preview table, making them a natural extension of `DatasetPreviewTableComponent`. Angular Material `MatMenuModule` provides the dropdown menu pattern needed for the column action list.

**Component breakdown**:
- `ColumnHeaderComponent` (presentational) — renders column name (editable input), action button with indicator, restore icon for excluded columns
- `ColumnActionMenuComponent` (presentational) — dropdown menu with actions (remove, change type, filter), indicators per action
- `ColumnFilterFormComponent` (presentational) — operator selector + value input + validate/delete buttons

**Alternatives considered**:
- Build as entirely separate component outside the table: rejected because column headers are tightly coupled to the table structure
- Use NgRx for state: rejected per Constitution §VI guidance (signals for component-local state; NgRx for app-wide state)

---

## R6: Debounce Strategy for Frontend Config Updates

**Decision**: Use RxJS `debounceTime(400)` for text input changes (rename, filter value) and immediate dispatch for discrete actions (remove, restore, type change, filter operator). Each config change triggers PUT metadata → GET preview sequence.

**Rationale**: The spec requires debounce for text inputs (FR-016) and immediate application for other actions (FR-015). 400ms is within the 300-500ms "reasonable" range mentioned in assumptions. Chaining PUT → GET ensures the preview always reflects the persisted config.

**Alternatives considered**:
- Debounce all actions: rejected because discrete actions (clicks) should be instant per FR-015
- Use switchMap to cancel in-flight previews: adopted — only the latest preview matters, earlier requests can be cancelled

---

## R7: Raw Preview Fallback for Error Recovery (FR-019 Clarification)

**Decision**: Add `raw: bool = Query(False)` parameter to GET preview. When `raw=true`, skip all transformations and return the original staging data. When `raw=false` (default), read saved config from DB and apply transformations. **FR-019 is implemented as raw data fallback** (not a revert to previous config state).

**Rationale**: If the user's configuration breaks the preview (wrong projection, invalid type cast, etc.), the frontend shows the raw (untransformed) staging data as fallback. This is simpler and more reliable than caching the previous successful preview state, because the PUT has already persisted the new config. The raw fallback allows the user to see the original data and fix their configuration.

**Error handling flow**:
1. Frontend calls GET preview (default `raw=false`)
2. If backend returns error (500), frontend calls GET preview with `raw=true`
3. Frontend displays raw data + error message from failed transformed preview
4. User can fix configuration and retry

**Note on FR-019**: The spec says "revenir à l'état précédant la requête" — interpreted as showing raw data (the baseline before any transformations) rather than caching the previous transformed preview. The PUT has already persisted the new config, so a true "revert" would require either rolling back the PUT or caching the previous response. The raw fallback approach is simpler and provides a consistent recovery path.

---

## R8: Process DAG Configuration Consistency

**Decision**: Update the process DAG to call `read_data_from_postgis(columns=config.columns, limit=None)` instead of reading all data and filtering in Python. After reading, apply rename and cast via `apply_transformations`. This mirrors the preview pipeline exactly — same SQL logic, just without LIMIT.

**Rationale**: FR-021/FR-022 require identical transformation between preview and ingestion. Using the same `read_data_from_postgis(columns=...)` call in both code paths guarantees that exclusion and filtering are performed identically in both cases. The only difference is LIMIT (10 for preview, none for process DAG).

**Changes needed to process DAG flow**:
1. Pass `config.columns` to `read_data_from_postgis` instead of reading `SELECT *` then filtering in Python
2. Call `apply_transformations(df, config)` for rename + cast only
3. Write result to final table

The `IntegrityTransformation` model is deserialized identically in both paths from `integrity_link.integrity_transformation` JSON.
