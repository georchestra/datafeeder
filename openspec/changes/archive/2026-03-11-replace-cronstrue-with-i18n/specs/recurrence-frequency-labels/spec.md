## ADDED Requirements

### Requirement: Recurrence frequency labels must not expose scheduling details
The `RecurrenceSelectorComponent` SHALL display frequency option labels as plain period descriptions (e.g. "Every 2 days") without exposing the underlying scheduled time of day.

#### Scenario: Singular period label
- **WHEN** a frequency code with count 1 is rendered (e.g. `"1d"`)
- **THEN** the label SHALL read "Every day" (singular form, no count)

#### Scenario: Plural period label
- **WHEN** a frequency code with count > 1 is rendered (e.g. `"2d"`)
- **THEN** the label SHALL read "Every 2 days" (plural form with count)

#### Scenario: Label is locale-aware
- **WHEN** the application locale is set (e.g. `"fr"`)
- **THEN** the label SHALL be rendered in that locale's translation

#### Scenario: Unknown frequency code falls back to raw code
- **WHEN** a frequency code does not match the expected pattern
- **THEN** the component SHALL display the raw code string as the label
