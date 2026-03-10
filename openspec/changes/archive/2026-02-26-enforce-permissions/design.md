## Context

Permission rules (`IntegrityLinkRule`) already exist in the database and can be edited/saved through the UI. However, they are not enforced: any authenticated user can access any dataset endpoint, and the frontend shows all navigation links regardless of permissions. Only two partial checks exist: the dataset list filters to owner-only for non-admins, and `process.py` checks ownership before triggering processing.

The `GeorchestraContext` extracts user identity from gateway headers (`sec-username`, `sec-roles`, `sec-email`) but does **not** currently include the user's organization (`sec-org` header), which is needed to match against `IntegrityLinkRule.group_or_role`.

## Goals / Non-Goals

**Goals:**
- Enforce all permission rules via HTTP 403 on every protected backend endpoint
- Filter dataset list visibility based on group permissions
- Conditionally render frontend navigation based on effective permissions
- Reusable, centralized permission-checking logic

**Non-Goals:**
- Changing the permission data model (IntegrityLinkRule schema stays as-is)
- Adding new API endpoints (existing endpoints gain authorization checks)
- Frontend route guards or custom 403 pages (backend 403 is displayed as-is)
- DATA-dimension permission enforcement (DATA READ/WRITE controls external systems, not DataFeeder navigation)

## Decisions

### Decision 1: Add `organization` to `GeorchestraContext`

Extract the `sec-org` header alongside existing headers. This gives all routes access to the user's group for permission matching.

**Alternative considered**: Read `sec-org` directly in each route via `Header(...)`. Rejected because it scatters the same logic across many route files and breaks the established pattern of using `GeorchestraContextDep`.

**File**: `apps/backend/src/services/georchestra.py`

### Decision 2: Create a reusable permission-checking dependency

Implement a `PermissionChecker` class or function in `apps/backend/src/core/security.py` that:
1. Loads the `IntegrityLink` by ID (404 if not found)
2. Checks admin → allow immediately
3. Checks owner → allow immediately
4. Queries `IntegrityLinkRule` for the user's organization + required level
5. Raises 403 if no match

This will be a FastAPI dependency that can be parameterized by required access level:
- `METADATA_READ` — list visibility
- `METADATA_WRITE` — detail access, metadata proxy
- `OWNER_ONLY` — rights editing, events, recurrence, reconfigure, delete

**Alternative considered**: Middleware-based approach. Rejected because permission checks need the dataset ID from the path, which varies by route pattern.

**File**: `apps/backend/src/core/security.py`

### Decision 3: Extend list API response with per-item access level

Add an `access_level` field to the `IntegrityLinkListItem` response model. Computed per-row based on user context:
- `"OWNER"` — user is the dataset owner
- `"ADMIN"` — user is an administrator
- `"WRITE"` — user's group has METADATA WRITE
- `"READ"` — user's group has METADATA READ

This avoids a second API call from the frontend to determine per-dataset permissions.

**File**: `apps/backend/src/models/integrity_link.py` (response model), `apps/backend/src/api/routes/ingestion/integrity_links.py` (query)

### Decision 4: Update dataset list query with permission join

Modify the `list_integrity_links` query to LEFT JOIN with `IntegrityLinkRule` and filter:
```sql
WHERE integrity_owner = :username
   OR EXISTS (SELECT 1 FROM integrity_link_rule
              WHERE integrity_link_id = integrity_link.id
              AND rule_type = 'METADATA'
              AND group_or_role = :user_org)
```
For admins, no filter is applied.

**File**: `apps/backend/src/api/routes/ingestion/integrity_links.py`

### Decision 5: Frontend uses `access_level` from list response

The list component uses the `access_level` field to:
- Disable row click for `READ` level (dataset visible but not navigable)
- Enable row click for `WRITE`, `OWNER`, `ADMIN`

The layout sidebar uses the loaded `IntegrityLink` data (augmented with permission info) to conditionally show/hide links.

**Files**: 
- `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.ts`
- `apps/frontend/src/app/layout/intlink-layout.component.ts`
- `apps/frontend/src/app/layout/intlink-layout.component.html`

### Decision 6: No frontend route guards

Per spec FR-013, manual URL navigation to unauthorized pages relies on the backend's 403 response. The frontend displays the error as-is. No Angular guards or custom redirect logic needed.

## Risks / Trade-offs

- **Performance of list query with permission join**: The LEFT JOIN + EXISTS subquery adds complexity. → Mitigation: Index on `integrity_link_rule(integrity_link_id, rule_type, group_or_role)`. Dataset counts are expected to be manageable (hundreds, not millions).
- **Race condition on group changes**: If a user's group changes mid-session, the frontend may show stale access levels until next list refresh. → Accepted per spec (backend rejects the next action; frontend reflects on next page load).
- **`sec-org` header reliability**: The gateway must always inject this header. → Mitigation: Validate presence in `GeorchestraContext`; return 401 if missing.
