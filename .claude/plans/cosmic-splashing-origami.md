# Refactor: extract `app-data-source-api` component

## Context

The API source section (OGC service input + selected-service card) is currently inlined in `data-source-selector.component.html`. The FTP source follows a cleaner pattern — a dedicated `app-data-source-ftp` component owns its own template, form state, and emits a typed data object. This refactor applies the same pattern to the API case.

---

## Critical files

| File | Action |
|------|--------|
| `apps/frontend/src/app/shared/components/data-source-api/data-source-api.component.ts` | **Create** |
| `apps/frontend/src/app/shared/components/data-source-api/data-source-api.component.html` | **Create** |
| `apps/frontend/src/app/shared/components/data-source-api/data-source-api.component.spec.ts` | **Create** |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.ts` | **Modify** |
| `apps/frontend/src/app/shared/components/data-source-selector/data-source-selector.component.html` | **Modify** |

---

## `ApiData` interface

```ts
export interface ApiData {
  serviceUrl: string
  layerName: string
  serviceProtocol: string
}
```

---

## New component: `data-source-api`

**TS** — mirrors FTP pattern with signals instead of a form:
- `initialValue = input<ApiData | null>(null)` — pre-populate on edit
- `apiDataChanged = output<ApiData | null>()` — emits on select or remove
- `currentService = signal<DatasetServiceDistribution>({ ...EMPTY_SERVICE })` — feeds `gn-ui-online-service-resource-input`
- `selectedLayer = signal<ApiData | null>(null)` — drives template branch
- `effect()` on `initialValue` → sets both signals when non-null
- `handleServiceChange(service)` → sets `selectedLayer`, updates `currentService`, emits `apiDataChanged`
- `removeService()` → resets both signals, emits `null`
- `get protocolLabel()` → `'WFS'` or `'OGC API'` based on `selectedLayer()?.serviceProtocol`
- Imports: `NgIconComponent`, `ButtonComponent`, `OnlineServiceResourceInputComponent`, `provideIcons({ iconoirAxes })`

**HTML** — the exact markup currently in `data-source-selector`:
```html
@if (!selectedLayer()) {
  <div class="px-9 py-6">
    <gn-ui-online-service-resource-input [featuresOnly]="true" [service]="currentService()" (serviceChange)="handleServiceChange($event)" />
  </div>
} @else {
  <div class="px-9 py-6 bg-beige border-gray-600 border-t rounded-b-lg flex items-center">
    <div class="gn-ui-card bg-white flex-1">
      <div class="bg-beige w-[56px] h-[56px] rounded-[4px] text-secondary-darker grid justify-center items-center shrink-0">
        <ng-icon name="iconoirAxes"></ng-icon>
      </div>
      <div class="flex flex-col justify-center">
        <div class="text-lg font-bold">{{ selectedLayer()!.layerName }}</div>
        <div class="text-xs text-gray-500">{{ protocolLabel }} • {{ selectedLayer()!.layerName }}</div>
      </div>
    </div>
    <gn-ui-button type="light" ... (buttonClick)="removeService()" data-test="remove-item">
      <span class="material-symbols-outlined gn-ui-icon-medium">close</span>
    </gn-ui-button>
  </div>
}
```

---

## Changes to `data-source-selector`

**Remove:**
- `currentService` signal
- `handleServiceChange`, `removeService`, `protocolLabel`
- `iconoirAxes` import + provideIcons entry
- `OnlineServiceResourceInputComponent` from imports
- The `currentService.set(...)` line from the `initialApiSource` effect

**Add:**
- `DataSourceApiComponent` to imports
- `apiInitialValue = computed(() => { const src = this.initialApiSource(); if (!src) return null; return { serviceUrl: src.url, layerName: src.layerName, serviceProtocol: src.protocol } })`
- `handleApiDataChange(data: ApiData | null)` → patches `serviceUrl`, `layerName`, `serviceProtocol` in form (null → `null`)

**Template** — replace the inlined api block with:
```html
} @if (form.controls.radio.value === 'api') {
<app-data-source-api
  [initialValue]="apiInitialValue()"
  (apiDataChanged)="handleApiDataChange($event)"
/>
}
```

---

## Test spec (`data-source-api.component.spec.ts`)

Mirror `data-source-ftp.component.spec.ts`:
- `should create`
- `should emit apiDataChanged when a service is selected` (call `handleServiceChange` with a mock `DatasetServiceDistribution`)
- `should emit null when removeService is called`
- `should initialize from initialValue input`

---

## Verification

1. `cd apps/frontend && npm run lint && npm run test:ut` — no errors
2. In the app: select "Service & API OGC" → service input appears → pick a layer → card replaces input → close button resets to input
3. Edit an existing API import → card pre-populated with saved layer
