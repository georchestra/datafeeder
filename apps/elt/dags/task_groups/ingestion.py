"""Ingestion task group."""

from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
)
from utils import get_final_schema, get_sqlalchemy_engine


@task_group(group_id="ingestion")
def ingestion_group() -> None:
    """Task group for ingestion tasks.

    Tasks can access runtime configuration via context.
    """

    @task.branch(task_id="select_ingestion_mode")
    def do_branching(**context: dict[str, Any]) -> str | bool:
        params = context.get("params", {})

        # switch based on params source_type
        source_type = params.get("source_type", "")
        match source_type:
            case "FILE":
                return "ingestion.file_ingest_step"
            case "URL":
                return "ingestion.url_ingest_step"
            case _:
                raise AirflowException(f"Unsupported source_type: {source_type}")

    @task(task_id="file_ingest_step")
    def file_ingest_step(**context: dict[str, Any]) -> None:
        params = context.get("params", {})
        engine = get_sqlalchemy_engine()

        try:
            ingest_data_from_file_into_postgis(
                params.get("source", ""), "my_table", engine, schema=get_final_schema()
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
                "my_table",
                engine,
                schema=get_final_schema(),
            )
        except Exception as e:
            raise AirflowException(f"Failed to ingest data from URL: {e}")

    do_branching() >> [file_ingest_step(), url_ingest_step()]
