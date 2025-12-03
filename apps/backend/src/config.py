from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    airflow_host: str = "http://airflow-apiserver:8081/airflow"
    airflow_username: str = "admin"
    airflow_password: str = "admin"


# Use lru_cache to ensure settings are only loaded once
# FastAP's doc about it :
# https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache
@lru_cache
def get_settings():
    return Settings()
