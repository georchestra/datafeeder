---
paths:
  - "apps/frontend/**"
---

- Reuse a single `OverlayRef` (or dispose on close) — never create a new one per `openMenu()`.
- Debounce text inputs on `(input)` or `ngModelChange`, not `(change)` (fires on blur only).
- Prefer `takeUntilDestroyed()` over manual `takeUntil(destroy$)`.
- Prefer Tailwind `group`/`group-hover:` over JS signals for simple hover-reveal patterns.
- i18n keys: camelCase for new keys, snake_case only when extending existing namespace.
