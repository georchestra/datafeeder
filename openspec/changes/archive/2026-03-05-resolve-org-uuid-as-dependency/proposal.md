## Why

`compute_effective_access` calls `resolve_org_id`, which performs a synchronous HTTP fetch of the full organization list on every permission check. Endpoints that iterate over datasets (e.g., list views) will trigger this network call once per row, adding cumulative latency proportional to the number of rows and making every permission gate dependent on console availability.

## What Changes

- Introduce a FastAPI `Depends`-based `OrgContext` that resolves the current user's org shortName (from `sec-org` header) to its console UUID **once per request** using the existing geOrchestra Console `GET /internal/organizations/shortname/{name}` endpoint.
- Remove the call to `resolve_org_id` (and thus the full organizations-list fetch) from `compute_effective_access` in `core/security.py`.
- Update `compute_effective_access` and `load_authorized_integrity_link` to accept the pre-resolved `org_id: str | None` argument instead of computing it internally.
- Remove `resolve_org_id` from `api/routes/groups_common.py` (dead code once replaced).
- Add `get_org_id` dependency function in `core/security.py` (or a new `core/acl.py`) using `ConsoleService` injected via `Depends`.

## Capabilities

### New Capabilities

- `resolve-org-uuid-as-dependency`: FastAPI dependency that resolves the authenticated user's organisation shortName to its console UUID once per request and injects it into route handlers.

### Modified Capabilities

_(none — no spec-level user-facing behaviour changes; this is a backend performance and reliability improvement)_

## Impact

- **Backend only** — no API contract changes, no frontend impact.
- Files affected:
  - `apps/backend/src/core/security.py` — signature changes to `compute_effective_access` / `load_authorized_integrity_link`.
  - `apps/backend/src/api/routes/groups_common.py` — `resolve_org_id` removed.
  - All route handlers that call `load_authorized_integrity_link` gain one extra `Depends` parameter.
  - `apps/backend/src/services/console_service.py` — potentially extended with a `get_organization_by_shortname` method (already present).
  - `apps/backend/tests/` — unit tests for the new dependency and updated security helpers.
- Principle 8 (Security) and Principle 4 (Testing) apply.
- No database migrations required.
