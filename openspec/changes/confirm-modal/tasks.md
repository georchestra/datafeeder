## 1. Shared Component — ConfirmModalComponent

- [ ] 1.1 Create `apps/frontend/src/app/shared/components/confirm-modal/confirm-modal.component.ts`: standalone Angular component, inject `DIALOG_DATA` and `DialogRef` from `@angular/cdk/dialog`; define `ConfirmModalData` interface (`title`, `message`, `confirmLabel?`, `cancelLabel?`, `variant?: 'danger' | 'warning'`); implement `confirm()` calling `dialogRef.close(true)` and `cancel()` calling `dialogRef.close(undefined)`
- [ ] 1.2 Create `apps/frontend/src/app/shared/components/confirm-modal/confirm-modal.component.html`: Tailwind-styled modal layout — overlay backdrop, dialog panel with title, message, cancel button and confirm button; apply red destructive styling on confirm button when `variant === 'danger'`
- [ ] 1.3 Export `ConfirmModalComponent` and `ConfirmModalData` from `apps/frontend/src/app/shared/components/confirm-modal/index.ts`
- [ ] 1.4 Run `npm run format` in `apps/frontend/` and verify no ESLint/TypeScript errors on new files

## 2. Feature Integration — integrity-link-list

- [ ] 2.1 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.ts`: inject `Dialog` from `@angular/cdk/dialog`; replace `window.confirm()` in `deleteIntegrityLink()` with `dialog.open(ConfirmModalComponent, { data: { title, message, confirmLabel, variant: 'danger' } })`; await `dialogRef.closed` as a Promise; proceed only when result is `true`
- [ ] 2.2 Remove the `TranslateService` injection if it is no longer used after the migration (was used only for `translate.instant()` in the confirm call); keep it if still needed elsewhere in the component

## 3. Tests

- [ ] 3.1 Create `apps/frontend/src/app/shared/components/confirm-modal/confirm-modal.component.spec.ts`: vitest tests covering — modal renders title and message from `DIALOG_DATA`; confirm button calls `dialogRef.close(true)`; cancel button calls `dialogRef.close(undefined)`; Escape key closes via CDK (verify `dialogRef.close` is called)
- [ ] 3.2 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.spec.ts`: replace `vi.spyOn(window, 'confirm')` mock with a mock for `Dialog.open()` returning an observable; update scenarios — "calls delete API when modal confirmed", "does not call delete API when modal cancelled"

## 4. Validation

- [ ] 4.1 Manual smoke test: delete a dataset — verify the in-app modal appears (not the browser native dialog), confirm deletes and removes the row, cancel leaves the row intact
- [ ] 4.2 Manual test: press Escape while modal is open — verify modal closes without deleting
- [ ] 4.3 Manual test: click the backdrop — verify modal closes without deleting
