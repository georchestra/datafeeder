---
name: angular-datakern
description: Build Angular 20 applications following DataKern architecture patterns. Use when working with Angular components, services, or features in apps/frontend/. Covers standalone components, zoneless change detection, signals, NgRx state management, Tailwind CSS styling, atomic design principles, smart/presentational component separation, i18n with ngx-translate, and Vitest testing. Essential for implementing UI features, creating components, managing state, or maintaining frontend code in the DataKern project.
---

# Angular DataKern Development

Build Angular 20 applications following DataKern's established architecture patterns, atomic design principles, and coding standards.

## Quick Start

### Creating a New Component

**Presentational Component** (no services, pure UI):

```typescript
import { Component, Input, Output, EventEmitter } from '@angular/core'
import { CommonModule } from '@angular/common'
import { TranslateDirective } from '@ngx-translate/core'

@Component({
  selector: 'app-status-badge',
  imports: [CommonModule, TranslateDirective],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.css'
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: StatusType
  @Output() statusClick = new EventEmitter<void>()
}
```

**Smart Component** (with services and state):

```typescript
import { Component, inject, signal, computed, OnInit } from '@angular/core'
import { Router } from '@angular/router'
import { Api } from '../../core/api/api'
import { MyPresentationalComponent } from '../../shared/components/my-component'

@Component({
  selector: 'app-my-feature',
  imports: [MyPresentationalComponent],
  templateUrl: './my-feature.component.html'
})
export class MyFeatureComponent implements OnInit {
  private readonly api = inject(Api)
  private readonly router = inject(Router)
  
  data = signal<Data[]>([])
  filteredData = computed(() => this.data().filter(d => d.active))
  
  async ngOnInit() {
    const result = await this.api.getData()
    this.data.set(result)
  }
}
```

### Component Placement

- **Atoms/Molecules** (reusable UI) → `app/shared/components/`
- **Organisms** (feature-specific) → `app/features/{feature}/components/`
- **Smart Components** → `app/features/{feature}/`
- **Services** → `app/core/` (singleton) or `app/features/{feature}/` (feature-specific)

## Core Principles

1. **Standalone Components**: All components use standalone API (no NgModules)
2. **Zoneless Change Detection**: Application uses signals for reactivity
3. **Atomic Design**: Components organized as atoms → molecules → organisms
4. **Smart/Dumb Separation**: Container components manage state, presentational components display
5. **Dependency Injection**: Use `inject()` function over constructor injection
6. **Component Size Limit**: Maximum 200 lines (TypeScript + template + styles combined)

## Architecture

### Directory Structure

```
app/
├── core/          # Singleton services, API client, auth, layout
├── shared/        # Reusable components, pipes, directives, types
├── features/      # Feature modules (import, metadata, events, etc.)
└── layout/        # Page layout orchestration
```

**See [references/architecture-patterns.md](references/architecture-patterns.md) for detailed directory structure, module rules, and component patterns.**

## State Management

### Local State: Use Signals

```typescript
export class MyComponent {
  count = signal(0)
  doubleCount = computed(() => this.count() * 2)
  
  increment() {
    this.count.update(v => v + 1)
  }
}
```

### Global State: Use NgRx

```typescript
export class MyContainerComponent {
  private readonly store = inject(Store)
  
  data$ = this.store.pipe(select(selectMyData))
  
  onAction() {
    this.store.dispatch(myAction({ payload }))
  }
}
```

**See [references/state-management.md](references/state-management.md) for NgRx configuration, effects, selectors, and when to use signals vs NgRx.**

## Styling

Use **Tailwind CSS 3** utility classes:

```html
<div class="flex items-center gap-4 p-4 bg-white rounded-lg shadow-md">
  <span class="text-lg font-semibold text-gray-900" translate>title</span>
</div>
```

**Angular Material** components available for complex UI:
- `MatTabsModule`, `MatButtonToggleModule`, `MatDialogModule`

**geonetwork-ui** components for geospatial features:
- `ButtonComponent`, `SpinningLoaderComponent`, `FeatureEditorModule`

