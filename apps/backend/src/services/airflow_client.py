from collections.abc import Callable
from functools import lru_cache

import jwt
import requests
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DagRunApi
from airflow_client.client.api.event_log_api import EventLogApi
from airflow_client.client.api.task_instance_api import TaskInstanceApi
from airflow_client.client.api_client import ApiClient
from airflow_client.client.configuration import Configuration
from airflow_client.client.exceptions import ConflictException, NotFoundException
from airflow_client.client.models.dag_run_patch_body import DAGRunPatchBody
from airflow_client.client.models.dag_run_patch_states import DAGRunPatchStates
from airflow_client.client.models.dag_run_response import DAGRunResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.run_ids import (
    is_manual_process_run,
    process_run_like,
    process_run_prefix,
    staging_run_like,
    staging_run_prefix,
)

logger = get_logger()

__all__ = [
    "get_airflow_api_client",
    "get_dag_run_api",
    "get_dag_api",
    "get_event_log_api",
    "get_task_instance_api",
    "cancel_dataset_runs",
    "cancel_scheduled_runs",
    "delete_dag",
    "purge_dataset_dag_runs",
    "remove_ingestion_dag",
]


class AirflowAccessTokenResponse(BaseModel):
    access_token: str


def _request_new_access_token() -> str:
    settings = get_settings()

    url = f"{settings.AIRFLOW_URL}/auth/token"
    payload = {
        "username": settings.AIRFLOW_USERNAME,
        "password": settings.AIRFLOW_PASSWORD,
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 201:
        raise RuntimeError(f"Failed to get access token: {response.status_code} {response.text}")

    response_success = AirflowAccessTokenResponse(**response.json())
    return response_success.access_token


def _is_jwt_expired(token: str) -> bool:
    try:
        jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
        return False
    except jwt.ExpiredSignatureError:
        return True
    # Any other errors
    except jwt.PyJWTError:
        raise RuntimeError("Invalid JWT token")


@lru_cache
def _get_cached_airflow_api_client() -> ApiClient:
    settings = get_settings()
    config = Configuration(host=settings.AIRFLOW_URL)
    config.access_token = _request_new_access_token()
    return ApiClient(configuration=config)


def _refresh_caches_if_token_expired() -> None:
    """
    Refresh the cached Airflow API client if its access token is expired.
    This function can be called to ensure the client is up-to-date.
    """
    client = _get_cached_airflow_api_client()

    # Check if airflow access token is expired
    token = getattr(getattr(client, "configuration", None), "access_token", None)
    if token is None or _is_jwt_expired(token):
        _get_cached_airflow_api_client.cache_clear()

        # Also clear dependent caches to ensure they use the refreshed client
        _get_cached_dag_run_api.cache_clear()
        _get_cached_dag_api.cache_clear()
        _get_cached_event_log_api.cache_clear()
        _get_cached_task_instance_api.cache_clear()


def get_airflow_api_client() -> ApiClient:
    _refresh_caches_if_token_expired()
    return _get_cached_airflow_api_client()


@lru_cache
def _get_cached_dag_run_api() -> DagRunApi:
    return DagRunApi(_get_cached_airflow_api_client())


def get_dag_run_api() -> DagRunApi:
    _refresh_caches_if_token_expired()
    return _get_cached_dag_run_api()


@lru_cache
def _get_cached_dag_api() -> DAGApi:
    return DAGApi(_get_cached_airflow_api_client())


def get_dag_api() -> DAGApi:
    _refresh_caches_if_token_expired()
    return _get_cached_dag_api()


@lru_cache
def _get_cached_event_log_api() -> EventLogApi:
    return EventLogApi(_get_cached_airflow_api_client())


def get_event_log_api() -> EventLogApi:
    _refresh_caches_if_token_expired()
    return _get_cached_event_log_api()


@lru_cache
def _get_cached_task_instance_api() -> TaskInstanceApi:
    return TaskInstanceApi(_get_cached_airflow_api_client())


def get_task_instance_api() -> TaskInstanceApi:
    _refresh_caches_if_token_expired()
    return _get_cached_task_instance_api()


def _for_each_dag_run(
    dag_id: str,
    action: Callable[[DAGRunResponse], bool],
    run_id_like: str | None = None,
    states: list[str] | None = None,
) -> None:
    """Apply action to every run of a DAG matching the server-side filters.

    Pages by re-querying (limit=100) until no matching run remains, so the
    action must be self-consuming: it must remove the run from the filtered
    result set (delete it, or patch it out of the states filter) and return
    whether it made progress — a page with no progress bails out to avoid
    looping. A missing DAG (404 on the query) is a no-op.
    """
    api = get_dag_run_api()
    while True:
        try:
            page = api.get_dag_runs(
                dag_id=dag_id, run_id_pattern=run_id_like, state=states, limit=100
            )
        except NotFoundException:
            return
        runs = page.dag_runs
        if not runs:
            return
        progressed = False
        for run in runs:
            progressed = action(run) or progressed
        if not progressed:
            return


def _force_fail_dag_runs(
    dag_id: str,
    dag_run_id_prefix: str | None = None,
    exclude: Callable[[str], bool] | None = None,
) -> None:
    dag_run_api = get_dag_run_api()
    patch_body = DAGRunPatchBody(state=DAGRunPatchStates.FAILED)

    def force_fail(dag_run: DAGRunResponse) -> bool:
        # Re-check the prefix: the LIKE pattern treats '_' as a wildcard
        if dag_run_id_prefix and not dag_run.dag_run_id.startswith(dag_run_id_prefix):
            return False
        if exclude and exclude(dag_run.dag_run_id):
            return False
        try:
            dag_run_api.patch_dag_run(
                dag_id=dag_id, dag_run_id=dag_run.dag_run_id, dag_run_patch_body=patch_body
            )
            return True
        except NotFoundException:
            return True  # already gone — progress nonetheless

    _for_each_dag_run(
        dag_id,
        force_fail,
        run_id_like=f"{dag_run_id_prefix}%" if dag_run_id_prefix else None,
        states=["running", "queued"],
    )


def cancel_dataset_runs(integrity_link_id: str) -> None:
    """
    Cancel ALL running or queued Airflow runs of a dataset: the scheduled
    ingestion DAG runs (ingestion_{id}) plus every process_dag and staging_dag
    run, scheduled or manual, matched by run-id prefix.

    Used by dataset deletion, where no run may keep writing to the tables.
    """
    _force_fail_dag_runs(f"ingestion_{integrity_link_id}")
    _force_fail_dag_runs("process_dag", dag_run_id_prefix=process_run_prefix(integrity_link_id))
    _force_fail_dag_runs("staging_dag", dag_run_id_prefix=staging_run_prefix(integrity_link_id))


def cancel_scheduled_runs(integrity_link_id: str) -> None:
    """
    Cancel only the schedule-driven runs of a dataset: the ingestion DAG runs
    (ingestion_{id}) and the process_dag runs they spawned. Manual process
    runs ('..._manual') and staging runs (always user-initiated) are spared.

    Used when the recurrence schedule is cleared, so an in-flight manual run
    is not collateral damage.
    """
    _force_fail_dag_runs(f"ingestion_{integrity_link_id}")
    _force_fail_dag_runs(
        "process_dag",
        dag_run_id_prefix=process_run_prefix(integrity_link_id),
        exclude=is_manual_process_run,
    )


def _delete_dag_runs(dag_id: str, run_id_like: str) -> None:
    """Delete all runs of a DAG whose run id matches a SQL LIKE pattern.

    Deleting a dag run cascades its task instances and XComs in the Airflow
    metadata DB. Pages by re-querying until no (deletable) run remains.
    Best-effort: per-run failures are logged and skipped.
    """
    api = get_dag_run_api()

    def delete(run: DAGRunResponse) -> bool:
        try:
            api.delete_dag_run(dag_id=dag_id, dag_run_id=run.dag_run_id)
            return True
        except NotFoundException:
            return True  # already gone — progress nonetheless
        except Exception as e:
            logger.warning(f"Failed to delete dag run {dag_id}/{run.dag_run_id}: {e}")
            return False

    _for_each_dag_run(dag_id, delete, run_id_like=run_id_like)


def purge_dataset_dag_runs(integrity_link_id: str) -> None:
    """
    Delete the Airflow run history (dag runs, task instances, XComs) of a dataset.

    Covers staging_dag runs (run ids '<id>' / '<id>_<ts>') and process_dag runs
    (run ids '<id>_<ts>[_manual]'). Run-id matching uses SQL LIKE patterns.
    """
    _delete_dag_runs("staging_dag", staging_run_like(integrity_link_id))
    _delete_dag_runs("process_dag", process_run_like(integrity_link_id))


def remove_ingestion_dag(integrity_link_id: str) -> None:
    """
    Cancel runs and delete the scheduled ingestion DAG for a dataset.

    Used when the recurrence schedule is cleared, so the dynamic
    ingestion_{id} DAG does not linger in Airflow as stale metadata once the
    DAG generator stops emitting it.

    Best-effort: logs and suppresses any Airflow error.
    """
    try:
        cancel_scheduled_runs(integrity_link_id)
        delete_dag(f"ingestion_{integrity_link_id}")
    except Exception as e:
        logger.warning(
            f"Failed to remove ingestion DAG for integrity link {integrity_link_id}: {e}",
            exc_info=True,
        )


def delete_dag(dag_id: str) -> None:
    """
    Delete a DAG from Airflow.

    Treats 404 (DAG not found) as success since the end goal is achieved.
    Raises an exception for other errors.

    Args:
        dag_id: The ID of the DAG to delete

    Raises:
        Exception: If the deletion fails for reasons other than 404
    """
    try:
        get_dag_api().delete_dag(dag_id)
    except NotFoundException:
        # DAG doesn't exist — treat as success since the goal is to ensure it's not there
        pass
    except ConflictException:
        # Active runs are blocking deletion — force them to failed, then retry
        _force_fail_dag_runs(dag_id)
        try:
            get_dag_api().delete_dag(dag_id)
        except NotFoundException:
            pass
