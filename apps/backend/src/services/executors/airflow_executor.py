"""Airflow task executor implementation."""

import logging
from datetime import datetime
from typing import Any

from airflow_client.client.models.dag_run_state import DagRunState
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody

from src.core.task_executor import BaseTaskExecutor, TaskRunInfo, TaskStatus
from src.services.airflow_client import get_dag_run_api
from src.services.airflow_logs import generate_failed_dag_run_logs

logger = logging.getLogger(__name__)


def _convert_airflow_status(airflow_status: DagRunState) -> TaskStatus:
    """Convert Airflow DAG run state to unified TaskStatus."""
    mapping = {
        DagRunState.QUEUED: TaskStatus.QUEUED,
        DagRunState.RUNNING: TaskStatus.RUNNING,
        DagRunState.SUCCESS: TaskStatus.SUCCESS,
        DagRunState.FAILED: TaskStatus.FAILED,
    }
    mapped = mapping.get(airflow_status)
    if mapped is None:
        logger.warning("Couldn't map %s to TaskStatus, fallback to QUEUED", airflow_status.value)
        return TaskStatus.QUEUED
    return mapped


class AirflowTaskExecutor(BaseTaskExecutor):
    """Airflow implementation of task executor."""

    def trigger_staging_task(
        self,
        run_id: str,
        staging_table_name: str,
        source: str,
        source_type: str,
        success_callback_url: str | None = None,
        failure_callback_url: str | None = None,
        encrypted_credentials: str | None = None,
        source_layer: str | None = None,
        source_protocol: str | None = None,
    ) -> TaskRunInfo:
        """Trigger a staging task in Airflow."""
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="staging_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=run_id,
                conf={
                    "staging_table_name": staging_table_name,
                    "source": source,
                    "source_type": source_type,
                    "success_callback_url": success_callback_url or "",
                    "failure_callback_url": failure_callback_url or "",
                    "encrypted_credentials": encrypted_credentials,
                    "source_layer": source_layer,
                    "source_protocol": source_protocol,
                },
            ),
        )

        return TaskRunInfo(
            task_id=dag_run_response.dag_id,
            run_id=dag_run_response.dag_run_id,
            status=_convert_airflow_status(dag_run_response.state),
            execution_date=None,
        )

    def trigger_process_task(
        self,
        run_id: str,
        staging_table_name: str | None = None,
        final_table_name: str = "",
        integrity_transformation: dict[str, Any] | None = None,
        success_callback_url: str | None = None,
        failure_callback_url: str | None = None,
        last_retrieval_timestamp: datetime | None = None,
    ) -> TaskRunInfo:
        """Trigger a process task in Airflow."""
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="process_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=run_id,
                conf={
                    "staging_table_name": staging_table_name,
                    "final_table_name": final_table_name,
                    "integrity_transformation": integrity_transformation or {},
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                    "last_retrieval_timestamp": last_retrieval_timestamp,
                },
            ),
        )

        return TaskRunInfo(
            task_id=dag_run_response.dag_id,
            run_id=dag_run_response.dag_run_id,
            status=_convert_airflow_status(dag_run_response.state),
            execution_date=None,
        )

    def get_task_status(self, task_id: str, run_id: str) -> TaskRunInfo:
        """Get the status of a task in Airflow."""
        dag_run = get_dag_run_api().get_dag_run(dag_id=task_id, dag_run_id=run_id)

        return TaskRunInfo(
            task_id=dag_run.dag_id,
            run_id=dag_run.dag_run_id,
            status=_convert_airflow_status(dag_run.state),
            execution_date=None,
        )

    def get_task_logs(self, task_id: str, run_id: str) -> str:
        """Get logs for a task in Airflow."""
        return generate_failed_dag_run_logs(task_id, run_id)

    def get_task_note(self, task_id: str, run_id: str) -> str | None:
        """Get the note attached to a DAG run in Airflow."""
        dag_run = get_dag_run_api().get_dag_run(dag_id=task_id, dag_run_id=run_id)
        return dag_run.note
