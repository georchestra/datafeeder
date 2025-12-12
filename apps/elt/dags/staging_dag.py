from datetime import datetime
from typing import Any

import requests
from airflow.decorators import dag
from airflow.models import Param
from task_groups.ingestion import ingestion_group


def _dag_success_callback(context: dict[str, Any]) -> None:
    params = context.get("params", {})

    if params.get("success_backend_route_callback"):
        requests.post(params.get("success_backend_route_callback"))


def _dag_failure_callback(context: dict[str, Any]) -> None:
    params = context.get("params", {})

    if params.get("failure_backend_route_callback"):
        requests.post(params.get("failure_backend_route_callback"))


@dag(
    dag_id="staging_dag",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    params={  # type: ignore[arg-type]
        "source": Param(
            default="/tmp/files/myfile.gpkg",
            type="string",
            description="Source path or URL",
            minLength=1,
        ),
        "source_type": Param(
            default="FILE",
            type="string",
            description="FTP, URL, OGC WFS, FILE",
            enum=["FTP", "URL", "OGC_WFS", "FILE"],
        ),
        "success_callback_url": Param(
            default="", type=["null", "string"], description="URL to call on success", minLength=1
        ),
        "failure_callback_url": Param(
            default="", type=["null", "string"], description="URL to call on failure", minLength=1
        ),
    },
    on_success_callback=_dag_success_callback,
    on_failure_callback=_dag_failure_callback,
)
def staging_dag(**context: dict[str, Any]) -> None:
    # Add ingestion task group
    ingestion_group()


staging_dag_instance = staging_dag()
