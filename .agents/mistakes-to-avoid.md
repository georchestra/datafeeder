# Mistakes to Avoid

A living list of anti-patterns inferred from past implementation errors. Every agent and skill MUST consult this list **before starting any implementation**. Whenever an error is discovered and fixed during implementation, a correction rule MUST be inferred from the fix and appended here.

**Rule format**: add a row with `Domain`, `Directive`, `Rule`, and `Reason` columns.

**Available domain tags**:

| Tag        | Scope                                            |
| ---------- | ------------------------------------------------ |
| `backend`  | `apps/backend` — FastAPI application             |
| `frontend` | `apps/frontend` — Angular application            |
| `elt`      | `apps/elt` — Airflow DAGs and ELT pipelines      |
| `shared`   | `libs/data_manipulation` — shared Python library |
| `infra`    | Docker, Makefile, CI/CD, environment config      |
| `all`      | Cross-cutting — applies to every domain          |

**Available directive values**:

| Directive  | Meaning                                                   |
| ---------- | --------------------------------------------------------- |
| **Always** | Unconditional requirement — do it every time              |
| **Never**  | Unconditional prohibition — do not do it                  |
| **Prefer** | Strong default — deviate only with explicit justification |

| Domain     | Directive  | Rule                                                                                                                                                                       | Reason                                                                                                                                                          |
| ---------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `all`      | **Always** | Write self-documenting code: comments MUST explain "why", never "what"; MUST NOT duplicate the code; MUST NOT reference task IDs, user stories, or implementation metadata | Comments that restate the code or reference external trackers rot quickly and add noise without value                                                           |
| `frontend` | **Always** | Reuse a single `OverlayRef` (or dispose it on close) and unsubscribe from outside-click events when using Angular CDK Overlay                                              | Creating a new `OverlayRef` on every `openMenu()` call without disposing leaks overlay instances and subscriptions across open/close cycles                     |
| `shared`   | **Always** | Keep the OpenAPI contract in sync with the implementation as query parameters and response fields are introduced                                                           | Implementation can diverge from the contract spec without notice (e.g., missing `include_excluded` param, missing `original_type` field on `ColumnConfig`)      |
| `shared`   | **Always** | Escape SQL LIKE wildcards (`%`, `_`) in user-provided filter values                                                                                                        | Unescaped characters are treated as wildcards, producing incorrect matches for text that literally contains those characters                                    |
| `shared`   | **Never**  | Use `pandas.astype(bool)` to cast text columns to boolean — use an explicit mapper covering `true/false/1/0/yes/no` and preserve nulls                                     | Any non-empty string (including `"false"`) evaluates to `True`                                                                                                  |
| `shared`   | **Always** | Raise an explicit exception when all columns are excluded before ingestion                                                                                                 | Silently returning an empty DataFrame causes downstream transformations and ELT steps to write an empty table without any user-facing error                     |
| `frontend` | **Always** | Bind debounced text inputs to `(input)` or `ngModelChange` instead of `(change)`                                                                                           | The `change` event only fires on blur/commit, making debounce ineffective while the user is typing                                                              |
| `frontend` | **Prefer** | `takeUntilDestroyed()` over manual `takeUntil(destroy$)` patterns in Angular components                                                                                    | Less boilerplate and idiomatic Angular 20 when a `DestroyRef` is available                                                                                      |
| `frontend` | **Prefer** | CSS `group`/`group-hover:` Tailwind utilities over a JS signal (`hoveredId`) for simple hover-reveal patterns                                                              | A signal and `(mouseenter)`/`(mouseleave)` bindings add unnecessary reactive state; Tailwind group hover achieves the same result with zero JS                  |
| `all`      | **Prefer** | Prefer camelCase for new i18n translation keys (e.g. `dashboard.deleteDataset`); only use snake_case when extending an existing underscore-based namespace                 | The codebase mixes camelCase and snake_case; defaulting to camelCase for new keys while preserving established snake_case namespaces avoids confusion and churn |
| `shared`   | **Prefer** | Use `sqlalchemy.inspect(engine).has_schema()` / `.has_table()` instead of raw `information_schema` queries for existence checks                                            | SQLAlchemy's `inspect()` API is dialect-agnostic, less error-prone, and avoids hand-written SQL for metadata operations                                          |
| `backend`  | **Prefer** | Use Pydantic types (`PostgresDsn`, `AnyHttpUrl`, etc.) for URI config fields instead of plain `str`                                                                        | Pydantic validates the URI format at startup, catching misconfiguration early instead of failing at first use                                                    |
| `all`      | **Always** | Write specs in English, not French — even when the original delta specs or design docs were drafted in French                                                              | Mixed-language specs cause confusion; English is the project standard for specs                                                                                   |
