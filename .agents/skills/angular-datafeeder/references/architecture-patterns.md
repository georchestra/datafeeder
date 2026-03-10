# Angular Architecture Patterns

## Directory Structure

```
apps/frontend/src/
├── main.ts                    # Application bootstrap
├── index.html                 # HTML entry point
├── styles.scss               # Global styles
├── app/
│   ├── app.ts                # Root component
│   ├── app.routes.ts         # Application routing configuration
│   ├── app.config.ts         # Application-level providers and configuration
│   ├── core/                 # Core module (singleton services, app-wide concerns)
│   │   ├── api/              # Generated API client (ng-openapi-gen)
│   │   ├── auth/             # Authentication services
│   │   ├── layout/           # Global layout components (header, navigation)
│   │   └── settings/         # Application settings service
│   ├── shared/               # Shared module (reusable components, pipes, directives)
│   │   ├── components/       # Presentation components (buttons, forms, tables)
│   │   ├── directives/       # Reusable directives
│   │   ├── pipes/            # Reusable pipes (transforms)
│   │   ├── types/            # TypeScript interfaces/types
│   │   └── utils/            # Utility functions
│   ├── features/             # Feature modules (domain-specific functionality)
│   │   ├── import/           # Ingestion tunnel feature
│   │   ├── integrity-link-list/  # Dataset list/dashboard feature
│   │   ├── metadata/         # Metadata editor feature
│   │   └── events/           # Event journal feature
│   └── layout/               # Layout orchestration
└── translations/             # i18n JSON files (en, fr, de, etc.)
```

## Module Rules

### Core Module (`app/core/`)

- MUST contain singleton services, authentication, global layout, and app-wide state
- MUST be imported once in `app.config.ts`
- Components here are NOT feature-specific
- Examples: API client, auth service, settings service

### Shared Module (`app/shared/`)

- MUST contain reusable presentational components, pipes, directives, and utilities
- MUST NOT contain feature-specific logic or services
- Can be imported by any feature module
- Examples: status badge, alert box, search input

### Feature Modules (`app/features/`)

- MUST be self-contained with their own routing, components, services, and state
- Features SHOULD communicate via services or store, not direct component coupling
- Each feature represents a major user workflow or domain
- Examples: import (ingestion tunnel), metadata (metadata editor)

### Layout (`app/layout/`)

- MUST handle page layout composition (header, sidebar, content area orchestration)
- Orchestrates the overall page structure

## Component Architecture

### Atomic Design Principles

Components follow atomic design with clear hierarchy:

- **Atoms**: Basic UI elements (buttons, inputs, badges)
  - Location: `app/shared/components/`
  - Examples: status-badge, alert-box, search-input
  - Size: Small, focused, single-purpose

- **Molecules**: Composite components (forms, cards, lists)
  - Location: `app/shared/components/`
  - Examples: dataset-title, event-type-badge
  - Size: Combine atoms into functional units

- **Organisms**: Feature components (wizards, dashboards, complex forms)
  - Location: `app/shared/components/` or `app/features/`
  - Examples: data-import-wizard, events-list
  - Size: Complex, may contain business logic

### Component Types

**Presentational Components** (Dumb Components):

- Receive data via `@Input()`
- Emit events via `@Output()`
- Focus on display logic only
- NO service injection (except utilities like TranslateService)
- Example:

```typescript
@Component({
  selector: "app-status-badge",
  imports: [CommonModule, TranslateDirective],
  templateUrl: "./status-badge.component.html",
  styleUrl: "./status-badge.component.css",
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: StatusType;
}
```

**Smart Components** (Container Components):

- Inject services
- Manage state (NgRx Store)
- Handle routing
- Delegate to presentational components
- Example:

```typescript
@Component({
  selector: "app-import",
  imports: [DataImportWizardComponent],
  templateUrl: "./import.component.html",
})
export class ImportComponent implements OnInit {
  private readonly api = inject(Api);
  private readonly router = inject(Router);

  ngOnInit() {
    // Fetch data, manage state
  }
}
```

## Naming Conventions

- Components: `*.component.ts`
- Services: `*.service.ts`
- Directives: `*.directive.ts`
- Pipes: `*.pipe.ts`
- Types: `*.ts` (in `shared/types/`)
- Tests: `*.spec.ts`

## File Organization Rules

- Maximum component size: **200 lines** (TypeScript + HTML + CSS combined)
- Split larger components into smaller subcomponents
- Group related files by feature/domain
- One component per file
- Template and styles in separate files for complex components

## Standalone Components

All components MUST be standalone (Angular 20 best practice):

```typescript
@Component({
  selector: "app-example",
  imports: [CommonModule, TranslateDirective, OtherComponent],
  templateUrl: "./example.component.html",
  styleUrl: "./example.component.css",
})
export class ExampleComponent {}
```

## Change Detection

- Use **OnPush** change detection strategy by default for performance
- Use **signals** for reactive state (Angular 20 reactive primitives)
- Implement proper lifecycle hooks (OnInit, OnDestroy)
- Use takeUntil pattern for subscription cleanup

## Dependency Injection

Use modern Angular dependency injection with `inject()` function:

```typescript
export class MyComponent {
  private readonly api = inject(Api);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);
}
```
