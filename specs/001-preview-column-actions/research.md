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

**Decision**: Extend `apply_transformations` to handle the new column actions (rename, exclude, cast, filter) in addition to the existing projection transformation. The `IntegrityTransformation` model in `data_manipulation` will be updated to match the new `ColumnConfig` schema.

**Rationale**: The `data_manipulation` library is the single source of truth for transformations (Constitution §III). Both the backend preview endpoint and the ELT process DAG call `apply_transformations`. Adding column actions here guarantees FR-021 (preview = final transformation).

**Processing order**:
1. Filter rows (based on column filters — cumulative intersection)
2. Exclude columns (mark excluded columns for removal)
3. Rename columns
4. Cast types
5. Apply projection/geometry transformations (existing logic)
6. Drop excluded columns from output

**Alternatives considered**:
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

## R7: Raw Preview Fallback for Error Recovery

**Decision**: Add `raw: bool = Query(False)` parameter to GET preview. When `raw=true`, skip all transformations and return the original staging data. When `raw=false` (default), read saved config from DB and apply transformations.

**Rationale**: If the user's configuration breaks the preview (wrong projection, invalid type cast, etc.), the frontend needs a way to still display the original data alongside error messages so the user can debug their configuration. This is explicitly described in the user prompt as "critical".

**Error handling flow**:
1. Frontend calls GET preview (default `raw=false`)
2. If backend returns error (500), frontend calls GET preview with `raw=true`
3. Frontend displays raw data + error message from failed transformed preview
4. User can fix configuration and retry

---

## R8: Process DAG Configuration Consistency

**Decision**: The process DAG already reads `integrity_link.integrity_transformation` and passes it to `apply_transformations`. After refactoring, the same `TransformationConfiguration` Pydantic model will be used, ensuring the serialized JSON stored in `integrity_transformation` is deserialized identically for both preview and final ingestion.

**Rationale**: FR-021/FR-022 require identical transformation between preview and ingestion. Since both code paths use `data_manipulation.apply_transformations` with the same config from `integrity_transformation`, this is achieved by construction.

**No changes needed to process DAG flow** — it already:
1. Reads `integrity_transformation` from IntegrityLink
2. Passes it as `IntegrityTransformation(**dict)` to `apply_transformations`
3. Writes result to final table

The only change is that `IntegrityTransformation` will now include column actions (rename, exclude, cast, filter) in addition to projection.
