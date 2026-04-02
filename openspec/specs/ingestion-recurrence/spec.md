# Capability: Ingestion Recurrence

## Purpose

Defines how recurring ingestion schedules are configured, validated, stored, and displayed during the import wizard. Covers preset-based recurrence selection, cron storage, UI selector behaviour, and database schema requirements.

## Requirements

### Requirement: Recurrence persistence during the ingestion process

The system MUST allow setting or clearing a recurrence when finalising ingestion (process step). The `recurrence` field is always present in the request (a preset or explicit `null`) — there is no distinction between "not provided" and "null".

- If `recurrence` is a valid preset, the corresponding cron expression is stored in `IntegrityLink.schedule` and `schedule_enabled` is set to `true`.
- If `recurrence` is `null`, `IntegrityLink.schedule` is set to `null` and `schedule_enabled` is set to `false`. This allows removing an existing recurrence during reconfiguration.

#### Scenario: Process submitted with a recurrence preset

- **WHEN** the user submits the process form with `recurrence: "EVERY_DAY"`
- **THEN** the `schedule` field of the IntegrityLink MUST contain `0 4 * * *` and `schedule_enabled` MUST be `true`

#### Scenario: Process submitted with null recurrence (removal)

- **WHEN** the user submits the process form with `recurrence: null`
- **THEN** the `schedule` and `schedule_enabled` fields of the IntegrityLink MUST be reset to `null` and `false`

#### Scenario: Process submitted with an invalid preset

- **WHEN** the user submits the process form with `recurrence: "INVALID_VALUE"`
- **THEN** the backend MUST reject the request with HTTP 422

---

### Requirement: Recurrence selector in the ingestion wizard (step 2)

The ingestion wizard MUST display a recurrence selector on step 2 (configuration), only for remote sources (all except local file). The selector MUST present the recurrence presets defined by the backend.

#### Scenario: Selector displayed for a remote source

- **WHEN** the user is on step 2 of the wizard with a URL, FTP, API, or database source type
- **THEN** a recurrence selector MUST be visible with the available presets, and an empty default option (no recurrence)

#### Scenario: Selector hidden for a local file

- **WHEN** the user is on step 2 of the wizard with a local file source type
- **THEN** the recurrence selector MUST NOT be displayed

#### Scenario: Default selection

- **WHEN** the recurrence selector is displayed
- **THEN** the default value MUST be empty (no recurrence — one-shot ingestion)

#### Scenario: Selector option labels

- **WHEN** the selector displays the presets
- **THEN** each option MUST display the translated preset label (e.g. "Every minute", "Every hour", "Every day", "Every week", "Every month", "Every year")

---

### Requirement: Recurrence exposure in the IntegrityLink response

The `GET /ingestion/integrity-link/{id}` response MUST include the `preset_id` field in addition to the existing `schedule` field, allowing consumers to get both cron and preset in a single call.

#### Scenario: Retrieving an IntegrityLink with a configured recurrence

- **WHEN** the API receives `GET /ingestion/integrity-link/{id}` for an IntegrityLink whose `schedule` is `"0 4 * * *"`
- **THEN** the response MUST contain `schedule: "0 4 * * *"` and `preset_id: "EVERY_DAY"`

#### Scenario: Retrieving an IntegrityLink with no recurrence

- **WHEN** the API receives `GET /ingestion/integrity-link/{id}` for an IntegrityLink whose `schedule` is `null`
- **THEN** the response MUST contain `schedule: null` and `preset_id: null`

#### Scenario: Retrieving an IntegrityLink with a custom cron not mapped to a preset

- **WHEN** the API receives `GET /ingestion/integrity-link/{id}` for an IntegrityLink whose `schedule` is a cron expression that does not match any known preset
- **THEN** the response MUST contain the populated `schedule` and `preset_id: null`

---

### Requirement: Schedule column size increase in database

The `schedule` field of the `integrity_link` table MUST support cron expressions of sufficient length. The `max_length` constraint MUST be increased from 10 to 20 characters to accommodate the longest cron expressions.

#### Scenario: Schedule column migration

- **WHEN** the migration is applied
- **THEN** the `schedule` column of `datakern.integrity_link` MUST be of type `VARCHAR(63)`
