from enum import Enum

from pydantic import BaseModel

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
    def from_cron(cls, cron: str) -> "RecurrencePreset | None":
        return _CRON_TO_PRESET.get(cron)


_CRON_EXPRESSIONS: dict[RecurrencePreset, str] = {
    RecurrencePreset.EVERY_MINUTE: "* * * * *",  # Every minute
    RecurrencePreset.EVERY_HOUR: "0 * * * *",  # Every hour at minute 0
    RecurrencePreset.EVERY_DAY: f"0 {_settings.RECURRENCE_EXECUTION_HOUR} * * *",  # Every day at the specified hour
    RecurrencePreset.EVERY_WEEK: f"0 {_settings.RECURRENCE_EXECUTION_HOUR} * * 1",  # Every Monday at the specified hour
    RecurrencePreset.EVERY_MONTH: f"0 {_settings.RECURRENCE_EXECUTION_HOUR} 1 * *",  # Every month on the 1st at the specified hour
    RecurrencePreset.EVERY_YEAR: f"0 {_settings.RECURRENCE_EXECUTION_HOUR} 1 1 *",  # Every year on January 1st at the specified hour
}

# Completeness check at import time
assert set(_CRON_EXPRESSIONS) == set(RecurrencePreset), (
    f"Missing cron for: {set(RecurrencePreset) - set(_CRON_EXPRESSIONS)}"
)

_CRON_TO_PRESET: dict[str, RecurrencePreset] = {v: k for k, v in _CRON_EXPRESSIONS.items()}


class RecurrencePresetItem(BaseModel):
    id: RecurrencePreset
    cron: str
