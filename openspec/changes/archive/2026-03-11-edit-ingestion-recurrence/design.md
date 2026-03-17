## Context

The ingestion tunnel currently supports one-shot data ingestion from local files, URLs, FTP, databases, and APIs. The `IntegrityLink` model already persists `schedule` (str, max 10 chars) and `schedule_enabled` (bool) fields, and the Airflow `process-dag-generator.py` dynamically creates scheduled DAGs from those fields. However, there is no backend endpoint to write these fields, no cron conversion logic, and no frontend UI for recurrence selection.

The Figma mockup (node `979-19443`) shows a dropdown selector in step 2 of the ingestion wizard for choosing a recurrence frequency from a predefined list.

## Goals / Non-Goals

**Goals:**

- Expose a configurable list of recurrence frequencies from backend settings to the frontend
- Convert a human-readable frequency code (e.g. `1d`, `2M`) into a valid cron expression suitable for Airflow
- Apply nocturnal execution hours for daily-or-longer frequencies
- Anchor monthly+ frequencies to the current day-of-month (capping Feb 29 → 28)
- Persist the computed cron expression in `IntegrityLink.schedule` during the process step
- Provide a recurrence selector in the ingestion wizard step 2, visible only for remote sources
- Gray out frequencies shorter than the dataset's measured `staging_retrieve_time`

**Non-Goals:**

- Editing recurrence after initial ingestion (separate future feature on the Data Publisher sidebar)
- Pausing recurrence during dataset reconfiguration (separate task)
- Wiring Airflow DAG success/failure callbacks to real backend endpoints (already placeholder, separate task)
- Custom arbitrary cron expressions — only predefined frequency codes are allowed

## Decisions

### D1: Frequency format — Short codes (`1d`, `2M`) over raw cron

**Choice**: Use a compact `<amount><unit>` format (e.g. `1d`, `1M`, `2w`) as the user-facing and API-level frequency representation. The backend converts this to a cron expression before persisting.

**Rationale**: Raw cron is error-prone for users and harder to validate. Short codes are self-documenting, compact (fits existing `max_length=10`), and allow the backend to enforce business rules (nocturnal hour, day-of-month anchoring) during conversion.

**Alternatives considered**:
- Raw cron input: too complex for users, bypasses business rules
- Enum of fixed cron expressions: inflexible, can't anchor to current day-of-month dynamically

### D2: Settings structure — Extend `core/config.py` with two new fields

**Choice**: Add to `Settings`:
```python
RECURRENCE_FREQUENCIES: str = Field(
    default='["1m","1h","1d","1w","1M","1y"]',
    description="JSON array of allowed recurrence frequency codes",
)
RECURRENCE_EXECUTION_HOUR: int = Field(
    default=4,
    description="Hour (0-23) for nocturnal execution of daily+ schedules",
)
```

**Rationale**: Follows the existing pattern (cf. `PROJECTIONS` which is also a JSON string setting). Configurable via env vars without code changes. The execution hour is a single integer, simple and clear.

### D3: Cron conversion logic — New `recurrence_service.py`

**Choice**: Create `apps/backend/src/services/recurrence_service.py` containing:
- `parse_frequency(freq: str) -> tuple[int, str]` — parses `"2M"` into `(2, "M")`
- `frequency_to_cron(freq: str, execution_hour: int, reference_date: date) -> str` — returns cron expression

Conversion rules:
| Unit | Cron pattern | Example (`execution_hour=4`) |
|------|-------------|-----|
| `m` (minute) | `*/<n> * * * *` | `1m` → `*/1 * * * *` |
| `h` (hour) | `0 */<n> * * *` | `1h` → `0 */1 * * *` |
| `d` (day) | `0 <hour> */<n> * *` | `1d` → `0 4 */1 * *` |
| `w` (week) | `0 <hour> */<n*7> * *` | `1w` → `0 4 */7 * *` |
| `M` (month) | `0 <hour> <day> */<n> *` | `1M` (on Feb 27) → `0 4 27 */1 *` |
| `y` (year) | `0 <hour> <day> */<n*12> *` | `1y` (on Mar 15) → `0 4 15 */12 *` |

