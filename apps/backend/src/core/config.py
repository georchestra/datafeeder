import re
import secrets
from configparser import ConfigParser
from functools import lru_cache
from itertools import chain
from os import getenv
from typing import Any

from pydantic import (
    PostgresDsn,
)

from .georchestraconfig import GeorchestraConfig

__all__ = ["DataKernSettings", "get_settings"]


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class DataKernSettings:
    def __init__(self):
        self.georchestra_config: GeorchestraConfig = GeorchestraConfig()
        self.datakern_config: dict[str, Any] = dict()
        # Project Information
        self.datakern_config["project_name"] = "DataKern"

        # API Configuration
        self.datakern_config["api_v1_str"] = "/api/v1"
        self.datakern_config["environment"] = "local"  # Can be "local", "staging", "production"
        self.datakern_config["sentry_dsn"] = None

        # Security
        self.secret_key: str = secrets.token_urlsafe(32)

        # Airflow configuration
        self.datakern_config["airflow_username"] = "airflow"
        self.datakern_config["airflow_password"] = "airflow"
        # 60 minutes * 24 hours * 8 days = 8 days
        self.datakern_config["access_token_expire_minutes"] = 60 * 24 * 8

        self.datakern_config["backend_cors_origins"] = []

        self.datakern_config["email_reset_token_expire_hours"] = 48  # type: ignore[arg-type]

        self.read_datakern_config()

    def read_datakern_config(self):
        parser = ConfigParser()
        with open(f"{self.georchestra_config.datadirpath}/datakern/datakern.conf") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.datakern_config = parser["section"]  # type: ignore[arg-type]

    def all_cors_origins(self) -> list[str]:
        return [
            str(origin).rstrip("/")  # type: ignore[arg-type]
            for origin in self.datakern_config["backend_cors_origins"]  # type: ignore[arg-type]
        ] + [self.georchestra_config.get("datakern.target", "gateway_routes")]

    def sqlalchemy_database_uri(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.georchestra_config.get("pgsqluser", "default"),
            password=self.georchestra_config.get("pgsqlpassword", "default"),
            host='127.0.0.1',
            # host=self.georchestra_config.get("pgsqlhost", "default"),
            port=int(self.georchestra_config.get("pgsqlport", "default")),
            path=self.georchestra_config.get("pgsqldatabase", "default"),
        )

    def emails_enabled(self) -> bool:
        return bool(
            self.georchestra_config.get("smtphost", "default")
            and self.georchestra_config.get("administratoremail", "default")
        )

    def get(self, key: str) -> str:
        value: str = self.datakern_config[key]
        if value:
            # this is to catch ${ENV_VAR}
            search_env = re.match("^\\${(.*)}$", value)  # type: ignore[arg-type]
            # this is for url using env var http://${ENV_VAR}/geonetwork/..etc?params
            search_env2 = re.match("(.*)\\${(.*)}(.*)", value)  # type: ignore[arg-type]
            search_env3 = re.match("(.*)\\${(.*):.*}(.*)", value)  # type: ignore[arg-type]

            if search_env:
                if getenv(search_env.group(1)):
                    value = getenv(search_env.group(1))  # type: ignore[arg-type]
            elif search_env3:  # type: ignore[arg-type]
                if getenv(search_env3.group(2)):
                    value = (
                        f"{search_env3.group(1)}"
                        + f"{getenv(search_env3.group(2))}"
                        + f"{search_env3.group(3)}"
                    )
            elif search_env2:
                if getenv(search_env2.group(2)):
                    value = (
                        f"{search_env2.group(1)}"
                        + f"{getenv(search_env2.group(2))}"
                        + f"{search_env2.group(3)}"
                    )
        return value

    def tostr(self) -> str:
        str_to_return: str = "\r\n<br>Datakern config: \r\n<br>"

        for key2 in self.datakern_config:
            str_to_return += "\t&emsp;" + key2 + " : "
            if self.datakern_config[key2] == self.get(key2):  # type: ignore[arg-type]
                str_to_return += " \t&emsp;" + f"{self.datakern_config[key2]}" + "\r\n<br> "
            else:
                str_to_return += (
                    " \t&emsp;"
                    + f"{self.datakern_config[key2]}"
                    + " = "
                    + f"{self.get(key2)}"  # type: ignore[arg-type]
                    + "\r\n<br> "
                )
        return str_to_return


# Use lru_cache to ensure settings are only loaded once
# FastAP's doc about it :
# https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache
@lru_cache
def get_settings():
    return DataKernSettings()  # type: ignore[arg-type]
