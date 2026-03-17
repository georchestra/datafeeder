## Context

`IntegrityLink` already stores the cron expression in `schedule`. A dedicated `GET /ingestion/integrity-link/{id}/recurrence` endpoint was introduced to expose `cron + preset_id` to the frontend, but this creates an unnecessary second round-trip: the frontend already loads the full `IntegrityLinkResponse` via the store before rendering the events page.

`IntegrityLinkResponse` currently exposes `schedule` (the raw cron string) but not `preset_id`. The frontend `EventsComponent` therefore calls the recurrence endpoint to resolve the preset from the cron.

## Goals / Non-Goals

**Goals:**
- Expose `preset_id` directly on `IntegrityLinkResponse` so consumers have cron + preset in one call.
- Remove the redundant `/recurrence` endpoint.
- Update `EventsComponent` to derive recurrence from the already-loaded store value.

**Non-Goals:**
- Changing how recurrence is written/updated (process endpoint is untouched).
- Modifying `RecurrenceSelectorComponent` behaviour.
- Altering the `schedule_enabled` field or Airflow scheduling logic.

## Decisions

### 1. Add `preset_id` to `IntegrityLinkResponse`, not a new response model

**Decision**: Add `preset_id: str | None` directly to `IntegrityLinkResponse` in `data_import.py`.

**Rationale**: `IntegrityLinkResponse` already holds `schedule`. Keeping cron and preset together on the same model avoids a shape mismatch. A separate `RecurrenceResponse` wrapper is unnecessary when only one extra nullable field is needed.

**Alternative considered**: Return a nested `recurrence: RecurrenceResponse | None` object. Rejected — over-engineered for two scalar fields, and would require frontend model changes beyond what's needed.

### 2. Compute `preset_id` at serialisation time in `get_integrity_link`

**Decision**: Populate `preset_id` in the route handler by calling `RecurrencePreset.from_cron(integrity_link.schedule)` after `model_validate`, rather than adding a `@computed_field` to the Pydantic model.

**Rationale**: `IntegrityLinkResponse` uses `model_validate(integrity_link)` from ORM attributes. `RecurrencePreset.from_cron` is pure business logic that belongs in the route (or a service helper) rather than leaking domain logic into the response model. The route already performs similar post-validation mutation (`response.access_level = effective.value`).

**Alternative considered**: `@computed_field` on `IntegrityLinkResponse`. Rejected — the model would need to import `RecurrencePreset`, coupling the response model to domain logic and making it harder to test in isolation.

### 3. Frontend reads recurrence from `IntegrityLinkStore`, not a dedicated call

**Decision**: `EventsComponent` reads `cron` (`integrityLink().schedule`) and `preset_id` (`integrityLink().preset_id`) directly from the store signal instead of invoking `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet`.

**Rationale**: The store is already loaded before the events page renders. Removing the extra API call reduces latency and simplifies the component. The `RecurrenceSelectorComponent.recurrence` input can be constructed inline from the store value.

### 4. Delete the generated API client file

**Decision**: Delete `apps/frontend/src/app/core/api/fn/ingestion/get-integrity-link-recurrence-*.ts` and remove its re-export from `functions.ts`.

**Rationale**: The file is generated from the OpenAPI spec. Once the endpoint is removed from the backend spec, the file becomes dead code and will be regenerated without it on the next `make generate-api`. Deleting it now keeps the client in sync and prevents stale imports.

## Risks / Trade-offs

- **External consumers of `/recurrence`**: Any third-party client calling this endpoint will receive 404 after deployment. → Mitigation: the endpoint is internal-only (same frontend); no public API contract exists.
- **`preset_id` derivation cost**: `RecurrencePreset.from_cron` iterates over a small enum on every `get_integrity_link` call. → Negligible; the enum has ≤10 entries.

## Migration Plan

1. Backend: add `preset_id` field + populate in handler → deploy.
2. Backend: remove `/recurrence` endpoint in the same deploy (atomic with step 1).
3. Frontend: update `EventsComponent` to read from store; delete dead API client file → deploy after backend.

No database migration required.
