from functools import lru_cache

from airflow_client.client.api.dag_run_api import DagRunApi
from airflow_client.client.api_client import ApiClient
from airflow_client.client.configuration import Configuration

from ..config import get_settings


@lru_cache
def get_airflow_configuration() -> Configuration:
    settings = get_settings()
    config = Configuration(host=settings.airflow_host)
    config.username = settings.airflow_username
    config.password = settings.airflow_password
    return config


@lru_cache
def get_airflow_api_client() -> ApiClient:
    return ApiClient(get_airflow_configuration())


@lru_cache
def get_dag_run_api() -> DagRunApi:
    return DagRunApi(get_airflow_api_client())
