## Context

The current recurrence system implements a fully configurable frequency pipeline: environment variable `RECURRENCE_FREQUENCIES` → settings API → frontend selector → frequency parsing service → cron generation → `IntegrityLink.schedule`. This pipeline involves ~6 files across backend and frontend, handles edge cases (Feb 29, nocturnal execution hour anchoring), and generates dynamic i18n labels from `<amount><unit>` codes.

In practice, only a small fixed set of recurrence options is needed. The existing complexity is unjustified. Additionally, the recurrence is only settable during the initial import wizard — there is no way to view or manage it afterward on the dataset detail page. Admins who modify cron expressions directly in the database have no frontend visibility into their changes.

The Figma design (node `1119-21266`) shows the recurrence displayed on the dataset detail/metadata page within the `intlink-layout` shell, accessible via the `/:intlink_id/edit` route.

## Goals / Non-Goals

**Goals:**
- Replace the configurable frequency system with a fixed set of 6 hardcoded presets (EVERY_MINUTE, EVERY_HOUR, EVERY_DAY, EVERY_WEEK, EVERY_MONTH, EVERY_YEAR)
- Display recurrence as read-only on the dataset detail page (metadata feature), supporting preset labels and cronstrue fallback for custom crons
- Simplify the backend by removing `apps/backend/src/services/recurrence_service.py` and the `RECURRENCE_FREQUENCIES` config setting. Keep `RECURRENCE_EXECUTION_HOUR` as configurable execution hour for daily+ presets
- Ensure admin-modified cron values are visible in the frontend via cronstrue

**Non-Goals:**
- Editing recurrence from the dataset detail page (deferred — "reconfigure" button will handle this later)
- Per-user permission checks on recurrence changes (deferred)
- Changing the ELT/Airflow DAG generation logic (already works with raw cron from DB)
- Migration of existing `IntegrityLink.schedule` values (existing crons remain valid)

## Decisions

### Decision 1: Hardcoded Python StrEnum for presets

Define a `RecurrencePreset` StrEnum in a new module `apps/backend/src/models/recurrence.py`:

```python
from src.core.config import get_settings
_settings = get_settings()

class RecurrencePreset(str, Enum):
    EVERY_MINUTE = "EVERY_MINUTE"
    EVERY_HOUR = "EVERY_HOUR"
    EVERY_DAY = "EVERY_DAY"
    EVERY_WEEK = "EVERY_WEEK"
    EVERY_MONTH = "EVERY_MONTH"
    EVERY_YEAR = "EVERY_YEAR"

    @property
    def cron(self) -> str:
        return _CRON_EXPRESSIONS[self]

    @classmethod
    def from_cron(cls, cron: str) -> RecurrencePreset | None:
        return _CRON_TO_PRESET.get(cron)
```

Cron expressions for `EVERY_DAY` and above use `_settings.RECURRENCE_EXECUTION_HOUR` (default: 4). `EVERY_MINUTE` and `EVERY_HOUR` are fixed.

**Why StrEnum over Literal or plain dict:** StrEnum integrates naturally with FastAPI/Pydantic for request validation (automatic 422 on invalid value), is self-documenting, and the string values serialize cleanly to JSON. The `.cron` property and `.from_cron()` classmethod encapsulate mapping logic inside the enum.

**Alternative considered:** Keep frequency codes (`1d`, `1w`) as presets — rejected because the whole point is to decouple from the frequency-parsing machinery and use explicit, readable identifiers.

### Decision 2: Recurrence response model with `cron` + `preset_id`

The `GET /ingestion/integrity-link/{id}/recurrence` endpoint returns a flat response:

```python
class RecurrenceResponse(BaseModel):
    cron: str | None = None
    preset_id: str | None = None
```

The backend reads `IntegrityLink.schedule` (a raw cron string) and performs a reverse-lookup in `CRON_PRESET_MAP` to resolve `preset_id`. The `preset_id` is never stored in the database — it is derived at each call.

