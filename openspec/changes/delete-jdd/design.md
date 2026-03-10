## Context

The JDD dashboard currently allows users to view and search their datasets (IntegrityLinks). Users cannot yet delete datasets — once ingested, a JDD persists indefinitely. This change adds deletion as a lifecycle operation, removing all associated resources: the Airflow recurrent DAG (if applicable), the GeoServer layer, the data table, the GeoNetwork metadata record, and the IntegrityLink row itself.

The backend already provides:

- `load_authorized_integrity_link()` with `AccessLevel.OWNER_ONLY` for ownership-based permission
- `GeoServerService` for layer management
- `AirflowApiClient` (via `airflow_client` library's `DAGApi`) for DAG operations
- `MetadataService` wrapping GeoNetwork

The frontend dashboard (`integrity-link-list` feature) already lists JDDs via the `listIntegrityLinks` API call, using Angular signals without NgRx.

## Goals / Non-Goals

**Goals:**

- `DELETE /api/ingestion/integrity-link/{id}` endpoint enforcing ownership (owner or admin)
- Sequential resource cleanup: DAG (blocking) → GeoServer layer → data table → GeoNetwork record → IntegrityLink (via cascade)
- Hover-triggered trash icon in the JDD list row; row removed from list on success
- Error is surfaced to caller if DAG deletion fails; subsequent steps are skipped in that case

**Non-Goals:**

- Soft delete / recycle bin
- Bulk deletion
- Cascading error recovery or rollback of partial cleanup
- Error display UI in frontend (deferred to GSMEL-904)
- Migration of existing data

## Decisions

### 1. Endpoint path: `DELETE /ingestion/integrity-link/{id}`

**Decision**: Add the DELETE method to the existing `integrity_link.py` router, keeping the path consistent with the existing GET on the same resource.

**Alternative considered**: A separate `/ingestion/jdd/{id}` path. Rejected — the resource is already named `integrity-link` throughout the API; a new alias would add confusion.

### 2. Permission model: `AccessLevel.OWNER_ONLY`

**Decision**: Reuse the existing `load_authorized_integrity_link(id, AccessLevel.OWNER_ONLY, ...)` helper, which raises HTTP 403 for non-owners/non-admins and HTTP 404 if the record doesn't exist.

**Alternative**: Manual check. Rejected — the helper already implements the correct semantics and is tested.

### 3. Cleanup sequence and failure semantics

**Decision**: Execute cleanup steps in this order:

1. Delete Airflow DAG (only if `schedule` is set) — **blocking**: if this fails → return HTTP 500, stop
2. Delete GeoServer layer — best-effort, log on failure
3. Drop final table (`{org_schema}.{final_table_name}`) — best-effort, log on failure
4. Drop staging table (`staging.{staging_table_name}`) with `IF EXISTS` — best-effort, log on failure (usually already cleaned post-ingestion)
5. Delete GeoNetwork record — best-effort, log on failure
6. Delete IntegrityLink row (DB) — cascade removes `IntegrityLinkRule` rows automatically

**Rationale**: DAG deletion is the only step where a lingering process could corrupt system state (scheduled runs on a deleted dataset). All other steps are idempotent resources that can be cleaned up manually if needed. Staging table drop captures orphaned tables from failed ingestions (successful ingestions already drop staging in the transformation task group). `ON DELETE CASCADE` on `integrity_link_rule.integrity_link_id` ensures no orphan rules remain.

**Alternative**: Transactional rollback across all external systems. Rejected — distributed rollback across Airflow/GeoServer/GeoNetwork/PostgreSQL is impractical and over-engineered for this use case.

### 4. Frontend: component-level signal state, no NgRx action

**Decision**: Add deletion directly to `IntegrityLinkListComponent` using a local signal for the pending-delete ID and the existing `api.invoke()` pattern. On success, filter the deleted item from the `integrityLinks` signal.

**Rationale**: The list already manages its own state via signals without NgRx. Introducing an NgRx action for a single delete operation would significantly over-engineer the interaction with no observable benefit.

**Alternative**: NgRx `deleteJdd` action + effect. Rejected — the feature doesn't use NgRx; introducing it here would be inconsistent.

### 4b. UI Design: Figma mockup with hover states

**Design Reference**: [Figma: Hover-triggered delete button](https://www.figma.com/design/IwMxmE9G9D9StF2QLlR1uE/ingestion-donn%C3%A9es?node-id=127-4236&p=f&t=TebrnRWWgdhRvUGf-0)

**Implementation Note**: Use Figma MCP during implementation to extract exact visual specifications (spacing, colors, sizing, hover states, button positioning). The Figma file includes comments describing the hover behavior and interaction states.

### 5. Database: no migration needed

**Decision**: Rely on existing `ON DELETE CASCADE` constraint in database schema (`docker/datadir/database/130-datakern.sql` line 56). Both staging and final tables are dropped via direct SQL `DROP TABLE IF EXISTS` in the service layer (best-effort, with error logging).

**Rationale**: The database initialization script already defines the FK constraint with `ON DELETE CASCADE`, ensuring that deleting an IntegrityLink automatically removes associated IntegrityLinkRule rows. No migration or model changes needed.

**Alternative**: Keep orphan rules and clean on read. Rejected — orphan rules are data integrity violations.

## Risks / Trade-offs

| Risk                                                                             | Mitigation                                                         |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Airflow DAG deletion fails even when no DAG exists (e.g., DAG was never created) | Service catches 404 from Airflow and treats it as success          |
| GeoServer layer deletion fails silently                                          | Log error with integrity_link_id; resource can be cleaned manually |
| Data table already dropped (e.g., prior manual cleanup)                          | `DROP TABLE IF EXISTS` avoids hard failure                         |
| GeoNetwork record missing                                                        | Treat 404 as success in MetadataService                            |
| Race condition: concurrent delete and update                                     | Acceptable — first DELETE wins; second sees 404                    |

## Migration Plan

1. Deploy backend with new DELETE endpoint
2. Deploy frontend with hover-state delete button
3. No rollback complexity — no schema changes needed

## Open Questions

~~Does `integrity_link_rule.integrity_link_id` already have `ON DELETE CASCADE`? → verify in Alembic migrations before implementing~~

**RESOLVED**: ✅ FK constraint HAS `ON DELETE CASCADE` in database initialization script (`docker/datadir/database/130-datakern.sql` line 56). No migration needed. Note: SQLModel definition doesn't specify `ondelete='CASCADE'` but the actual database schema is correct.

~~Should the staging table also be dropped, or only the final table? → per Jira story: "suppression table données" refers to the published final table; staging is separate~~

**RESOLVED**: ✅ New Jira requirement: "suppression table données (staging et finale, selon l'état du JDD)" - Delete BOTH tables according to JDD state. In practice:

- Final table: Always attempt to drop if `final_table_name` is set (published data)
- Staging table: Always attempt to drop with `IF EXISTS` (usually already cleaned post-ingestion, but may linger if ingestion failed)
- Both operations are best-effort with error logging
