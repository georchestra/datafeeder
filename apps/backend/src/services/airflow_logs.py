from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Union

from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.structured_log_message import StructuredLogMessage
from airflow_client.client.models.task_instance_collection_response import (
    TaskInstanceCollectionResponse,
)
from airflow_client.client.models.task_instance_response import TaskInstanceResponse
from airflow_client.client.models.task_instances_log_response import TaskInstancesLogResponse
from fastapi import HTTPException

from .airflow_client import get_task_instance_api


def generate_dag_run_logs(dag_id: str, dag_run_id: str) -> str:
    try:
        failed_task_instances: TaskInstanceCollectionResponse = (
            get_task_instance_api().get_task_instances(
                dag_id=dag_id, dag_run_id=dag_run_id, state=["failed"]
            )
        )
        all_logs: List[str] = []
        task_instances: List[TaskInstanceResponse] = failed_task_instances.task_instances

        def fetch_log(
            task_instance: TaskInstanceResponse,
        ) -> Tuple[TaskInstanceResponse, TaskInstancesLogResponse]:
            dag_run_logs: TaskInstancesLogResponse = get_task_instance_api().get_log(
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                task_id=task_instance.task_id,
                try_number=task_instance.try_number,
                full_content=True,
            )
            return (task_instance, dag_run_logs)

        with ThreadPoolExecutor() as executor:
            future_to_task = {executor.submit(fetch_log, ti): ti for ti in task_instances}
            for future in as_completed(future_to_task):
                task_instance, dag_run_logs = future.result()
                log_entries: Optional[Union[List[str], List[StructuredLogMessage]]] = (
                    dag_run_logs.content.actual_instance
                )
                if log_entries is None:
                    continue
                formatted_lines: List[str] = []
                for entry in log_entries:
                    if isinstance(entry, str):
                        formatted_lines.append(entry)
                    else:
                        # entry is StructuredLogMessage or similar
                        event = str(getattr(entry, "event", ""))
                        timestamp = getattr(entry, "timestamp", None)
                        if timestamp:
                            timestamp_str = timestamp.isoformat()
                            formatted_lines.append(f"[{timestamp_str}] {event}")
                        else:
                            formatted_lines.append(event)
                all_logs.append(
                    f"--- Logs for task: {task_instance.task_id} (try: {task_instance.try_number}) ---\n"
                    + "\n".join(formatted_lines)
                )
        return "\n\n".join(all_logs)
    except NotFoundException:
        raise HTTPException(
            status_code=404, detail=f"Logs not found for DAG run: {dag_id}/{dag_run_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
