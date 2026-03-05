## Context

Every call to `compute_effective_access` in `core/security.py` invokes `resolve_org_id`, which performs a synchronous HTTP `GET` against the geOrchestra Console to fetch the full organisation list and searches for a matching `shortName`. This happens:

- Once per single-resource endpoint (acceptable but still wasteful).
- **Once per dataset row** on list endpoints (e.g., `GET /ingestion/integrity_links`) — N requests per HTTP request, where N is the size of the result set.

Additionally, `integrity_links.py` calls `resolve_org_id` *twice*: once explicitly before the loop (line 57) and once implicitly per iteration via `compute_effective_access` (line 95).

The geOrchestra Console exposes a direct lookup endpoint:
`GET /internal/organizations/shortname/{name}` (already used by `ConsoleService.get_organization`).

## Goals / Non-Goals

**Goals:**
- Resolve the current user's org UUID **exactly once per HTTP request** using a FastAPI `Depends` dependency.
- Remove all internal `resolve_org_id` calls from `compute_effective_access`.
- Eliminate the duplicate call in `integrity_links.py`.
- No change in observable security behaviour — access semantics stay identical.

**Non-Goals:**
- Caching org UUIDs across requests (TTL/in-memory cache) — out of scope.
- Making `ConsoleService` async — out of scope; sync `httpx` in a threadpool is acceptable for now.
- Changing the `IntegrityLinkRule` storage format or permission model.

## Decisions

### D1 — New `get_org_id` FastAPI dependency in `core/security.py`

The dependency reads `geo_ctx.organization` (already available via `GeorchestraContext`) and calls `ConsoleService.get_organization(short_name)` which hits `GET /internal/organizations/shortname/{name}`. Returns `str | None` (UUID or `None` if org not found / console unreachable).

**Why here, not in `services/`?**  
`core/security.py` already owns all permission-related helpers. Keeping `get_org_id` co-located avoids a new file and ensures the dependency graph stays within core.

**Why not in `api/routes/groups_common.py`?**  
`groups_common.py` implements group-list fetching for the groups management UI. Mixing per-request org resolution into that module would blur its single responsibility.

**Alternatives considered:**
- Middleware that resolves and attaches org UUID to request state — more complex, no benefit over a dependency.
- LRU cache on `resolve_org_id` — avoids the repeated call but complicates testability and introduces stale-data risk; dependency pattern is cleaner.

### D2 — `compute_effective_access` receives `org_id: str | None`

Signature changes from:
```python
def compute_effective_access(integrity_link, geo_ctx, session) -> EffectiveAccess | None
```
to:
```python
def compute_effective_access(integrity_link, geo_ctx, session, org_id: str | None) -> EffectiveAccess | None
```
The internal `resolve_org_id` call is removed. If `org_id is None`, the function returns `None` (no org-based access), preserving current semantics.

### D3 — `load_authorized_integrity_link` receives `org_id: str | None`

Passes `org_id` through to `compute_effective_access`. Routes that already call `load_authorized_integrity_link` add one extra argument sourced from `Depends(get_org_id)`.

### D4 — `integrity_links.py` list endpoint uses injected `org_id`

The explicit `resolve_org_id` call at line 57 is replaced by the injected `org_id`. The per-row `compute_effective_access` call (line 95) uses the same injected value.

### D5 — `resolve_org_id` in `groups_common.py` is removed

Once no callers remain, the function is deleted. This removes the full-list fetch entirely from permission hot paths.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Console unreachable at request time | `get_org_id` returns `None` on any exception (same as current `resolve_org_id` behaviour); user gets 403 rather than 500. |
| Route handlers forget to declare `get_org_id` dependency | Type annotations and Pyright will flag missing `org_id` argument to `compute_effective_access`/`load_authorized_integrity_link`. |
| Test suites mock `resolve_org_id` and break | Update mocks to target `get_org_id` dependency or `ConsoleService.get_organization`. |

## Migration Plan

1. Add `get_org_id` dependency to `core/security.py`.
2. Update signatures of `compute_effective_access` and `load_authorized_integrity_link`.
3. Update all call sites in `integrity_link.py`, `integrity_links.py`, `geonetwork.py`, `staging.py`, `process.py`.
4. Delete `resolve_org_id` from `groups_common.py`.
5. Update / add tests.
6. Run `make fix-all-python` and confirm no Pyright errors.

Rollback: all changes are in the backend Python layer; reverting the PR restores the previous behaviour completely.

## Open Questions

_(none)_
