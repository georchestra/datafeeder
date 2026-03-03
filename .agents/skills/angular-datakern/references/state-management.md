# State Management with NgRx

## Configuration

NgRx is configured in `app.config.ts`:

```typescript
import { StoreModule } from "@ngrx/store";
import { EffectsModule } from "@ngrx/effects";

export const appConfig: ApplicationConfig = {
  providers: [
    importProvidersFrom(
      StoreModule.forRoot(
        {},
        {
          metaReducers: [],
          runtimeChecks: {
            strictActionImmutability: false,
            strictStateImmutability: false,
          },
        },
      ),
    ),
    importProvidersFrom(EffectsModule.forRoot()),
    // ...other providers
  ],
};
```

## When to Use NgRx

Use NgRx for:

- Application-wide state that needs to be shared across features
- Complex state management with multiple data sources
- State that requires side effects (API calls, routing)
- State that needs to be persisted across navigation

Do NOT use NgRx for:

- Component-local state (use signals instead)
- Simple parent-child communication (use @Input/@Output)
- Read-only data (use services)

## Signals vs NgRx

**Use Signals** (Angular 20):

- Component-local reactive state
- Derived/computed values
- Simple reactive patterns
- Better performance for local state

```typescript
export class MyComponent {
  count = signal(0);
  doubleCount = computed(() => this.count() * 2);

  increment() {
    this.count.update((v) => v + 1);
  }
}
```

**Use NgRx**:

- Application-wide state
- Complex state with side effects
- State that needs to be shared across routes
- State history/time-travel debugging

## Smart Components Pattern

Smart components connect to the store:

```typescript
import { Store, select } from "@ngrx/store";
import { Observable } from "rxjs";

export class MyContainerComponent {
  private readonly store = inject(Store);

  data$: Observable<Data> = this.store.pipe(select(selectMyData));

  onAction() {
    this.store.dispatch(myAction({ payload }));
  }
}
```

## Effects for Side Effects

Use Effects for async operations:

```typescript
import { Injectable } from "@angular/core";
import { Actions, createEffect, ofType } from "@ngrx/effects";
import { map, catchError, switchMap } from "rxjs/operators";

@Injectable()
export class MyEffects {
  loadData$ = createEffect(() =>
    this.actions$.pipe(
      ofType(loadData),
      switchMap(() =>
        this.api.getData().pipe(
          map((data) => loadDataSuccess({ data })),
          catchError((error) => of(loadDataFailure({ error }))),
        ),
      ),
    ),
  );

  constructor(
    private actions$: Actions,
    private api: ApiService,
  ) {}
}
```

## Selectors

Create memoized selectors for efficient state derivation:

```typescript
import { createSelector, createFeatureSelector } from "@ngrx/store";

export const selectFeature = createFeatureSelector<FeatureState>("feature");

export const selectData = createSelector(selectFeature, (state) => state.data);

export const selectFilteredData = createSelector(
  selectData,
  selectFilter,
  (data, filter) => data.filter((item) => item.matches(filter)),
);
```