Special case: if `reference_date` is Feb 29, cap `day` to 28.

**Rationale**: Centralized, testable service. The reference date is passed at call time (process endpoint captures `date.today()`), making the function pure and easy to unit test.

### D4: API surface — Extend settings endpoint + process request

**Choice**:
1. **Settings**: Add `recurrence_frequencies: list[str]` and `recurrence_execution_hour: int` to the `get_all_settings()` response.
2. **Process request**: Add an optional `recurrence_frequency: str | None = None` field to `ProcessRequest`. When provided, backend validates it against allowed frequencies, converts to cron, and persists in `IntegrityLink.schedule` + sets `schedule_enabled = True`.

**Rationale**: API-first — the settings endpoint already serves frontend configuration (projections). The process endpoint is the natural place to set the schedule since that's when the user finalizes ingestion. No new endpoint needed.

**Alternatives considered**:
- Dedicated `PATCH /ingestion/integrity-link/{id}/schedule` endpoint: more RESTful but premature — the process step is the only place recurrence is set for now. Can be added later for the Data Publisher sidebar.

### D5: Frontend component — Presentational `RecurrenceSelectorComponent`

**Choice**: Create `apps/frontend/src/app/shared/components/recurrence-selector/` as a presentational component. It receives available frequencies and `staging_retrieve_time` as inputs, emits the selected frequency. The wizard's step 2 (smart component) integrates it.

**Rationale**: Follows atomic design (molecule-level component), smart/presentational separation. Reusable for the future Data Publisher sidebar recurrence editing.

### D6: Graying out fast frequencies — Compare against `staging_retrieve_time`

**Choice**: The backend already stores `staging_retrieve_time` on `IntegrityLink` (a `timedelta`). The frontend receives it in `IntegrityLinkResponse`. The recurrence selector maps each frequency code to a minimum duration and disables options where the frequency period is less than the retrieve time. A tooltip explains why.

Minimum durations for comparison:
| Code | Min duration |
|------|------------|
| `1m` | 60s |
| `1h` | 3600s |
| `1d` | 86400s |
| `1w` | 604800s |
| `1M` | 2592000s (30d) |
| `1y` | 31536000s (365d) |

### D7: Translation — `cronstrue` for human-readable cron display

**Choice**: Install `cronstrue` npm package for displaying generated cron expressions in human-readable form in the UI. Also add standard i18n keys for frequency labels in `translations/`.

**Rationale**: `cronstrue` is lightweight, well-maintained, and supports French locale. Useful for confirmation or display after selection.

## Risks / Trade-offs

- **[Risk] Single-value frequency only** → By design. The format `<amount><unit>` enforces one unit at a time. Compound expressions (e.g. "every 1 day and 5 minutes") are excluded. → *Mitigation*: Clear validation error message. Can be extended later if needed.
- **[Risk] Feb 29 edge case** → Anchoring monthly schedules to day 29 in February would cause cron to never fire in non-leap years → *Mitigation*: Cap to 28 when reference date is Feb 29. Documented and tested.
- **[Risk] `staging_retrieve_time` may be null** → If the staging DAG didn't record it, all frequencies are enabled → *Mitigation*: Acceptable — user assumes responsibility. A null check is simpler than blocking.
- **[Risk] DAG generator reads `schedule` directly** → The DAG generator already uses `IntegrityLink.schedule` as the Airflow cron. Changing the stored format could break existing schedules → *Mitigation*: The field stores the final cron expression (not the frequency code), so the DAG generator needs no changes.
- **[Trade-off] No database migration needed** → The `schedule` and `schedule_enabled` columns already exist. The `max_length=10` on `schedule` is sufficient for cron expressions (max: `*/60 */24 28 */12 *` = 18 chars). → *Action*: Increase `max_length` to 20 in the model to be safe. This is a model change only; the DB column is already `VARCHAR(10)` but since SQLModel doesn't auto-migrate, we need an Alembic migration to `ALTER COLUMN`.

## Open Questions

- Should the recurrence selector also be available when editing an existing dataset from the Data Publisher sidebar? (Currently scoped to ingestion wizard only — the sidebar link remains disabled.)
