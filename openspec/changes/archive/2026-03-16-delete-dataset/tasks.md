## 1. Database Verification

- [x] 1.1 Verify `datafeeder.integrity_link_rule` FK `integrity_link_id` has `ON DELETE CASCADE` → ✅ Confirmed present in `docker/datadir/database/130-datafeeder.sql` line 56

## 2. Backend — Service Layer

- [x] 2.1 Add `delete_dag()` method to `apps/backend/src/services/airflow_client.py` using the existing `DAGApi`; treat 404 as success, raise on other errors
- [x] 2.2 Add `delete_layer()` method to `apps/backend/src/services/geoserver.py`; treat 404 as success, log other errors
- [x] 2.3 Add `delete_record()` method to `apps/backend/src/services/metadata_service.py` (GeoNetwork); treat 404 as success, log other errors
- [x] 2.4 Create `apps/backend/src/services/dataset_deletion_service.py` with `delete_dataset(integrity_link, session)`:
  - If `schedule` is set: call `delete_dag()` — raise HTTP 500 on failure (blocking step)
  - Call `delete_layer()` — best-effort
  - Drop final table with `DROP TABLE IF EXISTS {org_schema}.{final_table_name}` — best-effort
  - Drop staging table with `DROP TABLE IF EXISTS staging.{staging_table_name}` — best-effort (usually already cleaned, captures failed ingestion orphans)
  - Call `delete_record()` — best-effort
  - Delete IntegrityLink from DB (cascade removes IntegrityLinkRule rows via FK constraint)

## 3. Backend — API Route

- [x] 3.1 Add `DELETE /{integrity_link_id}` handler to `apps/backend/src/api/routes/ingestion/integrity_link.py`:
  - Use `load_authorized_integrity_link(id, AccessLevel.OWNER_ONLY, ...)` for permission check
  - Delegate to `DatasetDeletionService.delete_dataset()`
  - Return HTTP 204 on success
- [x] 3.2 Run `make fix-all-python` and verify Pyright has no errors on changed files

## 4. Backend — Tests

- [x] 4.1 Add unit tests in `apps/backend/tests/services/` for `DatasetDeletionService`:
  - Happy path: with and without schedule
  - DAG delete failure → HTTP 500, other steps skipped
  - DAG 404 → treated as success
- [x] 4.2 Add API integration tests in `apps/backend/tests/api/` for `DELETE /ingestion/integrity-link/{id}`:
  - Owner can delete → 204
  - Non-owner → 403
  - Admin can delete any → 204
  - Unknown ID → 404

## 5. Frontend — API Client Update

- [x] 5.1 Add `DELETE /ingestion/integrity-link/{id}` to `apps/frontend/openapi.json` (or regenerate from backend)
- [x] 5.2 Run `ng-openapi-gen` to regenerate `apps/frontend/src/app/core/api/fn/ingestion/` with the new delete function

## 6. Frontend — UI: Hover-State Delete Button

**Figma Design**: [Hover-triggered delete button](https://www.figma.com/design/IwMxmE9G9D9StF2QLlR1uE/ingestion-donn%C3%A9es?node-id=127-4236&p=f&t=TebrnRWWgdhRvUGf-0) — includes hover states and interaction behaviors

**Implementation**: Use Figma MCP to extract exact visual specifications during implementation

- [x] 6.1 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.html`:
  - Add `(mouseenter)` / `(mouseleave)` binding on each row to track hovered row ID
  - Add trash icon button (`iconoirTrash` from `@ng-icons/iconoir`) visible only when `hoveredId === link.id`
  - Button triggers `deleteIntegrityLink(link.id)` on click
  - **Use Figma MCP to extract exact styling, positioning, and hover state styling from design**
- [x] 6.2 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.ts`:
  - Add `hoveredId = signal<string | null>(null)` for hover state
  - Add `deleting = signal<string | null>(null)` to prevent double-click
  - Implement `deleteIntegrityLink(id)`: call API, on success filter item from `integrityLinks` signal
  - Register `iconoirTrash` in `provideIcons()`
- [x] 6.3 Add i18n keys for delete action in `apps/frontend/translations/` (`dashboard.delete_dataset`, `dashboard.delete_dataset_confirm`)

## 7. Frontend — Tests

- [x] 7.1 Add/update vitest tests in `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.spec.ts`:
  - Trash icon hidden by default, visible on hover
  - Calls delete API on click
  - Removes item from list on success
  - Does not remove item on API failure

## 8. Validation

- [x] 8.1 Manual smoke test: delete a dataset as owner → verify row disappears and resources are removed
- [x] 8.2 Manual test: attempt delete as non-owner → verify 403 and row stays in list
- [x] 8.3 Manual test: delete a dataset with a recurrent schedule → verify DAG is removed from Airflow
- [ ] 8.4 Verify network trace for DAG deletion failure → backend returns 500, dataset remains in list (validates GSMEL-866 acceptance per Jira notes)

## 9. Post-Implementation Bug Fix — Stale Reconfigure After Admin Deletion

**Scenario**: An admin deletes a user's dataset while the user is on `intlink-layout`. The user then clicks "Reconfigure" in the sidebar, which navigates to `/import/:intlink_id`. The resolver calls `/api/ingestion/integrity-link/{id}`, gets a 404, but the wizard component renders without surfacing the error.

**Approach**: Resolver-layer redirect using Angular's `RedirectCommand`. A `createIntegrityLinkResolver(redirectOnError?)` factory produces both the shared resolver (no redirect) and a specialized `ImportIntegrityLinkResolver` (redirects to `/import` on error). Navigation is intercepted before the component mounts — no URL manipulation needed.

- [x] 9.1 Refactor `apps/frontend/src/app/core/resolvers/integrity-link.resolver.ts` into a `createIntegrityLinkResolver(redirectOnError?: string)` factory:
  - On error (catch), call `integrityLinkStore.clearIntegrityLink()` and, if `redirectOnError` is set, return `new RedirectCommand(router.parseUrl(redirectOnError))`
  - Export `IntegrityLinkResolver = createIntegrityLinkResolver()` (unchanged behavior for `intlink-layout` routes)
  - Export `IntegrityLinkResolverWithRedirect = createIntegrityLinkResolver('/import')` (redirects on 404/403/500 for `import/:intlink_id`)
  - Update `app.routes.ts` to use `IntegrityLinkResolverWithRedirect` for the `import/:intlink_id` route
  - Clear `loadError` on successful load in `IntegrityLinkStore.loadIntegrityLink()`
  - In `DataImportWizardComponent`, add `handleIntegrityLinkLoadError()`: reads `store.loadError()` on init, translates it into `importError`, then clears `store.loadError`
- [x] 9.2 Add i18n keys `import.datasetLoadError.not_found`, `import.datasetLoadError.forbidden`, `import.datasetLoadError.server_error` to all 8 translation files (en/fr/de/nl/it/pt/es/sk) with proper native-language translations
- [x] 9.3 Add tests:
  - `apps/frontend/src/app/core/resolvers/integrity-link.resolver.spec.ts` (new): 9 tests covering `IntegrityLinkResolver` (basic load, parent params, no id, error→undefined) and `IntegrityLinkResolverWithRedirect` (404/403/500→`RedirectCommand('/import')`, success, no id)
  - `DataImportWizardComponent` spec: 5 new tests in `handleIntegrityLinkLoadError` describe block; 79 tests total pass
