from functools import lru_cache

from airflow_client.client.api.dag_run_api import DagRunApi
from airflow_client.client.api_client import ApiClient
from airflow_client.client.configuration import Configuration

from ..config import get_settings

CONFIGURATION = Configuration(
    host=get_settings().airflow_host,
    username=get_settings().airflow_username,
    password=get_settings().airflow_password,
)


@lru_cache
def get_airflow_api_client() -> ApiClient:
    return ApiClient(CONFIGURATION)


@lru_cache
def get_dag_run_api() -> DagRunApi:
    return DagRunApi(get_airflow_api_client())
