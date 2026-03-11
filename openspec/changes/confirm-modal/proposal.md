## Why

The dataset delete action uses `window.confirm()` for user confirmation — a native browser dialog that doesn't match the application design system, cannot be styled or translated consistently, and blocks the main thread. A reusable, in-app modal confirmation component is needed to complete the delete-dataset feature with proper UX.

## What Changes

- **New shared `ConfirmModalComponent`** — a reusable Angular standalone component for destructive-action confirmation dialogs, built on Angular CDK Dialog (already a dependency) with Tailwind CSS styling
- **Replace `window.confirm()`** in `integrity-link-list` — the delete flow uses the new modal instead of the native dialog
- **i18n integration** — title, message, and button labels are passed as translation keys or resolved strings; no hardcoded text
- **Accessible by default** — focus trap, keyboard (Escape to cancel), ARIA roles via CDK Dialog

## Capabilities

### New Capabilities

- `confirm-modal`: Reusable confirmation modal dialog for destructive actions — built on Angular CDK Dialog, Tailwind-styled, signal-compatible, i18n-friendly. Configurable title, message, confirm/cancel labels and variants (danger, warning).

### Modified Capabilities

<!-- No existing spec-level behavior changes required -->

## Impact

- **Frontend only** — no backend, ELT, or database changes
- `apps/frontend/src/app/shared/components/confirm-modal/` — new shared component
- `apps/frontend/src/app/features/integrity-link-list/` — updated to use modal instead of `window.confirm()`
- `apps/frontend/translations/` — new i18n keys for modal content
- `@angular/cdk/dialog` is already a transitive dep via `@angular/cdk: 20.2.14` — no new packages needed