- If the cron matches a known preset → `{ "cron": "0 4 * * *", "preset_id": "EVERY_DAY" }`
- If the cron is custom (admin-modified) → `{ "cron": "30 2 15 * *", "preset_id": null }`
- If no schedule → `{ "cron": null, "preset_id": null }`

**Why no `type` discriminator:** The presence/absence of `preset_id` is the discriminator. A separate `type` field adds no information and increases model complexity. The frontend checks `preset_id != null` to decide between i18n label vs cronstrue fallback.

**Why a dedicated endpoint over extending IntegrityLinkResponse:** Separation of concerns — the recurrence endpoint does the reverse-mapping logic server-side, keeping the frontend simple. Also prepares for future expansion (edit endpoint at the same path with PUT).

### Decision 3: Rewrite `RecurrenceSelectorComponent` to a presenter

Rewrite `apps/frontend/src/app/shared/components/recurrence-selector/` as a presentational component that:
- Takes a `RecurrenceResponse` as input (from the new endpoint)
- Displays a Material select/combobox in disabled state
- Maps preset IDs to i18n keys: `recurrence.preset.EVERY_DAY` → "Tous les jours"
- Falls back to cronstrue for custom crons
- Shows a "none" placeholder when no schedule

**Why cronstrue over custom label logic:** cronstrue is a proven library that handles all cron patterns. We avoid reinventing cron description. It supports locale via `cronstrue/locales/fr`.

### Decision 4: Remove settings recurrence fields

The `GET /settings` response removes `recurrence_frequencies` and `recurrence_execution_hour`. The new preset list endpoint `GET /ingestion/recurrence-presets` replaces this. Settings endpoint retains only `projections`.

**Why a separate endpoint over keeping in settings:** The presets are domain-specific to ingestion recurrence and include cron expressions — they don't belong in the generic settings bag. Placing them under `/ingestion/` groups related endpoints cleanly.

### Decision 5: Process endpoint uses preset enum

`ProcessRequest.recurrence_frequency` is renamed to `recurrence` and typed as `RecurrencePreset | None`. Pydantic validates the enum value automatically — no custom validation service needed.

**BREAKING**: The field name and accepted values change. Frontend must be updated simultaneously.

### Decision 6: Frontend cronstrue dependency

Add `cronstrue` npm package to `apps/frontend/package.json`. Use it with locale support for French:

```typescript
import cronstrue from 'cronstrue/i18n'
cronstrue.toString(cron, { locale: currentLang })
```

**Alternative considered:** Server-side cron description — rejected to keep the backend stateless about display concerns and avoid a new dependency in Python.

## Risks / Trade-offs

- **[Risk] Existing IntegrityLinks with non-preset crons** → Mitigation: The `preset_id: null` response path + cronstrue displays these correctly. No data migration needed.
- **[Risk] cronstrue locale coverage may be incomplete** → Mitigation: cronstrue supports French natively. If a locale is missing, it falls back to English.
- **[Risk] Breaking API change on `/ingestion/process`** → Mitigation: Frontend and backend are deployed together in this monorepo. Coordinate in a single release.
- **[Trade-off] Fixed recurrence options** → Acceptable: Six presets (minute through year) cover all common scheduling needs. Custom crons can be set by admins directly in DB.

## Migration Plan

1. No database migration needed — `IntegrityLink.schedule` column is unchanged
2. Remove environment variable `RECURRENCE_FREQUENCIES` from `apps/backend/datafeeder.env` and Docker config. `RECURRENCE_EXECUTION_HOUR` is kept as a configurable setting (default: 4)
3. Deploy backend + frontend simultaneously (breaking API change)
4. Existing scheduled IntegrityLinks continue working — their cron expressions are already stored and read by Airflow DAG generator unchanged

## Open Questions

- None — scope is well-defined and self-contained for a read-only first phase.
