import logging
import os
import secrets
import warnings
from functools import lru_cache
from string import Template
from typing import Annotated, Any, Literal

from data_manipulation.logging import configure_logging
from pydantic import (
    AliasChoices,
    AnyUrl,
    BeforeValidator,
    Field,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from typing_extensions import Self

from src.core.constants import DEFAULT_DATA_SCHEMA
from src.core.logging import get_logger
from src.core.paths import get_default_datadir
from src.core.task_executor import TaskExecutorType
from src.plugins.PropertiesConfigSettingsSource import PropertiesConfigSettingsSource

logger = get_logger()
configure_logging(logger)

__all__ = ["Settings", "get_settings"]


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    datafeeder_config: str = os.getenv("DATAFEEDER_CONFIG", "")
    _default_datadir = get_default_datadir()

    if not os.path.exists(datafeeder_config) and not os.path.exists(
        f"{_default_datadir}/datafeeder-python/datafeeder.env"
    ):
        logger.warning("Configuration file not found!")
        logger.warning("looked for DATAFEEDER_CONFIG at: %s", os.getenv("DATAFEEDER_CONFIG", ""))
        logger.warning(
            "looked for datafeeder.env at: %s",
            f"{_default_datadir}/datafeeder-python/datafeeder.env",
        )
    else:
        if not os.path.exists(datafeeder_config) and os.path.exists(
            f"{_default_datadir}/datafeeder-python/datafeeder.env"
        ):
            datafeeder_config = f"{_default_datadir}/datafeeder-python/datafeeder.env"
        logger.info("Loading configuration from %s", datafeeder_config)

    model_config = SettingsConfigDict(
        # Load .env from workspace root, with defaults from georchestra properties
        env_file=datafeeder_config,
        env_ignore_empty=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            PropertiesConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            init_settings,
            file_secret_settings,
        )

    # Project Information
    PROJECT_NAME: str = "Datafeeder"
    BACKEND_INTERNAL_URL: str = "http://localhost:8000"
    DATA_PUBLIC_URL: str = "http://localhost:8080/geoserver"
    DATAHUB_PUBLIC_URL: str = "http://localhost:8080/datahub/dataset/{metadata_id}"
    METADATA_PUBLIC_URL: str = "http://localhost:8080/geonetwork"
    DATADIR_PATH: str = get_default_datadir()

    # API Configuration
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    TMP_UPLOAD_PATH: str = "/tmp/"

    # Projections Configuration, used by frontend
    PROJECTIONS: str = Field(
        default='[{"value": "EPSG:4326", "label": "WGS 84"}, {"value": "EPSG:3857", "label": "Web Mercator"}]',
        description="JSON string of available projections for the frontend",
    )

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ENCRYPTION_KEY: str = Field(
        default="",
        description="Encryption key for storing sensitive data (HTTP Basic Auth credentials)",
    )

    # Task Executor Configuration (AIRFLOW)
    TASK_EXECUTOR: TaskExecutorType = TaskExecutorType.AIRFLOW

    # Airflow configuration
    AIRFLOW_INTERNAL_URL: str = "http://localhost:8081/airflow"
    AIRFLOW_USERNAME: str = "airflow"
    AIRFLOW_PASSWORD: str = "airflow"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 60 minutes * 24 hours * 8 days = 8 days
    RECURRENCE_EXECUTION_HOUR: int = (
        4  # Hour of the day (0-23) when daily/weekly/monthly/yearly recurrences run
    )

    # CORS Configuration
    FRONTEND_HOST: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    # PostgreSQL Database
    POSTGRES_DATAFEEDER_HOST: str = Field(
        default="localhost", validation_alias=AliasChoices("pgsqlHost", "POSTGRES_HOST")
    )
    POSTGRES_DATAFEEDER_PORT: int = Field(
        default=5432, validation_alias=AliasChoices("pgsqlPort", "POSTGRES_PORT")
    )
    POSTGRES_DATAFEEDER_USER: str = Field(
        default="georchestra", validation_alias=AliasChoices("pgsqlUser", "POSTGRES_USER")
    )
    POSTGRES_DATAFEEDER_PASSWORD: str = Field(
        default="georchestra", validation_alias=(AliasChoices("pgsqlPassword", "POSTGRES_PASSWORD"))
    )
    POSTGRES_DATAFEEDER_DB: str = Field(
        default="georchestra", validation_alias=(AliasChoices("pgsqlDatabase", "POSTGRES_DB"))
    )

    POSTGRES_DATA_HOST: str | None = None
    POSTGRES_DATA_PORT: int | None = None
    POSTGRES_DATA_USER: str | None = None
    POSTGRES_DATA_PASSWORD: str | None = None
    POSTGRES_DATA_DB: str | None = None

    # Source databases for database import type (key → SQLAlchemy URI)
    SOURCE_DATABASES: dict[str, PostgresDsn] = Field(default_factory=dict)

    # When True, final tables are written to a schema named after the org short name instead of "data"
    USE_ORG_SCHEMA: bool = False

    # GeoServer
    GEOSERVER_INTERNAL_URL: str = "http://localhost:8080/geoserver"

    GEOSERVER_USER: str = "testadmin"

    GEOSERVER_PASSWORD: str = "testadmin"

    # Geonetwork
    GEONETWORK_INTERNAL_URL: str = "http://localhost:8080/geonetwork"

    GEONETWORK_USERNAME: str = "testadmin"

    GEONETWORK_PASSWORD: str = "testadmin"

    # This is odd, apparently any UUID works as XSRF token
    GEONETWORK_XSRF_TOKEN: str = "c9f33266-e242-4198-a18c-b01290dce5f1"

    GN_SYNC_MODE: Literal["ORG", "ROLE"] = "ORG"

    METADATA_DEFAULT_GROUP_NAME: str = "sample"

    # Console
    CONSOLE_INTERNAL_URL: str = "http://localhost:8085/console"

    # Metadata groups (for authorization UI)
    METADATA_GROUPS_LABEL_FILTER_REGEX: str = ""

    # Data groups (for GeoServer authorization UI)
    DATA_GROUPS_LABEL_FILTER_REGEX: str = ""

    ### Validators and computed fields

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def POSTGRES_DATAFEEDER_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_DATAFEEDER_USER,
            password=self.POSTGRES_DATAFEEDER_PASSWORD,
            host=self.POSTGRES_DATAFEEDER_HOST,
            port=self.POSTGRES_DATAFEEDER_PORT,
            path=self.POSTGRES_DATAFEEDER_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def POSTGRES_DATA_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_DATA_USER,
            password=self.POSTGRES_DATA_PASSWORD,
            host=self.POSTGRES_DATA_HOST,
            port=self.POSTGRES_DATA_PORT,
            path=self.POSTGRES_DATA_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def GEONETWORK_XML_RECORD_URL(self) -> str:
        return f"{self.METADATA_PUBLIC_URL}/srv/api/records/{{metadata_id}}/formatters/xml"

    @model_validator(mode="after")
    def _set_data_db_defaults(self) -> Self:
        """Set POSTGRES_DATA_* fields to POSTGRES_DATAFEEDER_* values if not provided."""
        if self.POSTGRES_DATA_HOST is None:
            object.__setattr__(self, "POSTGRES_DATA_HOST", self.POSTGRES_DATAFEEDER_HOST)
        if self.POSTGRES_DATA_PORT is None:
            object.__setattr__(self, "POSTGRES_DATA_PORT", self.POSTGRES_DATAFEEDER_PORT)
        if self.POSTGRES_DATA_USER is None:
            object.__setattr__(self, "POSTGRES_DATA_USER", self.POSTGRES_DATAFEEDER_USER)
        if self.POSTGRES_DATA_PASSWORD is None:
            object.__setattr__(self, "POSTGRES_DATA_PASSWORD", self.POSTGRES_DATAFEEDER_PASSWORD)
        if self.POSTGRES_DATA_DB is None:
            object.__setattr__(self, "POSTGRES_DATA_DB", self.POSTGRES_DATAFEEDER_DB)
        return self

    # Validators
    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret(
            "POSTGRES_DATAFEEDER_PASSWORD", self.POSTGRES_DATAFEEDER_PASSWORD
        )
        self._check_default_secret("ENCRYPTION_KEY", self.ENCRYPTION_KEY)
        return self

    @field_validator("*", mode="after")
    @classmethod
    def expand_env_vars(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                v = Template(v).substitute(os.environ)
            except KeyError as e:
                logging.error(f"Environment variable {e} not set for value: {v}")
        return v


# Use lru_cache to ensure settings are only loaded once
# FastAP's doc about it :
# https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache
@lru_cache
def get_settings():
    logger.debug(Settings().model_dump())
    return Settings()


def get_data_schema(org: str) -> str:
    """Return the target schema for final tables: org name if USE_ORG_SCHEMA, else 'data'."""
    return org.lower() if get_settings().USE_ORG_SCHEMA else DEFAULT_DATA_SCHEMA


def get_staging_schema() -> str:
    """Get the staging schema, defaulting to 'staging'."""
    return "staging"  # FIXME get it from config


def is_shared_schema(schema: str) -> bool:
    """True for schemas shared across datasets/orgs, which must never be
    dropped: the staging schema and the default data schema (used for final
    tables when USE_ORG_SCHEMA is disabled)."""
    return schema in (get_staging_schema(), DEFAULT_DATA_SCHEMA)
