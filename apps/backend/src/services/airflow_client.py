from functools import lru_cache

import jwt
import requests
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DagRunApi
from airflow_client.client.api.event_log_api import EventLogApi
from airflow_client.client.api.task_instance_api import TaskInstanceApi
from airflow_client.client.api_client import ApiClient
from airflow_client.client.configuration import Configuration
from pydantic import BaseModel

from ..core.config import get_settings

__all__ = [
    "get_airflow_api_client",
    "get_dag_run_api",
    "get_dag_api",
    "get_event_log_api",
    "get_task_instance_api",
]


class AirflowAccessTokenResponse(BaseModel):
    access_token: str


def _request_new_access_token() -> str:
    settings = get_settings()

    url: str = f"{settings.datakern_config.get('airflow_url', 'gateway_routes')}/auth/token"
    payload = {
        "username": settings.datakern_config.get("airflow_username"),
        "password": settings.datakern_config.get("airflow_password"),
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
    config = Configuration(host=settings.datakern_config.get("airflow_url", "gateway_routes"))
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
