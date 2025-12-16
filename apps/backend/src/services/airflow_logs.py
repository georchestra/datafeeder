from airflow_client.client.exceptions import NotFoundException
from fastapi import HTTPException

from .airflow_client import get_task_instance_api


def generate_dag_run_logs(dag_id: str, dag_run_id: str) -> str:
    try:
        failed_task_instances = get_task_instance_api().get_task_instances(
            dag_id=dag_id, dag_run_id=dag_run_id, state=["failed"]
        )
        all_logs: list[str] = []
        for task_instance in failed_task_instances.task_instances:
            dag_run_logs = get_task_instance_api().get_log(
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                task_id=task_instance.task_id,
                try_number=task_instance.try_number,
                full_content=True,
            )
            log_entries = dag_run_logs.content.actual_instance
            if log_entries is None:
                continue
            formatted_lines: list[str] = []
            for entry in log_entries:
                if isinstance(entry, str):
                    formatted_lines.append(entry)
                elif hasattr(entry, "event"):
                    event = str(entry.event) if entry.event else ""
                    if hasattr(entry, "timestamp") and entry.timestamp:
                        timestamp_str = entry.timestamp.isoformat()
                        formatted_lines.append(f"[{timestamp_str}] {event}")
                    else:
                        formatted_lines.append(event)
                else:
                    formatted_lines.append(str(entry))
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
