# Endpoint Permission Matrix

> Backend endpoint behavior depending on the current user's effective access level.

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ 200 | Success |
| ❌ 403 | Forbidden |
| 🔍 filtered | Row-level visibility filter (no 403, just fewer/no results) |
| 🔓 open | No permission check — any authenticated user passes |

## Permission Resolution

```
                  ┌─────────────────────────┐
                  │  load_authorized_        │
                  │  integrity_link(id,      │
                  │    required_level)       │
                  └──────────┬──────────────┘
                             │
                  ┌──────────▼──────────────┐
                  │ compute_effective_access │
                  │  → ADMIN|OWNER|WRITE|   │
                  │    READ|None            │
                  └──────────┬──────────────┘
                             │
               ┌─────────────┼─────────────┐
               │             │             │
          None ▼        ADMIN/OWNER ▼    WRITE/READ ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────────┐
        │ 403      │  │ PASS     │  │ required_level?  │
        │ always   │  │ always   │  ├──────────────────┤
        └──────────┘  └──────────┘  │ OWNER_ONLY → 403 │
                                    │ META_WRITE:      │
                                    │   WRITE → pass   │
                                    │   READ  → 403    │
                                    │ META_READ → pass  │
                                    └──────────────────┘
```

## Dataset-Scoped Endpoints

| # | Endpoint | Check | ADMIN | OWNER | WRITE | READ | NO_PERM |
|---|----------|-------|-------|-------|-------|------|---------|
| 1 | `GET /ingestion/integrity-links/` | Row filter | 🔍 all rows | 🔍 own rows | 🔍 own + org-rule rows | 🔍 own + org-rule rows | 🔍 empty list |
| 2 | `GET /ingestion/integrity-link/{id}` | `METADATA_WRITE` | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 |
| 3 | `GET /integrity-link/{id}/rules` | `OWNER_ONLY` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 |
| 4 | `PUT /integrity-link/{id}/rules` | `OWNER_ONLY` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 |
| 5 | `DELETE /integrity-link/{id}/rules/{rid}` | `OWNER_ONLY` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 |
| 6 | `GET /staging/{id}/metadata` | `METADATA_WRITE` | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 |
| 7 | `PUT /staging/{id}/metadata` | `METADATA_WRITE` | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 |
| 8 | `GET /staging/{id}/preview` | `METADATA_WRITE` | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 |
| 9 | `POST /ingestion/process/` | `OWNER_ONLY` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 |
| 10 | `* /geonetwork/{path}` (with UUID) | `METADATA_WRITE` | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 |
| 11 | `* /geonetwork/{path}` (no UUID) | None | 🔓 open | 🔓 open | 🔓 open | 🔓 open | 🔓 open |
| 12 | `GET /airflow/dags/{dag}/runs/{intlink_id}` | `OWNER_ONLY` | ✅ 200 | ✅ 200 | ❌ 403 | ❌ 403 | ❌ 403 |

## Non-Scoped Endpoints (no dataset context)

| # | Endpoint | Any Authenticated User |
|---|----------|------------------------|
| 13 | `POST /ingestion/staging/` (create new dataset) | 🔓 open |
| 14 | `POST /staging/dag_success` (Airflow callback) | 🔓 open |
| 15 | `POST /staging/dag_failure` (Airflow callback) | 🔓 open |
| 16 | `POST /process/dag_success` (Airflow callback) | 🔓 open |
| 17 | `POST /process/dag_failure` (Airflow callback) | 🔓 open |
| 18 | `GET /airflow/dags/{dag}/runs` | 🔓 open |
| 19 | `GET /airflow/dags/{dag}/runs/{run_id}/status` | 🔓 open |
| 20 | `GET /airflow/dags/{dag}/runs/{run_id}/logs` | 🔓 open |
| 21 | `GET /settings/` | 🔓 open |
| 22 | `GET /metadata/groups/` | 🔓 open |
| 23 | `GET /data/groups/` | 🔓 open |
| 24 | `GET /utils/health-check/` | 🔓 open |

## List Endpoint Detail (Row-Level `access_level` Field)

The `GET /ingestion/integrity-links/` response includes a computed `access_level` per row:

| User Type | Row Visibility | `access_level` Value |
|-----------|---------------|---------------------|
| ADMIN | All datasets in the system | `"ADMIN"` on every row |
| OWNER | Own datasets + datasets with org METADATA rule | `"OWNER"` on own, `"WRITE"`/`"READ"` on shared |
| WRITE (org rule) | Own datasets + datasets where org has METADATA rule | `"OWNER"` on own, `"WRITE"` on matching |
| READ (org rule) | Own datasets + datasets where org has METADATA rule | `"OWNER"` on own, `"READ"` on matching |
| NO_PERM | Own datasets only (if any) | `"OWNER"` on own, nothing else |

## Notes

- **Authentication** is handled by the geOrchestra gateway which injects `sec-username`, `sec-roles`, `sec-org` headers. The backend has no JWT validation on these routes.
- **`GET /airflow/dags/{dag}/runs`** (endpoint #18) has no permission check — any authenticated user can list all DAG runs. This may be intentional but is worth noting.
- **Airflow callbacks** (#14-17) have no permission check by design — they are called by Airflow, not by users.