**See [references/styling.md](references/styling.md) for Tailwind patterns, color palette, responsive design, and component-specific styles.**

## Internationalization

Use **ngx-translate** for all user-facing text:

```html
<!-- Template -->
<h1 translate>import.title</h1>
<p>{{ 'import.status.' + status | translate }}</p>
```

```typescript
// TypeScript
import { marker } from '@biesbjerg/ngx-translate-extract-marker'

const label = marker('import.action.submit')
```

Extract translations:
```bash
npm run i18n:extract
```

**See [references/i18n.md](references/i18n.md) for translation file structure, extraction workflow, and best practices.**

## Testing

Use **Vitest** for unit tests:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/angular'

describe('StatusBadgeComponent', () => {
  it('should render status', async () => {
    await render(StatusBadgeComponent, {
      componentInputs: { status: 'success' }
    })
    
    expect(screen.getByText('success')).toBeDefined()
  })
})
```

Run tests:
```bash
npm run test:ut
```

**See [references/testing.md](references/testing.md) for testing patterns, mocking services, and E2E testing with Cypress.**

## API Integration

Use generated API client from **ng-openapi-gen**:

```typescript
import { inject } from '@angular/core'
import { Api } from '../../core/api/api'
import { lastValueFrom } from 'rxjs'

export class MyComponent {
  private readonly api = inject(Api)
  
  async loadData() {
    const data = await lastValueFrom(
      this.api.getData({ param: 'value' })
    )
    return data
  }
}
```

Generate API client:
```bash
npm run generate-api
```

## Development Workflow

1. **Create component**: Place in appropriate directory (shared vs feature)
2. **Write component code**: Follow standalone, signals, atomic design
3. **Add translations**: Mark strings with `translate` or `marker()`
4. **Extract translations**: Run `npm run i18n:extract`
5. **Write tests**: Create `.spec.ts` with Vitest
6. **Run tests**: `npm run test:ut`
7. **Check formatting**: `npm run format:check` or auto-fix with `npm run format`
8. **Check linting**: `npm run lint`

## Common Patterns

### Async Data Loading

```typescript
export class MyComponent implements OnInit {
  private readonly api = inject(Api)
  
  data = signal<Data[]>([])
  loading = signal(true)
  error = signal<string | null>(null)
  
  async ngOnInit() {
    try {
      const result = await lastValueFrom(this.api.getData())
      this.data.set(result)
    } catch (err) {
      this.error.set('Failed to load data')
    } finally {
      this.loading.set(false)
    }
  }
}
```

### Form Handling

```typescript
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'

export class MyFormComponent {
  private readonly fb = inject(FormBuilder)
  
  form = this.fb.group({
    name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]]
  })
  
  onSubmit() {
    if (this.form.valid) {
      const value = this.form.value
      // Process form
    }
  }
}
```

### Routing

```typescript
import { Router } from '@angular/router'

export class MyComponent {
  private readonly router = inject(Router)
  
  navigateToDetail(id: string) {
    this.router.navigate(['/detail', id])
  }
}
```

## Technology Stack

- **Angular**: 20.3.16 (latest)
- **NgRx**: 20.1.0 (Store, Effects, Router Store)
- **Tailwind CSS**: 3.x
- **Angular Material**: 20.2.14
- **geonetwork-ui**: 2.9.0-dev
- **ngx-translate**: 16.0.4
- **Vitest**: Latest (for unit tests)
- **Cypress**: Latest (for E2E tests)

## References

- **[architecture-patterns.md](references/architecture-patterns.md)** - Detailed directory structure, module rules, component types, naming conventions
- **[state-management.md](references/state-management.md)** - NgRx configuration, signals vs NgRx, effects, selectors
- **[styling.md](references/styling.md)** - Tailwind patterns, responsive design, Angular Material integration
- **[i18n.md](references/i18n.md)** - Translation workflow, key structure, extraction
- **[testing.md](references/testing.md)** - Unit tests with Vitest, E2E tests with Cypress, coverage
