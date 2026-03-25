"""Tests for recurrence handling in the process endpoint."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.models.data_import import ImportType, ProcessRequest
from src.models.integrity_link import IntegrityLink
from src.models.recurrence import RecurrencePreset


def _make_integrity_link(link_id: str | None = None) -> IntegrityLink:
    return IntegrityLink(
        id=UUID(link_id) if link_id else uuid4(),
        integrity_owner="testuser",
        integrity_organization="testorg",
        source_import_type=ImportType.URL,
        source_url="http://example.com/data.geojson",
        staging_table_name="staging_test",
        final_table_name=None,
        schedule=None,
        schedule_enabled=False,
    )


class TestRecurrenceInProcessRequest:
    """Unit tests for recurrence field in ProcessRequest."""

    def test_process_request_accepts_preset(self) -> None:
        req = ProcessRequest(
            integrity_link_id=str(uuid4()),
            title="Test layer",
            recurrence=RecurrencePreset.EVERY_DAY,
        )
        assert req.recurrence == RecurrencePreset.EVERY_DAY

    def test_process_request_accepts_preset_as_string(self) -> None:
        req = ProcessRequest(
            integrity_link_id=str(uuid4()),
            title="Test layer",
            recurrence="EVERY_WEEK",  # type: ignore[arg-type]
        )
        assert req.recurrence == RecurrencePreset.EVERY_WEEK

    def test_process_request_defaults_recurrence_to_none(self) -> None:
        req = ProcessRequest(integrity_link_id=str(uuid4()), title="Test layer")
        assert req.recurrence is None

    def test_process_request_allows_null_recurrence(self) -> None:
        req = ProcessRequest(
            integrity_link_id=str(uuid4()),
            title="Test layer",
            recurrence=None,
        )
        assert req.recurrence is None

    def test_process_request_rejects_invalid_preset(self) -> None:
        with pytest.raises(ValidationError):
            ProcessRequest(
                integrity_link_id=str(uuid4()),
                title="Test layer",
                recurrence="INVALID_VALUE",  # type: ignore
            )


class TestPresetCronMapping:
    """Tests for preset → cron resolution used in the process endpoint."""

    @pytest.mark.parametrize(
        "preset",
        list(RecurrencePreset),
    )
    def test_preset_resolves_to_cron(self, preset: RecurrencePreset) -> None:
        cron = preset.cron
        assert isinstance(cron, str)
        assert len(cron.split()) == 5  # valid cron has 5 fields

    def test_preset_cron_stored_on_integrity_link(self) -> None:
        link = _make_integrity_link()
        cron = RecurrencePreset.EVERY_DAY.cron
        link.schedule = cron
        link.schedule_enabled = True
        assert link.schedule == cron
        assert link.schedule_enabled is True


class TestIntegrityLinkScheduleModel:
    """Tests that IntegrityLink model accepts preset cron values."""

    def test_schedule_accepts_every_day_cron(self) -> None:
        link = _make_integrity_link()
        cron = RecurrencePreset.EVERY_DAY.cron
        link.schedule = cron
        assert link.schedule == cron

    def test_schedule_accepts_every_month_cron(self) -> None:
        link = _make_integrity_link()
        cron = RecurrencePreset.EVERY_MONTH.cron
        link.schedule = cron
        assert link.schedule == cron

    def test_staging_retrieve_time_is_timedelta(self) -> None:
        link = _make_integrity_link()
        link.staging_retrieve_time = timedelta(hours=2)
        assert isinstance(link.staging_retrieve_time, timedelta)
