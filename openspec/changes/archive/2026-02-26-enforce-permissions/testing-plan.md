# Task 7.3 — Manual Verification & Integration Tests: enforce-permissions

## Environment

- Frontend URL: http://localhost:8080/datakern/
- Backend via gateway: http://localhost:8080/datakern-backend
- Backend docs: http://localhost:8080/datakern-backend/docs

## LDAP Users & Organizations

Discovered from the geOrchestra LDAP (image: georchestra/ldap:25.0.x):

| Username         | Password             | Org (sec-org) | Key Roles                                     | IMPORT? |
|------------------|----------------------|---------------|-----------------------------------------------|---------|
| testadmin        | testadmin            | PSC           | ROLE_ADMINISTRATOR, ROLE_SUPERUSER, ROLE_IMPORT | Yes   |
| testuser         | testuser             | PSC           | ROLE_USER, ROLE_IMPORT                        | Yes     |
| testeditor       | testeditor           | C2C           | ROLE_USER, ROLE_GN_EDITOR                     | No      |
| idatafeeder      | idatafeeder          | (none)        | ROLE_GN_ADMIN, ROLE_IMPORT                    | Yes     |
| testreviewer     | testreviewer         | (none)        | ROLE_GN_REVIEWER, ROLE_USER                   | No      |
| testdelegatedadmin | testdelegatedadmin | (none)        | ROLE_USER                                     | No      |

**LDAP Orgs:**
- `PSC` (Project Steering Committee): members = testadmin, testuser
- `C2C` (Camptocamp): members = testeditor

**Notes on sec-org format:**
- The gateway sends the LDAP `cn` value as-is: `PSC` and `C2C` (uppercase)
- `IntegrityLinkRule.group_or_role` must match exactly what the gateway sends

**Notes on sec-roles format:**
- The gateway sends roles with `ROLE_` prefix: `ROLE_ADMINISTRATOR`, `ROLE_IMPORT`, etc.
- The backend must strip this prefix for `is_administrator()` to work

## Gateway Access Rules

From `docker/datadir/gateway/gateway.yaml`:
- `/datakern-backend/**` requires `ROLE_IMPORT` role
- Only testadmin, testuser, idatafeeder have IMPORT → the others can't reach the backend via gateway
- For direct backend tests at `:8000`, we bypass the gateway and inject `sec-*` headers manually

## Testing Strategy

All tests go through **http://localhost:8080** (geOrchestra gateway). This tests the full real
auth chain: LDAP → gateway → sec-* headers → backend.

- **Backend API tests**: Use `curl --user <user>:<password> http://localhost:8080/datakern-backend/...`
- **Frontend UI tests**: Use Playwright MCP (browser login at /login → navigate /datakern/)

## Bugs Found During Exploration

### Bug #1: ROLE_ prefix not stripped from sec-roles header

**Description:** The geOrchestra gateway injects roles with `ROLE_` prefix (e.g., `ROLE_ADMINISTRATOR`).
The `get_georchestra_context` function does NOT strip this prefix. So `geo_ctx.roles` contains
`{"ROLE_ADMINISTRATOR", "ROLE_IMPORT"}` instead of `{"ADMINISTRATOR", "IMPORT"}`.

`is_administrator()` calls `has_role("ADMINISTRATOR")` which checks `"ADMINISTRATOR" in roles`.
With the prefix present, this is `"ADMINISTRATOR" in {"ROLE_ADMINISTRATOR"}` → **False**.

**Effect:** Admin bypass is completely broken in production (via gateway). Admins only see their own
datasets instead of all datasets. All OWNER_ONLY operations on non-owned datasets fail for admins.

**Fix:** In `get_georchestra_context`, strip `ROLE_` prefix when parsing roles.

**File:** `apps/backend/src/services/georchestra.py`

## Test Dataset Setup — Created From Scratch

**No pre-existing datasets.** Each test dataset is created during test execution
using the staging URL import API. We use real open-data URLs from Bordeaux Métropole
(ci_vcub_p dataset) in three different formats to exercise diverse file types.

### Test data sources (Bordeaux Métropole — ci_vcub_p)

| Format   | URL |
|----------|-----|
| GeoJSON  | `https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/geojson` |
| CSV      | `https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/csv?use_labels=true` |
| Shapefile| `https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/shp` |

### Step-by-step dataset creation

All requests go through the gateway with Basic Auth.

**1. Create Dataset_A — owned by testadmin (org=PSC) — GeoJSON**

```bash
curl -X POST http://localhost:8080/datakern-backend/ingestion/staging/ \
  --user testadmin:testadmin \
  -F "type=url" \
  -F "url=https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/geojson"
```

→ Response: `{ "integrity_link_id": "<DATASET_A_ID>", ... }`
→ Wait for staging DAG to complete (poll `GET /airflow/dags/staging_dag/runs/<run_id>`)
→ Dataset remains in **staging** state (do NOT process)

