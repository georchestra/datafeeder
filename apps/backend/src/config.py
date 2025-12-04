from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    airflow_host: str = "http://localhost:8081/airflow"
    airflow_username: str = "airflow"
    airflow_password: str = "airflow"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Use lru_cache to ensure settings are only loaded once
# FastAP's doc about it :
# https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache
@lru_cache
def get_settings():
    return Settings()
