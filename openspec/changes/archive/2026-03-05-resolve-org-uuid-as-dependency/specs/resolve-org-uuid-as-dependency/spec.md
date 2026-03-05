## ADDED Requirements

### Requirement: Org UUID resolved once per request
The backend SHALL resolve the authenticated user's organisation shortName to its
geOrchestra Console UUID exactly once per HTTP request, using a FastAPI dependency,
and inject the result into all downstream permission checks.

#### Scenario: User belongs to a known organisation
- **WHEN** a request arrives with a valid `sec-org` header matching an existing geOrchestra organisation
- **THEN** the system fetches the org UUID from `GET /internal/organizations/shortname/{name}` exactly once per request

#### Scenario: User organisation not found in console
- **WHEN** the `sec-org` header value does not match any known organisation in the console
- **THEN** `get_org_id` returns `None` and the user is treated as having no organisation-based access

#### Scenario: Console unreachable
- **WHEN** the geOrchestra Console is unavailable or returns an error
- **THEN** `get_org_id` returns `None`, the request proceeds with no org-based access, and no 500 error is raised

#### Scenario: User has no organisation header
- **WHEN** a request arrives without a `sec-org` header (user has no organisation)
- **THEN** `get_org_id` returns `None` without making any network call

### Requirement: Permission checks use injected org UUID
The `compute_effective_access` function SHALL accept an `org_id: str | None` parameter
instead of resolving the org UUID internally. No network call SHALL be made inside
`compute_effective_access`.

#### Scenario: Org UUID passed to permission check
- **WHEN** `compute_effective_access` is called with a pre-resolved `org_id`
- **THEN** it uses that value directly to query `IntegrityLinkRule` records without calling `resolve_org_id`

#### Scenario: None org UUID short-circuits group check
- **WHEN** `compute_effective_access` is called with `org_id=None`
- **THEN** it returns `None` (no org-based access) without querying the database for rules

### Requirement: List endpoints perform single org resolution
On list endpoints that iterate over multiple datasets, the system SHALL resolve the
org UUID once before the iteration loop, not once per dataset row.

#### Scenario: List with multiple datasets
- **WHEN** a user requests the list of integrity links
- **THEN** the org UUID is resolved once and reused for all per-row permission evaluations

#### Scenario: Admin bypasses org resolution
- **WHEN** the requesting user is an administrator
- **THEN** `compute_effective_access` returns `EffectiveAccess.ADMIN` before any org UUID lookup is needed

### Requirement: resolve_org_id removed from production code
The `resolve_org_id` function in `api/routes/groups_common.py` SHALL be removed
once all callers have been migrated to the new dependency.

#### Scenario: No remaining callers
- **WHEN** all route handlers use `Depends(get_org_id)` for org resolution
- **THEN** `resolve_org_id` is not present in the codebase