**2. Create Dataset_B — owned by testuser (org=PSC) — CSV**

```bash
curl -X POST http://localhost:8080/datakern-backend/ingestion/staging/ \
  --user testuser:testuser \
  -F "type=url" \
  -F "url=https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/csv?use_labels=true"
```

→ Response: `{ "integrity_link_id": "<DATASET_B_ID>", ... }`
→ Wait for staging DAG to complete

**3. Create Dataset_C — owned by idatafeeder (org=none) — Shapefile**

```bash
curl -X POST http://localhost:8080/datakern-backend/ingestion/staging/ \
  --user idatafeeder:idatafeeder \
  -F "type=url" \
  -F "url=https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/ci_vcub_p/exports/shp"
```

→ Response: `{ "integrity_link_id": "<DATASET_C_ID>", ... }`
→ Wait for staging DAG to complete

### Variables to Record After Creation

| Label     | Owner       | Org    | ID (from response)    |
|-----------|-------------|--------|-----------------------|
| Dataset_A | testadmin   | PSC    | `$DATASET_A_ID`       |
| Dataset_B | testuser    | PSC    | `$DATASET_B_ID`       |
| Dataset_C | idatafeeder | (none) | `$DATASET_C_ID`       |

### Permission Rules to Configure (after datasets exist)

Rules are created by the **dataset owner** (or admin) via the rules endpoint.

**On Dataset_B (owned by testuser):**

```bash
# Rule 1: PSC org gets METADATA WRITE (so testadmin can also access via rule — redundant with admin, but validates rule logic)
curl -X PUT "http://localhost:8080/datakern-backend/ingestion/integrity-link/$DATASET_B_ID/rules" \
  --user testuser:testuser \
  -H "Content-Type: application/json" \
  -d '{"group_or_role": "PSC", "rule_type": "METADATA", "rule_value": "WRITE"}'

# Rule 2: C2C org gets METADATA READ (testeditor can see in list but NOT navigate)
curl -X PUT "http://localhost:8080/datakern-backend/ingestion/integrity-link/$DATASET_B_ID/rules" \
  --user testuser:testuser \
  -H "Content-Type: application/json" \
  -d '{"group_or_role": "C2C", "rule_type": "METADATA", "rule_value": "READ"}'
```

**On Dataset_C (owned by idatafeeder):**

```bash
# Rule 3: PSC org gets METADATA WRITE (testuser can access Dataset_C via this rule)
curl -X PUT "http://localhost:8080/datakern-backend/ingestion/integrity-link/$DATASET_C_ID/rules" \
  --user idatafeeder:idatafeeder \
  -H "Content-Type: application/json" \
  -d '{"group_or_role": "PSC", "rule_type": "METADATA", "rule_value": "WRITE"}'
```

### Expected State After Setup

| Dataset   | Owner       | Org    | Status  | Rules                              |
|-----------|-------------|--------|---------|-------------------------------------|
| Dataset_A | testadmin   | PSC    | staging | (none)                              |
| Dataset_B | testuser    | PSC    | staging | PSC→METADATA/WRITE, C2C→METADATA/READ |
| Dataset_C | idatafeeder | (none) | staging | PSC→METADATA/WRITE                  |

## Acceptance Scenarios (from spec)

### 1. Dataset List Visibility (`GET /ingestion/integrity-links/`)

| User        | Login (gateway)              | Expected datasets visible          | Expected access_level per dataset          |
|-------------|------------------------------|------------------------------------|--------------------------------------------|
| testadmin   | `--user testadmin:testadmin` | ALL 3 (admin bypass)               | ADMIN for all                              |
| testuser    | `--user testuser:testuser`   | Dataset_A (org=PSC, owner=testadmin but no rule → hidden?) + Dataset_B (owner) + Dataset_C (WRITE rule) | See note below |
| testeditor  | Cannot reach backend via gateway (no ROLE_IMPORT) | N/A — test via Playwright login only | N/A |
| idatafeeder | `--user idatafeeder:idatafeeder` | Dataset_C (owner only)         | OWNER                                      |

**Note on testuser visibility:**
- Dataset_A: testuser is NOT the owner, but org=PSC. Dataset_A has **no rules** → PSC has no METADATA rule → **not visible** to testuser
- Dataset_B: testuser IS the owner → **visible**, access_level=OWNER
- Dataset_C: testuser is not owner, but PSC→METADATA/WRITE rule exists → **visible**, access_level=WRITE

**Note on testeditor:**
- testeditor has no ROLE_IMPORT → the gateway blocks access to `/datakern-backend/**`
- BUT testeditor CAN log in to the frontend at `/datakern/` (the frontend is not role-gated in the gateway)
- The frontend fetches the API on behalf of the user; if the gateway blocks the XHR, the UI shows "No dataset found" or an error
- To test testeditor's READ-only visibility, we either: (a) test via Playwright browser login, or (b) relax this scenario

