import secrets
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from jproperties import Properties  # type: ignore[import-untyped]
from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

__all__ = ["Settings", "get_settings"]


def _is_placeholder(value: str) -> bool:
    """Check if a property value is a placeholder like ${VARIABLE}."""
    return value.startswith("${") and value.endswith("}")


def _extract_property(properties: Properties, key: str) -> str | None:
    """Extract a property value if it exists and is not a placeholder."""
    if not properties.get(key):  # type: ignore[no-untyped-call]
        return None
    value: str = properties.get(key).data  # type: ignore[no-untyped-call, union-attr]
    return None if _is_placeholder(value) else value  # type: ignore[return-value]


def _load_georchestra_properties() -> dict[str, Any]:
    """Load geOrchestra default.properties file for database configuration."""
    # Path from apps/backend/src/core/config.py -> docker/datadir/default.properties
    props_file = (
        Path(__file__).parent.parent.parent.parent.parent
        / "docker"
        / "datadir"
        / "default.properties"
    )

    if not props_file.exists():
        return {}

    props = Properties()
    with open(props_file, "rb") as f:
        props.load(f)  # type: ignore[no-untyped-call]

    # Extract postgres configuration from georchestra properties
    result: dict[str, Any] = {}

    # Project configuration
    if project_name := _extract_property(props, "projectName"):
        result["PROJECT_NAME"] = project_name
    if frontend_host := _extract_property(props, "frontendHost"):
        result["FRONTEND_HOST"] = frontend_host

    # PostgreSQL configuration
    if pgsql_host := _extract_property(props, "pgsqlHost"):
        result["POSTGRES_SERVER"] = "localhost" if pgsql_host == "database" else pgsql_host
    if pgsql_port := _extract_property(props, "pgsqlPort"):
        result["POSTGRES_PORT"] = int(pgsql_port)
    if pgsql_user := _extract_property(props, "pgsqlUser"):
        result["POSTGRES_USER"] = pgsql_user
    if pgsql_password := _extract_property(props, "pgsqlPassword"):
        result["POSTGRES_PASSWORD"] = pgsql_password
    if pgsql_database := _extract_property(props, "pgsqlDatabase"):
        result["POSTGRES_DB"] = pgsql_database

    # GeoServer configuration
    if geoserver_url := _extract_property(props, "geoserverUrl"):
        result["GEOSERVER_URL"] = geoserver_url
    if geoserver_user := _extract_property(props, "geoserverUser"):
        result["GEOSERVER_USER"] = geoserver_user
    if geoserver_password := _extract_property(props, "geoserverPassword"):
        result["GEOSERVER_PASSWORD"] = geoserver_password

    return result


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Load .env from workspace root, with defaults from georchestra properties
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Project Information
    PROJECT_NAME: str = "DataKern"

    # API Configuration
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    SENTRY_DSN: HttpUrl | None = None

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 60 minutes * 24 hours * 8 days = 8 days

    # CORS Configuration
    FRONTEND_HOST: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    # PostgreSQL Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "georchestra"
    POSTGRES_PASSWORD: str = "georchestra"
    POSTGRES_DB: str = "georchestra"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # GeoServer
    GEOSERVER_URL: str = "http://localhost:8080/geoserver"
    GEOSERVER_USER: str = "testadmin"
    GEOSERVER_PASSWORD: str = "testadmin"

    # Email Configuration
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            object.__setattr__(self, "EMAILS_FROM_NAME", self.PROJECT_NAME)
        return self

    # Test Users
    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

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
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret("FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD)
        return self


# Use lru_cache to ensure settings are only loaded once
# FastAP's doc about it :
# https://fastapi.tiangolo.com/advanced/settings/#creating-the-settings-only-once-with-lru-cache
@lru_cache
def get_settings():
    return Settings(**_load_georchestra_properties())  # type: ignore[arg-type]
