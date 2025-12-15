"""Ingestion task group."""

from typing import Any, Literal

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
)
from utils import get_sqlalchemy_engine, get_staging_schema


def ingestion_group(
    target_table_name: str, group_id: Literal["initial_ingestion", "refresh_ingestion"]
) -> None:
    """Factory function that creates an ingestion task group.

    Args:
        target_table_name: Table name to use for ingestion (Required)
        group_id: Identifier for the task group (initial_ingestion or refresh_ingestion)

    Returns:
        A task group for data ingestion
    """

    @task_group(group_id=group_id)  # type: ignore[misc]
    def _ingestion_impl() -> None:
        """Task group for ingestion tasks.

        Tasks can access runtime configuration via context.
        """

        @task.branch(task_id="select_ingestion_mode")  # type: ignore[misc]
        def do_branching(**context: dict[str, Any]) -> str | bool:
            params = context.get("params", {})
            source_type = params.get("source_type")

            match source_type:
                case "FILE":
                    return f"{group_id}.file_ingest_step"
                case "URL":
                    return f"{group_id}.url_ingest_step"
                case _:
                    raise AirflowException(f"Unsupported source_type: {source_type}")

        @task(task_id="file_ingest_step")
        def file_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            engine = get_sqlalchemy_engine()

            try:
                ingest_data_from_file_into_postgis(
                    params.get("source", ""),
                    params.get("staging_table_name", ""),
                    engine,
                    schema=get_staging_schema(),
                )
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from file: {e}")

        @task(task_id="url_ingest_step")
        def url_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            engine = get_sqlalchemy_engine()
            
            try:
                ingest_data_from_url_into_postgis(
                    params.get("source", ""),
                    params.get("staging_table_name", ""),
                    engine,
                    schema=get_staging_schema(),
                )
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from URL: {e}")

        do_branching() >> [file_ingest_step(), url_ingest_step()]

    return _ingestion_impl()
