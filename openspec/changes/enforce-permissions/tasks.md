## 1. Backend: GeorchestraContext Enhancement

- [x] 1.1 Add `organization` field to `GeorchestraContext` in `apps/backend/src/services/georchestra.py`, extracted from the `sec-org` request header
- [x] 1.2 Update `GeorchestraContext` tests to cover the new `organization` field

## 2. Backend: Permission Checking Dependency

- [x] 2.1 Create a reusable permission-checking dependency in `apps/backend/src/core/security.py` that accepts a required access level (METADATA_READ, METADATA_WRITE, OWNER_ONLY) and the dataset ID, loads the IntegrityLink, checks admin/owner/group-rule, and raises 403 on failure
- [x] 2.2 Write unit tests for the permission-checking dependency covering all access levels, admin bypass, owner bypass, group rule matching, WRITE-implies-READ, and 403 rejection in `apps/backend/tests/services/` or `apps/backend/tests/api/`

## 3. Backend: Dataset List Visibility Filtering (US1)

- [x] 3.1 Update the `list_integrity_links` query in `apps/backend/src/api/routes/ingestion/integrity_links.py` to include datasets where the user's organization has a METADATA rule (LEFT JOIN / EXISTS on IntegrityLinkRule)
- [x] 3.2 Add `access_level` computed field to the list response model in `apps/backend/src/models/integrity_link.py`, returning OWNER/ADMIN/WRITE/READ per item
- [x] 3.3 Write tests for dataset list visibility: owner sees own datasets, group with METADATA READ sees datasets, group without rules does not see datasets, admin sees all

## 4. Backend: Endpoint Authorization (US2)

- [x] 4.1 Add permission check to `GET /ingestion/integrity-link/{id}` requiring METADATA_WRITE, owner, or admin in `apps/backend/src/api/routes/ingestion/integrity_link.py`
- [x] 4.2 Add permission check to rules endpoints (`GET/PUT/DELETE /ingestion/integrity-link/{id}/rules*`) requiring OWNER_ONLY in `apps/backend/src/api/routes/ingestion/integrity_link.py`
- [x] 4.3 Add permission check to staging endpoints (`GET/PUT /ingestion/staging/{id}/metadata`, `GET /ingestion/staging/{id}/preview`) requiring METADATA_WRITE or OWNER_ONLY as appropriate in `apps/backend/src/api/routes/ingestion/staging.py`
- [x] 4.4 Add permission check to process endpoint (`POST /ingestion/process/`) — update existing owner check to also allow admin in `apps/backend/src/api/routes/ingestion/process.py`
- [x] 4.5 Add permission check to metadata proxy in `apps/backend/src/api/routes/geonetwork.py` requiring METADATA_WRITE, owner, or admin when the request references a dataset
- [x] 4.6 Add permission check to airflow/events endpoints (`GET /airflow/dags/*/runs*`, logs) requiring OWNER_ONLY in `apps/backend/src/api/routes/airflow.py`
- [x] 4.7 [P] Write integration tests for each protected endpoint verifying 403 for unauthorized users and 200 for authorized users

## 5. Frontend: Dataset List Permission-Aware Rendering (US3)

- [x] 5.1 Update the generated API client to include the new `access_level` field in `IntegrityLinkListItem` (regenerate from OpenAPI or update manually)
- [x] 5.2 Update `integrity-link-list.component.ts` in `apps/frontend/src/app/features/integrity-link-list/` to disable row click when `access_level` is `READ` (dataset visible but not navigable)
- [x] 5.3 Add visual indicator (e.g., greyed-out row or lock icon) for read-only datasets in the list
- [x] 5.4 Write vitest tests for the list component verifying clickable vs non-clickable rows based on access level

## 6. Frontend: Sidebar Conditional Navigation (US4, US5, US6)

- [x] 6.1 Update `intlink-layout.component.ts` and `.html` in `apps/frontend/src/app/layout/` to conditionally enable/disable sidebar links based on user's permission level on the loaded dataset
- [x] 6.2 For METADATA_WRITE users (non-owner): enable only "Metadata Sheet" link; disable authorizations, events, recurrence, reconfigure, delete
- [x] 6.3 For OWNER and ADMIN users: enable all sidebar links and actions
- [x] 6.4 Hide reconfigure and delete actions entirely for non-owner, non-admin users
- [x] 6.5 Display backend 403 errors as-is when users manually navigate to unauthorized URLs (no custom redirect or guard)
- [x] 6.6 Write vitest tests for the layout component verifying sidebar state for each permission level

## 7. Verification

- [ ] 7.1 Run full backend test suite (`make test-backend`) — all tests pass
- [ ] 7.2 Run full frontend test suite (`npm test` in `apps/frontend/`) — all tests pass
- [ ] 7.3 Manual verification: test all acceptance scenarios from the spec with different user roles (admin, owner, METADATA_WRITE group member, METADATA_READ group member, no-permission user)
