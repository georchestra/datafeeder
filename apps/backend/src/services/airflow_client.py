from functools import lru_cache

import jwt
import requests
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DagRunApi
from airflow_client.client.api.event_log_api import EventLogApi
from airflow_client.client.api.task_instance_api import TaskInstanceApi
from airflow_client.client.api_client import ApiClient
from airflow_client.client.configuration import Configuration
from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_patch_body import DAGRunPatchBody
from airflow_client.client.models.dag_run_patch_states import DAGRunPatchStates
from pydantic import BaseModel

from ..core.config import get_settings

__all__ = [
    "get_airflow_api_client",
    "get_dag_run_api",
    "get_dag_api",
    "get_event_log_api",
    "get_task_instance_api",
    "cancel_ingestion_dag",
    "delete_dag",
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


def cancel_ingestion_dag(integrity_link_id: str) -> None:
    """
    Cancel all running or queued Airflow runs associated with the given integrity link.

    Cancels the scheduled ingestion DAG runs (ingestion_{id}) and any process_dag runs
    triggered by them (identified by dag_run_id prefix).
    """
    dag_id = f"ingestion_{integrity_link_id}"

    # Cancel dag runs (running or queued) for the ingestion DAG:
    dag_run_api = get_dag_run_api()
    patch_body = DAGRunPatchBody(state=DAGRunPatchStates.FAILED)
    for dag_run in dag_run_api.get_dag_runs(dag_id=dag_id).dag_runs:
        if dag_run.state in ("running", "queued"):
            try:
                dag_run_api.patch_dag_run(
                    dag_id=dag_id, dag_run_id=dag_run.dag_run_id, dag_run_patch_body=patch_body
                )
            except NotFoundException:
                pass

    # Cancel triggered process_dag runs that were triggered by the ingestion DAG runs:
    dag_run_api = get_dag_run_api()
    patch_body = DAGRunPatchBody(state=DAGRunPatchStates.FAILED)
    for dag_run in dag_run_api.get_dag_runs(dag_id="process_dag").dag_runs:
        if dag_run.state in ("running", "queued") and dag_run.dag_run_id.startswith(
            f"{integrity_link_id}_"
        ):
            try:
                dag_run_api.patch_dag_run(
                    dag_id="process_dag",
                    dag_run_id=dag_run.dag_run_id,
                    dag_run_patch_body=patch_body,
                )
            except NotFoundException:
                pass


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
