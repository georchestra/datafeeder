import time
from datetime import datetime

import pytest
from common import get_feature_count, login, validate_dataset_ids
from playwright.sync_api import Page, expect

MEL_MAIRIE_FEATURES = 127
# Generated DAG parsed by the dag-processor (AIRFLOW__DAG_PROCESSOR__REFRESH_INTERVAL=30s),
# next "* * * * *" tick, then the triggered process_dag run.
SCHEDULED_RUN_TIMEOUT_SECONDS = 300


def _process_runs(page: Page, integrity_link_id: str) -> list[dict]:
    response = page.request.get(
        f"/datafeeder-backend/airflow/dags/process_dag/runs/{integrity_link_id}"
    )
    expect(response).to_be_ok()
    return response.json()["dag_runs"]


def _integrity_link(page: Page, integrity_link_id: str) -> dict:
    response = page.request.get(f"/datafeeder-backend/ingestion/integrity-link/{integrity_link_id}")
    expect(response).to_be_ok()
    return response.json()


class TestRecurrence:
    def test_every_minute_recurrence(self, page: Page, files_base_url: str):
        """A dataset scheduled every minute is re-ingested by Airflow, without user action."""
        login(page)
        page.goto("/dataset/import")
        page.get_by_placeholder("https://").fill(f"{files_base_url}/mel_mairie.json")
        page.locator("gn-ui-url-input").get_by_role("button").click()
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(
            timeout=30000
        )
        page.get_by_placeholder("Enter a title for your dataset").fill("recurrence")
        integrity_link_id, data_id = validate_dataset_ids(page, 30)

        # Run history only exists with Airflow: the local executor runs no schedule
        if not _process_runs(page, integrity_link_id):
            pytest.skip("Recurrence needs the Airflow task executor (TASK_EXECUTOR=AIRFLOW)")
        initial_retrieval = _integrity_link(page, integrity_link_id)["last_retrieval_timestamp"]

        # Through the sidebar, not page.goto(): on a cold load of /<id>/recurrence the
        # route guard runs before the integrity link is loaded and redirects to /edit.
        page.get_by_text("Recurrence", exact=True).click()
        page.locator('[data-test="recurrence-select"]').click()
        page.get_by_role("option", name="Every minute").click()
        # EVERY_MINUTE asks for a confirmation
        page.get_by_role("button", name="Continue").click()

        deadline = time.monotonic() + 10
        while True:
            integrity_link = _integrity_link(page, integrity_link_id)
            if integrity_link["schedule_enabled"]:
                break
            assert time.monotonic() < deadline, "recurrence not saved"
            page.wait_for_timeout(500)
        assert integrity_link["preset_id"] == "EVERY_MINUTE"
        assert integrity_link["schedule"] == "* * * * *"

        # Scheduled runs are the process_dag runs without the "_manual" suffix
        # (see apps/backend/src/core/run_ids.py). Their success callback, which updates
        # last_retrieval_timestamp, is sent after the run is marked successful: wait for both.
        deadline = time.monotonic() + SCHEDULED_RUN_TIMEOUT_SECONDS
        while True:
            scheduled = [
                run
                for run in _process_runs(page, integrity_link_id)
                if not run["dag_run_id"].endswith("_manual")
            ]
            failed = [run["dag_run_id"] for run in scheduled if run["state"] == "failed"]
            assert not failed, f"scheduled process_dag run(s) failed: {failed}"
            last_retrieval = _integrity_link(page, integrity_link_id)["last_retrieval_timestamp"]
            retrieved_again = datetime.fromisoformat(last_retrieval) > datetime.fromisoformat(
                initial_retrieval
            )
            if retrieved_again and any(run["state"] == "success" for run in scheduled):
                break
            assert time.monotonic() < deadline, (
                f"no successful scheduled run within {SCHEDULED_RUN_TIMEOUT_SECONDS}s: "
                f"{[(run['dag_run_id'], run['state']) for run in scheduled]}, "
                f"last_retrieval_timestamp={last_retrieval} (initial {initial_retrieval})"
            )
            page.wait_for_timeout(5000)

        assert get_feature_count(page, data_id) == MEL_MAIRIE_FEATURES

        page.get_by_text("Events", exact=True).click()
        expect(page.get_by_text("Scheduled").first).to_be_visible(timeout=15000)

        # Stop the schedule before the dataset is deleted by the conftest fixture
        response = page.request.delete(
            f"/datafeeder-backend/ingestion/integrity-link/{integrity_link_id}/schedule"
        )
        expect(response).to_be_ok()
