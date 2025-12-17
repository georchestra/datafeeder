from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.services.airflow_logs import generate_failed_dag_run_logs


class DummyTaskInstance:
    def __init__(self, task_id: str, try_number: int):
        self.task_id = task_id
        self.try_number = try_number


class DummyLogEntry:
    def __init__(self, event: str, timestamp: str | None = None):
        self.event = event
        self.timestamp = timestamp


class DummyLogContent:
    def __init__(self, actual_instance: list[DummyLogEntry]):
        self.actual_instance = actual_instance


class DummyDagRunLogs:
    def __init__(self, content: DummyLogContent):
        self.content = content


class DummyTaskInstances:
    def __init__(self, task_instances: list[DummyTaskInstance]):
        self.task_instances = task_instances


@patch("src.services.airflow_logs.get_task_instance_api")
def test_generate_failed_dag_run_logs_success(mock_get_task_instance_api: MagicMock):
    # Setup dummy data
    task_instance = DummyTaskInstance("task1", 1)
    log_entry1 = DummyLogEntry("event1", timestamp=None)
    log_entry2 = DummyLogEntry("event2", timestamp=None)
    dummy_logs = DummyDagRunLogs(DummyLogContent([log_entry1, log_entry2]))
    dummy_task_instances = DummyTaskInstances([task_instance])

    # Mock API methods
    mock_api = MagicMock()
    mock_api.get_task_instances.return_value = dummy_task_instances
    mock_api.get_log.return_value = dummy_logs
    mock_get_task_instance_api.return_value = mock_api

    result = generate_failed_dag_run_logs("dag1", "run1")
    assert "--- Logs for task: task1 (try: 1) ---" in result
    assert "event1" in result
    assert "event2" in result


@patch("src.services.airflow_logs.get_task_instance_api")
def test_generate_failed_dag_run_logs_not_found(mock_get_task_instance_api: MagicMock):
    mock_api = MagicMock()
    mock_api.get_task_instances.side_effect = Exception("Not found")
    mock_get_task_instance_api.return_value = mock_api
    with pytest.raises(HTTPException):
        generate_failed_dag_run_logs("dag1", "run1")
