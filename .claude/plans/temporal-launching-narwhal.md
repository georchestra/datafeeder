# Fix: preserve `layerTitle` in `DataSourceApiComponent` after store reload

## Context

After the user submits the staging form, `DataImportWizardComponent.onConfigureDataset()` calls
`setAndLoadIntegrityLink()`, which fetches fresh link data from the API and updates the store signal.
This triggers a recompute chain:

```
integrityLinkStore.integrityLink()  (store signal updated from API)
  → initialApiSource (computed, wizard)      — only has source_layer (technical ID)
    → apiInitialValue (computed, selector)
      → initialValue input (DataSourceApiComponent)
        → effect() → selectedLayer.set(init)  — layerTitle is undefined
          → template re-renders: layerTitle || layerName = "ns:buildings"
```

`layerTitle` (the human-readable label from WFS/OGC GetCapabilities) is never stored on the backend.
Once the store reloads, it's lost, and the card briefly shows the technical layer identifier before
the wizard navigates to the next step.

## Fix

**File:** `apps/frontend/src/app/shared/components/data-source-api/data-source-api.component.ts`

In the `effect()` constructor, before overwriting `selectedLayer`, read the current value with
`untracked()` (to avoid adding a reactive dependency that would cause an infinite loop). If the
incoming `init` has no `layerTitle` but the existing `selectedLayer` has the same `layerName`,
preserve the existing `layerTitle`.

```ts
import { Component, effect, input, output, signal, untracked } from '@angular/core'

// Inside constructor effect():
effect(() => {
  const init = this.initialValue()
  if (init) {
    const prev = untracked(() => this.selectedLayer())
    const layerTitle =
      init.layerTitle ?? (prev?.layerName === init.layerName ? prev?.layerTitle : undefined)
    this.selectedLayer.set({ ...init, layerTitle })
    this.currentService.set({
      type: 'service',
      url: new URL(init.serviceUrl),
      accessServiceProtocol:
        (init.serviceProtocol as DatasetServiceDistribution['accessServiceProtocol']) ??
        'ogcFeatures',
      identifierInService: init.layerName
    })
  }
})
```

The `layerTitle` preservation logic:
- Preserves the existing title when `init.layerTitle` is absent AND the layer name matches (store reload of the same layer)
- Drops it when the layer name changes (user switched to a different layer)
- Always prefers `init.layerTitle` when the upstream provides one (user re-selects via gn-ui)

## Critical file

| File | Change |
|------|--------|
| `apps/frontend/src/app/shared/components/data-source-api/data-source-api.component.ts` | Add `untracked` to import; rewrite effect body to preserve `layerTitle` |

## Verification

1. Start a new import with `api` source type, select a WFS layer that has a human-readable title.
2. Confirm the card shows the human-readable title.
3. Click Next (submit staging) — verify the card does NOT flash to the technical identifier.
4. Edit an existing API import — verify the card still shows the stored layer name (identifier) correctly (no regression; `layerTitle` is `undefined` on edit-load, so it falls back gracefully).
5. Run `cd apps/frontend && npm run test:ut` — the existing spec for `DataSourceApiComponent` should still pass.
