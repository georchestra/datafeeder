import secrets
import warnings
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


def load_georchestra_properties() -> dict[str, Any]:
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

    # Helper to check if a value is a placeholder like ${VARIABLE}
    def is_placeholder(value: str) -> bool:
        return value.startswith("${") and value.endswith("}")

    # Extract postgres configuration from georchestra properties
    result: dict[str, Any] = {}

    # Extract project name
    if props.get("projectName"):  # type: ignore[no-untyped-call]
        value = props.get("projectName").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["PROJECT_NAME"] = value

    # Extract frontend host
    if props.get("frontendHost"):  # type: ignore[no-untyped-call]
        value = props.get("frontendHost").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["FRONTEND_HOST"] = value

    if props.get("pgsqlHost"):  # type: ignore[no-untyped-call]
        # Convert 'database' hostname to 'localhost' for local development
        host = props.get("pgsqlHost").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(host):
            result["POSTGRES_SERVER"] = "localhost" if host == "database" else host
    if props.get("pgsqlPort"):  # type: ignore[no-untyped-call]
        value = props.get("pgsqlPort").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["POSTGRES_PORT"] = int(value)  # type: ignore[arg-type]
    if props.get("pgsqlUser"):  # type: ignore[no-untyped-call]
        value = props.get("pgsqlUser").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["POSTGRES_USER"] = value
    if props.get("pgsqlPassword"):  # type: ignore[no-untyped-call]
        value = props.get("pgsqlPassword").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["POSTGRES_PASSWORD"] = value
    if props.get("pgsqlDatabase"):  # type: ignore[no-untyped-call]
        value = props.get("pgsqlDatabase").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["POSTGRES_DB"] = value

    # Extract GeoServer configuration
    if props.get("geoserverUrl"):  # type: ignore[no-untyped-call]
        value = props.get("geoserverUrl").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["GEOSERVER_URL"] = value
    if props.get("geoserverUser"):  # type: ignore[no-untyped-call]
        value = props.get("geoserverUser").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["GEOSERVER_USER"] = value
    if props.get("geoserverPassword"):  # type: ignore[no-untyped-call]
        value = props.get("geoserverPassword").data  # type: ignore[no-untyped-call, union-attr]
        if not is_placeholder(value):
            result["GEOSERVER_PASSWORD"] = value

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
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str = "DataKern"
    SENTRY_DSN: HttpUrl | None = None

    # GeoServer settings
    GEOSERVER_URL: str = "http://localhost:8080/geoserver"
    GEOSERVER_USER: str = "testadmin"
    GEOSERVER_PASSWORD: str = "testadmin"

    # Database settings with defaults from georchestra properties
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

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            object.__setattr__(self, "EMAILS_FROM_NAME", self.PROJECT_NAME)
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changethis"

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


# Load georchestra properties and merge with settings
_georchestra_props = load_georchestra_properties()

# Create settings instance with georchestra defaults
settings = Settings(**_georchestra_props)  # type: ignore