### 2. Dataset Detail GET (`GET /ingestion/integrity-link/{id}`, requires METADATA_WRITE)

| User        | Dataset   | Expected |
|-------------|-----------|----------|
| testadmin   | any       | 200 (admin bypass) |
| testuser    | Dataset_B | 200 (owner) |
| testuser    | Dataset_C | 200 (WRITE rule) |
| testuser    | Dataset_A | 403 (no rule for PSC on Dataset_A) |
| idatafeeder | Dataset_B | 403 (no permission) |

### 3. Rules Endpoints (`GET/PUT /integrity-link/{id}/rules`, requires OWNER_ONLY)

| User        | Dataset   | Expected |
|-------------|-----------|----------|
| testadmin   | any       | 200 (admin) |
| testuser    | Dataset_B | 200 (owner) |
| testuser    | Dataset_C | 403 (WRITE rule ≠ owner) |
| idatafeeder | Dataset_C | 200 (owner) |

### 4. Staging Endpoints (`GET .../staging/{id}/metadata`, requires METADATA_WRITE)

| User        | Dataset   | Expected |
|-------------|-----------|----------|
| testuser    | Dataset_B | 200 (owner) |
| testuser    | Dataset_C | 200 (WRITE rule) |
| idatafeeder | Dataset_B | 403 (no permission) |

### 5. Process Endpoint (`POST /ingestion/process/`, requires OWNER_ONLY)

| User        | Dataset   | Expected |
|-------------|-----------|----------|
| testuser    | Dataset_B | 200 (owner) — note: triggers real Airflow DAG |
| testuser    | Dataset_C | 403 (WRITE rule ≠ owner) |

### 6. Airflow Events (`GET /airflow/dags/.../runs`, requires OWNER_ONLY)

| User        | Dataset   | Expected |
|-------------|-----------|----------|
| testuser    | Dataset_C | 403 (WRITE rule ≠ owner) |
| idatafeeder | Dataset_C | 200 (owner) |

### 7. Frontend UI Scenarios (via Playwright)

| User        | Login                        | Expected behavior |
|-------------|------------------------------|-------------------|
| testadmin   | testadmin / testadmin        | Sees all 3 datasets; can click any row; all sidebar links enabled; Authorizations, Events, Reconfigure visible |
| testuser    | testuser / testuser          | Sees Dataset_B (owner) + Dataset_C (WRITE rule); Dataset_C sidebar: only Metadata Sheet clickable; Authorizations/Events/Reconfigure disabled/hidden |
| testeditor  | testeditor / testeditor      | Frontend loads but API calls may fail (no ROLE_IMPORT for gateway). If API returns error, UI shows empty/error state. If frontend can somehow reach API, Dataset_B row should be NOT clickable (READ only) |

## Test Execution Flow

```
Phase 1 — Setup
  1. Create test_data.csv (3-row CSV)
  2. POST staging as testadmin  → Dataset_A (wait for staging DAG)
  3. POST staging as testuser   → Dataset_B (wait for staging DAG)
  4. POST staging as idatafeeder → Dataset_C (wait for staging DAG)
  5. PUT rules on Dataset_B: PSC→METADATA/WRITE, C2C→METADATA/READ
  6. PUT rules on Dataset_C: PSC→METADATA/WRITE

Phase 2 — Backend API Tests (via gateway, curl --user)
  7. Scenario 1: list visibility for each user
  8. Scenario 2: detail GET permissions
  9. Scenario 3: rules endpoint permissions
  10. Scenario 4: staging endpoint permissions
  11. Scenario 5: process endpoint 403 (skip 200 to avoid side effects)
  12. Scenario 6: airflow events permissions

Phase 3 — Frontend UI Tests (via Playwright)
  13. Login as testadmin → verify list + sidebar
  14. Login as testuser → verify list + sidebar on Dataset_C
  15. Login as testeditor → verify behavior (empty or read-only)

Phase 4 — Bug Fixes
  16. For each bug found: fix → git commit → re-run affected scenarios
```

## Test Commands — via gateway (Basic Auth)

```bash
# As testadmin
curl --user testadmin:testadmin http://localhost:8080/datakern-backend/...

# As testuser
curl --user testuser:testuser http://localhost:8080/datakern-backend/...

# As idatafeeder
curl --user idatafeeder:idatafeeder http://localhost:8080/datakern-backend/...
```

## Integration Tests Location

`apps/backend/tests/api/routes/test_enforce_permissions.py`

Tests use `TestClient` with `headers={"sec-username": ..., "sec-org": ..., "sec-roles": ...}`.
Fixtures create IntegrityLink + IntegrityLinkRule directly in test DB (no staging DAG needed).
Roles are set WITHOUT `ROLE_` prefix (since `get_georchestra_context` strips it after the fix).
