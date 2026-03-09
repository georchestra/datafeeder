## 1. Database Prerequisite

- [ ] 1.1 Verify `datakern.integrity_link_rule` FK `integrity_link_id` has `ON DELETE CASCADE` in Alembic migrations
- [ ] 1.2 If missing, create an Alembic migration in `apps/backend/` to add `ON DELETE CASCADE` to `integrity_link_rule.integrity_link_id`

## 2. Backend — Service Layer

- [ ] 2.1 Add `delete_dag()` method to `apps/backend/src/services/airflow_client.py` using the existing `DAGApi`; treat 404 as success, raise on other errors
- [ ] 2.2 Add `delete_layer()` method to `apps/backend/src/services/geoserver.py`; treat 404 as success, log other errors
- [ ] 2.3 Add `delete_record()` method to `apps/backend/src/services/metadata_service.py` (GeoNetwork); treat 404 as success, log other errors
- [ ] 2.4 Create `apps/backend/src/services/jdd_deletion_service.py` with `delete_jdd(integrity_link, session)`:
  - If `schedule` is set: call `delete_dag()` — raise HTTP 500 on failure (blocking step)
  - Call `delete_layer()` — best-effort
  - Drop `{org_schema}.{final_table_name}` with `DROP TABLE IF EXISTS` — best-effort
  - Call `delete_record()` — best-effort
  - Delete IntegrityLink from DB (cascade removes IntegrityLinkRule rows)

## 3. Backend — API Route

- [ ] 3.1 Add `DELETE /{integrity_link_id}` handler to `apps/backend/src/api/routes/ingestion/integrity_link.py`:
  - Use `load_authorized_integrity_link(id, AccessLevel.OWNER_ONLY, ...)` for permission check
  - Delegate to `JddDeletionService.delete_jdd()`
  - Return HTTP 204 on success
- [ ] 3.2 Run `make fix-all-python` and verify Pyright has no errors on changed files

## 4. Backend — Tests

- [ ] 4.1 Add unit tests in `apps/backend/tests/services/` for `JddDeletionService`:
  - Happy path: with and without schedule
  - DAG delete failure → HTTP 500, other steps skipped
  - DAG 404 → treated as success
- [ ] 4.2 Add API integration tests in `apps/backend/tests/api/` for `DELETE /ingestion/integrity-link/{id}`:
  - Owner can delete → 204
  - Non-owner → 403
  - Admin can delete any → 204
  - Unknown ID → 404

## 5. Frontend — API Client Update

- [ ] 5.1 Add `DELETE /ingestion/integrity-link/{id}` to `apps/frontend/openapi.json` (or regenerate from backend)
- [ ] 5.2 Run `ng-openapi-gen` to regenerate `apps/frontend/src/app/core/api/fn/ingestion/` with the new delete function

## 6. Frontend — UI: Hover-State Delete Button

- [ ] 6.1 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.html`:
  - Add `(mouseenter)` / `(mouseleave)` binding on each row to track hovered row ID
  - Add trash icon button (`iconoirTrash` from `@ng-icons/iconoir`) visible only when `hoveredId === link.id`
  - Button triggers `deleteIntegrityLink(link.id)` on click
- [ ] 6.2 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.ts`:
  - Add `hoveredId = signal<string | null>(null)` for hover state
  - Add `deleting = signal<string | null>(null)` to prevent double-click
  - Implement `deleteIntegrityLink(id)`: call API, on success filter item from `integrityLinks` signal
  - Register `iconoirTrash` in `provideIcons()`
- [ ] 6.3 Add i18n keys for delete action in `apps/frontend/translations/` (`dashboard.delete_jdd`, `dashboard.delete_jdd_confirm`)

## 7. Frontend — Tests

- [ ] 7.1 Add/update vitest tests in `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.spec.ts`:
  - Trash icon hidden by default, visible on hover
  - Calls delete API on click
  - Removes item from list on success
  - Does not remove item on API failure

## 8. Validation

- [ ] 8.1 Manual smoke test: delete a JDD as owner → verify row disappears and resources are removed
- [ ] 8.2 Manual test: attempt delete as non-owner → verify 403 and row stays in list
- [ ] 8.3 Manual test: delete a JDD with a recurrent schedule → verify DAG is removed from Airflow
- [ ] 8.4 Verify network trace for DAG deletion failure → backend returns 500, JDD remains in list (validates GSMEL-866 acceptance per Jira notes)
