# Testing with Vitest

## Test Configuration

The project uses Vitest for unit testing Angular components:

```json
{
  "scripts": {
    "test:ut": "vitest",
    "test:ut:ci": "vitest --run"
  }
}
```

## Test Structure

Tests are colocated with components in `*.spec.ts` files:

```
app/
├── features/
│   └── import/
│       ├── import.component.ts
│       └── import.component.spec.ts
└── shared/
    └── components/
        └── status-badge/
            ├── status-badge.component.ts
            └── status-badge.component.spec.ts
```

## Writing Component Tests

### Basic Component Test

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/angular";
import { StatusBadgeComponent } from "./status-badge.component";

describe("StatusBadgeComponent", () => {
  it("should render status", async () => {
    await render(StatusBadgeComponent, {
      componentInputs: { status: "success" },
    });

    expect(screen.getByText("success")).toBeDefined();
  });
});
```

### Testing with Dependencies

```typescript
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/angular";
import { MyComponent } from "./my.component";
import { MyService } from "./my.service";

describe("MyComponent", () => {
  it("should call service", async () => {
    const mockService = {
      getData: vi.fn().mockResolvedValue([]),
    };

    await render(MyComponent, {
      providers: [{ provide: MyService, useValue: mockService }],
    });

    expect(mockService.getData).toHaveBeenCalled();
  });
});
```

## E2E Testing with Cypress

E2E tests use Cypress:

```json
{
  "scripts": {
    "test:e2e": "ng serve --port 4201 & cypress open",
    "test:e2e:ci": "ng serve --port 4201 & cypress run"
  }
}
```

Cypress tests are in `cypress/e2e/`:

```typescript
describe("Import workflow", () => {
  it("should complete data import", () => {
    cy.visit("/import");
    cy.get('[data-test="source-selector"]').click();
    cy.get('[data-test="local-file"]').click();
    // ...
  });
});
```

## Test Coverage

- Target: >80% coverage for critical paths
- Run coverage reports with `vitest --coverage`
- Focus on:
  - Business logic
  - Smart component state management
  - Service interactions
  - User workflows
