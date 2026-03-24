## Why

Operations in the datafeeder module (metadata save, publish/unpublish, rights editing, deletion) are fire-and-forget with no guaranteed success — when they fail, the user currently receives no feedback. This leaves the interface in an inconsistent state and the user unaware that their action had no effect.

## What Changes

- Introduce a persistent error toast system in the frontend: toasts stay visible until explicitly dismissed by the user, survive navigation, and stack (most recent at the bottom) when multiple errors accumulate.
- Each error toast displays the name of the failed operation (e.g. "La sauvegarde des métadonnées a rencontré une erreur") and a close button.
- When an operation triggered by a button click fails, the triggering button is re-enabled so the user can retry.
- The following operations must show an error toast on failure:
  - Metadata save
  - GeoNetwork publish and unpublish
  - GeoServer publish and unpublish
  - GeoNetwork / GeoServer rights editing
  - Dataset deletion
- The following operations are not yet implemented and will be wired when built:
  - Recurrence editing

## Capabilities

### New Capabilities
- `error-toast`: Global, persistent, stackable error toast system for the frontend. Toasts survive navigation, are dismissed manually, and include the failed operation name.

### Modified Capabilities
- `delete-dataset`: On deletion failure, re-enable the delete button and surface the error via the toast system.

## Impact

- **Frontend-only change** (apps/frontend/).
- New `ErrorToastStore` in `core/stores/` and `ErrorToastComponent` in `shared/components/` (overlay-based).
- Feature components for metadata save, GeoNetwork publish/unpublish, GeoNetwork/GeoServer rights editing, and deletion will emit errors via the new store instead of silently failing.
- GeoServer publish/unpublish and recurrence editing are not yet implemented; toast wiring will be added when those features are built.
- No backend or API changes required.
- Aligned with Angular Architecture principle: smart/presentational separation — the toast component is purely presentational; the store manages state via Angular signals.
