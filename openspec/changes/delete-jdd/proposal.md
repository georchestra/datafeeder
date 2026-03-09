## Why

Users need the ability to delete their own datasets (JDDs) from the dashboard to complete the dataset lifecycle management workflow. This allows owners to clean up datasets that are no longer needed, removing all associated resources (GeoServer layer, GeoNetwork metadata, data table, Airflow DAG) in a single operation.

## What Changes

- **New DELETE endpoint** `DELETE /api/jdd/{id}` — removes the JDD and triggers full resource cleanup
- **Permission check** — only the JDD owner or an admin can delete; returns 403 for unauthorized attempts
- **Cascading cleanup** — deletion triggers sequential removal of: Airflow DAG (if recurrent), GeoServer layer, data table, GeoNetwork record, integrity link (via `ON DELETE CASCADE`)
- **Error handling** — DAG deletion is the only blocking step: if it fails, the backend returns an error and no further cleanup is performed; subsequent steps are best-effort without rollback
- **Frontend delete action** — a trash icon button appears on row hover in the JDD list; confirmation handled via the existing UI pattern; disappears from list on success
- **Admin override** — administrators can delete any JDD regardless of ownership

## Capabilities

### New Capabilities

- `delete-jdd`: Full-stack capability for deleting a JDD from the dashboard, including ownership-based permission enforcement, cascading resource cleanup, and hover-triggered UI action

### Modified Capabilities

<!-- No existing spec-level behavior changes required -->

## Impact

- **Backend**: New route in `api/routes/`, new service method in `services/`, integrity_link `ON DELETE CASCADE` must be confirmed on relevant FK relationships
- **Frontend**: `features/` dashboard component updated with hover-state delete button; NgRx action/reducer/effect for delete; API service call to new endpoint
- **ELT**: No DAG code changes; the backend calls the Airflow API to delete a DAG run/schedule
- **Database**: Verify `integrity_link` and related tables have `ON DELETE CASCADE` on `jdd` FK; add migration if missing
- **GeoServer / GeoNetwork**: Backend calls their respective APIs at deletion time; no structural changes to those systems
