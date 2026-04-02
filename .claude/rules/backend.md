---
paths:
  - "apps/backend/**"
  - "libs/data_manipulation/**"
---

- API-First: define endpoints before UI.
- Backend + ELT = minimal system; GeoServer/GeoNetwork/Frontend are optional.
- Security: geOrchestra gateway auth via headers. `integrity_link` = data lineage source of truth.
- Keep OpenAPI contract in sync as query params and response fields are added.
- Escape SQL LIKE wildcards (`%`, `_`) in user-provided filter values.
- Never use `pandas.astype(bool)` on text — use explicit mapper covering true/false/1/0/yes/no, preserve nulls.
- Raise an explicit exception when all columns are excluded before ingestion.
- No XSLT 2.0 with lxml (1.0 only) — 2.0 functions silently produce empty output.
- Wrap post-success side-effects (e.g. GeoNetwork updates) in try/except with `logger.warning()` — never let optional steps mask a successful operation.
- Use `gco:DateTime` tag for datetime values, never write datetime strings into `gco:Date`.
- Prefer module-level exported constants for XML namespace maps over class attributes.
