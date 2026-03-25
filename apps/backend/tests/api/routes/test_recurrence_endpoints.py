"""Tests for recurrence API endpoints."""

from src.api.routes.ingestion.recurrence import list_recurrence_presets
from src.models.recurrence import RecurrencePreset


class TestListRecurrencePresets:
    def test_returns_all_presets(self) -> None:
        result = list_recurrence_presets()
        assert len(result) == len(RecurrencePreset)

    def test_preset_structure(self) -> None:
        result = list_recurrence_presets()
        ids = {item.id for item in result}
        assert ids == {p.value for p in RecurrencePreset}

    def test_cron_values_match_map(self) -> None:
        result = list_recurrence_presets()
        for item in result:
            preset = RecurrencePreset(item.id)
            assert item.cron == preset.cron
