import logging
from datetime import datetime
from typing import Any

import requests
from airflow.decorators import dag
from airflow.models import Param
from task_groups.ingestion import ingestion_group

logger = logging.getLogger(__name__)


def _call_callback(callback_url: str, callback_type: str) -> None:
    """Call a callback URL and log the request and response.

    Args:
        callback_url: The URL to call
        callback_type: Type of callback (e.g., "success", "failure") for logging
    """
    logger.info(f"Calling {callback_type} callback URL: {callback_url}")
    try:
        response = requests.post(callback_url, timeout=10)
        logger.info(
            f"{callback_type.capitalize()} callback responded | "
            f"status_code={response.status_code} | "
            f"response={response.text[:200]}"
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"{callback_type.capitalize()} callback failed | url={callback_url} | error={str(e)}")


def _dag_success_callback(context: dict[str, Any]) -> None:
    params = context.get("params", {})
    callback_url = params.get("success_callback_url")

    if callback_url:
        _call_callback(callback_url, "success")


def _dag_failure_callback(context: dict[str, Any]) -> None:
    params = context.get("params", {})
    callback_url = params.get("failure_callback_url")

    if callback_url:
        _call_callback(callback_url, "failure")


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
