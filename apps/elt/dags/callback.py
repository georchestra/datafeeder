import logging
import os
import shutil
from typing import Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

LOG_DIR = "/opt/airflow/logs"


def dag_success_callback_remove_files(
    dag_run: Any,
) -> None:
    if dag_run:
        run_id = dag_run.run_id
        log_path = os.path.join(LOG_DIR, f"dag_id={dag_run.dag_id}", f"run_id={run_id}")
        if os.path.isdir(log_path):
            shutil.rmtree(log_path)
            logger.info("Deleted log directory: %s", log_path)


def _dag_success_callback(context: dict[str, Any]) -> None:
    """Callback when staging_dag succeeds."""
    params = context.get("params", {})
    callback_url = params.get("success_callback_url")

    # delete local or remote log if exists
    dag_success_callback_remove_files(dag_run=context.get("dag_run"))

    if callback_url:
        call_callback(callback_url, "success")


def _dag_failure_callback(context: dict[str, Any]) -> None:
    """Callback when staging_dag fails."""
    params = context.get("params", {})
    callback_url = params.get("failure_callback_url")
    if callback_url:
        reason: str = context.get("reason", "")
        call_callback(f"{callback_url}&reason={quote(reason)}", "failure")


def call_callback(callback_url: str, callback_type: str) -> None:
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
        logger.error(
            f"{callback_type.capitalize()} callback failed | url={callback_url} | error={str(e)}"
        )
