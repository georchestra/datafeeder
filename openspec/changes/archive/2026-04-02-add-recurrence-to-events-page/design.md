## Context

The events page (`/:intlink_id/events`) shows the DAG run history for a dataset. Users arrive here to inspect past ingestion events. Currently, the page header shows the dataset title but provides no visibility into the current recurrence schedule — a key piece of context when reviewing event history (e.g., "was this run expected at this time?").

The `RecurrenceSelectorComponent` (at `apps/frontend/src/app/shared/components/recurrence-selector/`) is a presentational component that already supports a `[disabled]="true"` read-only mode. The metadata page (`features/metadata/`) already uses it in this mode. The backend endpoint `GET /ingestion/integrity-link/{id}/recurrence` is already available. This change is a pure frontend integration.

## Goals / Non-Goals

**Goals:**
- Display the active recurrence schedule on the events page using `RecurrenceSelectorComponent` in disabled mode
- Fetch recurrence from `GET /ingestion/integrity-link/{id}/recurrence` via `EventsComponent`
- Use cronstrue (via existing component logic) for custom cron descriptions
- Match the read-only display pattern established by the metadata page

**Non-Goals:**
- Editing recurrence from the events page (deferred — belongs in a future "Recurrence Planning" page)
- Backend changes (endpoint already exists)
- Changes to `RecurrenceSelectorComponent` itself

## Decisions

### Decision 1: Fetch recurrence directly in EventsComponent

`EventsComponent` is the smart component for the events page. It already fetches DAG runs in `ngOnInit`. Recurrence data should be fetched in the same component using a `recurrence` signal, consistent with how `MetadataComponent` handles it.

**Why not in a store:** The recurrence is page-scoped context, not application-wide state. Adding it to `IntegrityLinkStore` would expand the store's scope beyond structural metadata. The metadata page fetches it locally — events should follow the same pattern.

**Why not reuse metadata's recurrence:** `EventsComponent` and `MetadataComponent` are independent feature components. Sharing state between sibling features would couple them unnecessarily.

### Decision 2: Placement below the page header

The recurrence combobox is placed below the page title (`{{ 'events.title' | translate }} {{ store.integrityLink()?.integrity_title }}`), before the events list. This mirrors the Figma layout (node `1119-21266`) showing dataset scheduling context at the top of the intlink pages.

**Why not in the sidebar or header:** The combobox is content, not navigation. Placing it inline with the page content makes it contextually obvious.

### Decision 3: Reuse existing `RecurrencePresetItem[]` pattern

`RecurrenceSelectorComponent` requires both `[recurrence]` and optionally `[presets]` inputs. In disabled mode, the presets are used to resolve the label for a known preset ID. Fetch presets from `GET /ingestion/recurrence-presets` (same as the wizard), or pass an empty array — the component falls back to cronstrue for custom crons regardless.

Fetching presets allows the component to display the correct i18n label for known presets (e.g., "Chaque jour"). This is the correct behavior and worth the extra API call.

## Risks / Trade-offs

- **[Risk] Extra API call on page load** → Mitigation: Both `recurrence` and `presets` requests are lightweight and parallel. No waterfall dependency.
- **[Trade-off] Duplicate fetch pattern vs metadata page** → Acceptable: The events and metadata pages are independent by design. DRY at the component level is satisfied by reusing `RecurrenceSelectorComponent`; data fetching is intentionally local.
