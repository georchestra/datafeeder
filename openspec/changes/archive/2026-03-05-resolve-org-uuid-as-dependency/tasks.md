## 1. Core dependency and updated security helpers

- [x] 1.1 Add `get_org_id(geo_ctx, settings)` FastAPI dependency to `apps/backend/src/core/security.py` — instantiates `ConsoleService` from settings, calls `get_organization(geo_ctx.organization)`, returns the org UUID string or `None`
- [x] 1.2 Update signature of `compute_effective_access` in `apps/backend/src/core/security.py` to accept `org_id: str | None` and remove the internal `resolve_org_id` call
- [x] 1.3 Update signature of `load_authorized_integrity_link` in `apps/backend/src/core/security.py` to accept and forward `org_id: str | None` to `compute_effective_access`
- [x] 1.4 Remove the `from src.api.routes.groups_common import resolve_org_id` import from `apps/backend/src/core/security.py`

## 2. Route handler migrations

- [x] 2.1 Update `apps/backend/src/api/routes/ingestion/integrity_link.py` — inject `org_id: Annotated[str | None, Depends(get_org_id)]` and pass it to every call of `load_authorized_integrity_link` and `compute_effective_access`
- [x] 2.2 Update `apps/backend/src/api/routes/ingestion/integrity_links.py` — inject `org_id: Annotated[str | None, Depends(get_org_id)]`, replace the explicit `resolve_org_id` call (line 57) with the injected value, and pass `org_id` to the per-row `compute_effective_access` call
- [x] 2.3 Update `apps/backend/src/api/routes/ingestion/staging.py` — inject `org_id` and pass it to all `load_authorized_integrity_link` calls
- [x] 2.4 Update `apps/backend/src/api/routes/ingestion/process.py` — inject `org_id` and pass it to the `load_authorized_integrity_link` call
- [x] 2.5 Update `apps/backend/src/api/routes/geonetwork.py` — inject `org_id` and pass it to the `load_authorized_integrity_link` call

## 3. Cleanup

- [x] 3.1 Delete `resolve_org_id` function from `apps/backend/src/api/routes/groups_common.py` (verify no remaining callers via grep)

---
**Checkpoint — Phase 1–3 complete**: `make fix-all-python` passes, Pyright reports zero new errors.

## 4. Tests

- [x] 4.1 [P] Add unit tests for `get_org_id` dependency in `apps/backend/tests/core/test_security.py` — scenarios: org found, org not found, console unreachable, no org header
- [x] 4.2 [P] Update existing tests for `compute_effective_access` in `apps/backend/tests/core/test_security.py` — pass `org_id` explicitly instead of relying on `resolve_org_id` mock
- [x] 4.3 [P] Update existing tests for `load_authorized_integrity_link` — same as above
- [x] 4.4 [P] Update route-level tests in `apps/backend/tests/api/` that mock `resolve_org_id` to mock `get_org_id` or `ConsoleService.get_organization` instead
- [x] 4.5 Confirm test coverage ≥ 80 % on `core/security.py` (`make test-backend` or equivalent)
