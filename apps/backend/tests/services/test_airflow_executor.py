from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from airflow_client.client.models.dag_run_state import DagRunState

from src.core.constants import DEFAULT_DATA_SCHEMA
from src.core.task_executor import TaskStatus
from src.services.executors.airflow_executor import (
    AirflowTaskExecutor,
    _convert_airflow_status,  # type: ignore
)


class TestAirflowTaskExecutor:
    def test_trigger_staging_task(self) -> None:
        executor = AirflowTaskExecutor()
        dag_run_response = MagicMock(
            dag_id="staging_dag",
            dag_run_id="run-123",
            state=DagRunState.QUEUED,
        )

        with patch(
            "src.services.executors.airflow_executor.get_dag_run_api"
        ) as mock_get_dag_run_api:
            mock_get_dag_run_api.return_value.trigger_dag_run.return_value = dag_run_response

            result = executor.trigger_staging_task(
                run_id="run-123",
                staging_table_name="stg_table",
                source="/tmp/data.csv",
                source_type="FILE",
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
                encrypted_credentials="enc-creds",
            )

            trigger_call = mock_get_dag_run_api.return_value.trigger_dag_run.call_args.kwargs
            body = trigger_call["trigger_dag_run_post_body"]

            assert trigger_call["dag_id"] == "staging_dag"
            assert body.dag_run_id == "run-123"
            assert body.conf == {
                "staging_table_name": "stg_table",
                "source": "/tmp/data.csv",
                "source_type": "FILE",
                "success_callback_url": "https://ok.example.com",
                "failure_callback_url": "https://ko.example.com",
                "encrypted_credentials": "enc-creds",
                "source_layer": None,
                "source_protocol": None,
            }
            assert result.task_id == "staging_dag"
            assert result.run_id == "run-123"
            assert result.status == TaskStatus.QUEUED
            assert result.execution_date is None

    def test_trigger_staging_task_with_api_source(self) -> None:
        executor = AirflowTaskExecutor()
        dag_run_response = MagicMock(
            dag_id="staging_dag",
            dag_run_id="run-api",
            state=DagRunState.QUEUED,
        )

        with patch(
            "src.services.executors.airflow_executor.get_dag_run_api"
        ) as mock_get_dag_run_api:
            mock_get_dag_run_api.return_value.trigger_dag_run.return_value = dag_run_response

            result = executor.trigger_staging_task(
                run_id="run-api",
                staging_table_name="stg_api",
                source="https://example.com/wfs",
                source_type="API",
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
                encrypted_credentials=None,
                source_layer="ns:buildings",
                source_protocol="wfs",
            )

            trigger_call = mock_get_dag_run_api.return_value.trigger_dag_run.call_args.kwargs
            body = trigger_call["trigger_dag_run_post_body"]

            assert body.conf["source_type"] == "API"
            assert body.conf["source_layer"] == "ns:buildings"
            assert body.conf["source_protocol"] == "wfs"
            assert result.status == TaskStatus.QUEUED

    def test_trigger_process_task(self) -> None:
        executor = AirflowTaskExecutor()
        retrieval_ts = datetime(2026, 1, 2, 3, 4, 5)
        dag_run_response = MagicMock(
            dag_id="process_dag",
            dag_run_id="run-456",
            state=DagRunState.RUNNING,
        )

        with patch(
            "src.services.executors.airflow_executor.get_dag_run_api"
        ) as mock_get_dag_run_api:
            mock_get_dag_run_api.return_value.trigger_dag_run.return_value = dag_run_response

            result = executor.trigger_process_task(
                run_id="run-456",
                staging_table_name="stg_table",
                final_table_name="final_table",
                integrity_transformation={"steps": ["normalize"]},
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
                last_retrieval_timestamp=retrieval_ts,
            )

            trigger_call = mock_get_dag_run_api.return_value.trigger_dag_run.call_args.kwargs
            body = trigger_call["trigger_dag_run_post_body"]

            assert trigger_call["dag_id"] == "process_dag"
            assert body.dag_run_id == "run-456"
            assert body.conf == {
                "staging_table_name": "stg_table",
                "final_table_name": "final_table",
                "integrity_transformation": {"steps": ["normalize"]},
                "success_callback_url": "https://ok.example.com",
                "failure_callback_url": "https://ko.example.com",
                "last_retrieval_timestamp": retrieval_ts,
                "target_schema": DEFAULT_DATA_SCHEMA,
            }
            assert result.task_id == "process_dag"
            assert result.run_id == "run-456"
            assert result.status == TaskStatus.RUNNING
            assert result.execution_date is None

    def test_get_task_status(self) -> None:
        executor = AirflowTaskExecutor()
        dag_run_response = MagicMock(
            dag_id="process_dag",
            dag_run_id="run-789",
            state=DagRunState.SUCCESS,
        )

        with patch(
            "src.services.executors.airflow_executor.get_dag_run_api"
        ) as mock_get_dag_run_api:
            mock_get_dag_run_api.return_value.get_dag_run.return_value = dag_run_response

            result = executor.get_task_status(task_id="process_dag", run_id="run-789")

            mock_get_dag_run_api.return_value.get_dag_run.assert_called_once_with(
                dag_id="process_dag", dag_run_id="run-789"
            )
            assert result.task_id == "process_dag"
            assert result.run_id == "run-789"
            assert result.status == TaskStatus.SUCCESS
            assert result.execution_date is None

    def test_get_task_logs(self) -> None:
        executor = AirflowTaskExecutor()

        with patch(
            "src.services.executors.airflow_executor.generate_failed_dag_run_logs",
            return_value="failed logs",
        ) as mock_generate_logs:
            result = executor.get_task_logs(task_id="process_dag", run_id="run-42")

            mock_generate_logs.assert_called_once_with("process_dag", "run-42")
            assert result == "failed logs"


@pytest.mark.parametrize(
    ("airflow_status", "expected"),
    [
        (DagRunState.QUEUED, TaskStatus.QUEUED),
        (DagRunState.RUNNING, TaskStatus.RUNNING),
        (DagRunState.SUCCESS, TaskStatus.SUCCESS),
        (DagRunState.FAILED, TaskStatus.FAILED),
    ],
)
def test_convert_airflow_status_known_mappings(
    airflow_status: DagRunState, expected: TaskStatus
) -> None:
    assert _convert_airflow_status(airflow_status) == expected


def test_convert_airflow_status_unknown_falls_back_to_queued(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class UnknownState:
        value = "mystery"

    caplog.set_level("WARNING")

    result = _convert_airflow_status(UnknownState())  # type: ignore

    assert result == TaskStatus.QUEUED
    assert "fallback to QUEUED" in caplog.text
