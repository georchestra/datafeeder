"""Tests for schema helpers in core config."""

from unittest.mock import patch

import pytest
from pydantic import PostgresDsn, ValidationError

from src.core.config import (
    CopySourceDatabase,
    DirectAccessSourceDatabase,
    Settings,
    is_shared_schema,
)
from src.services.georchestra import GeorchestraContext


class TestIsSharedSchema:
    def test_staging_schema_is_shared(self) -> None:
        assert is_shared_schema("staging")

    def test_default_data_schema_is_shared(self) -> None:
        assert is_shared_schema("data")

    def test_org_schema_is_not_shared(self) -> None:
        assert not is_shared_schema("myorg")

    def test_follows_configured_staging_schema(self) -> None:
        """The guard tracks get_staging_schema, not a hardcoded literal."""
        with patch("src.core.config.get_staging_schema", return_value="staging_v2"):
            assert is_shared_schema("staging_v2")
            assert not is_shared_schema("staging")


class TestSourceDatabases:
    def test_parsed_from_json_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"SOURCE_DB_1": {"type": "copy", "connection_string": "postgresql://u:p@h:5432/db"},'
            ' "PATRIMOINE": {"type": "direct_access", "connection_string":'
            ' "postgresql://u:p@h:5435/patrimoine", "jndi_reference": "jdbc/patrimoine",'
            ' "roles": ["EDITOR"]}}',
        )
        databases = Settings(_env_file=None).SOURCE_DATABASES  # type: ignore[call-arg]
        assert databases == {
            "SOURCE_DB_1": CopySourceDatabase(
                type="copy", connection_string=PostgresDsn("postgresql://u:p@h:5432/db")
            ),
            "PATRIMOINE": DirectAccessSourceDatabase(
                type="direct_access",
                connection_string=PostgresDsn("postgresql://u:p@h:5435/patrimoine"),
                jndi_reference="jdbc/patrimoine",
                roles=["EDITOR"],
            ),
        }

    @pytest.mark.parametrize(
        "entry",
        ['"postgresql://u:p@h:5432/db"', '{"connection_string": "postgresql://u:p@h/db"}'],
        ids=["bare_uri", "missing_type"],
    )
    def test_type_is_required(self, monkeypatch: pytest.MonkeyPatch, entry: str) -> None:
        monkeypatch.setenv("SOURCE_DATABASES", f'{{"SOURCE_DB_1": {entry}}}')
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_unknown_type_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"SOURCE_DB_1": {"type": "coppy", "connection_string": "postgresql://u:p@h/db"}}',
        )
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_direct_access_roles_default_to_empty(self) -> None:
        database = DirectAccessSourceDatabase(
            type="direct_access",
            connection_string=PostgresDsn("postgresql://u:p@h/db"),
            jndi_reference="jdbc/patrimoine",
        )
        assert database.roles == []

    @pytest.mark.parametrize(
        ("roles", "user_roles", "available"),
        [
            ([], set[str](), True),
            (["EDITOR"], set[str](), False),
            (["EDITOR"], {"OTHER"}, False),
            (["editor", "ADMIN"], {"EDITOR"}, True),
            (["ROLE_EDITOR"], {"EDITOR"}, True),
            (["EDITOR"], {"ADMINISTRATOR"}, True),
        ],
    )
    def test_is_available_to(self, roles: list[str], user_roles: set[str], available: bool) -> None:
        database = CopySourceDatabase(
            type="copy", connection_string=PostgresDsn("postgresql://u:p@h/db"), roles=roles
        )
        geo_ctx = GeorchestraContext(
            username="someone",
            roles=user_roles,
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert database.is_available_to(geo_ctx) is available

    @pytest.mark.parametrize("role", ["", " ", "ROLE_"])
    def test_empty_role_is_rejected(self, role: str) -> None:
        with pytest.raises(ValidationError):
            CopySourceDatabase(
                type="copy", connection_string=PostgresDsn("postgresql://u:p@h/db"), roles=[role]
            )

    def test_direct_access_requires_jndi_reference(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"PATRIMOINE": {"type": "direct_access", "connection_string": "postgresql://u:p@h/db"}}',
        )
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_direct_access_requires_connection_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"PATRIMOINE": {"type": "direct_access", "jndi_reference": "jdbc/patrimoine"}}',
        )
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_schema_parsed_from_json_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"SOURCE_DB_1": {"type": "copy", "connection_string": "postgresql://u:p@h/db",'
            ' "schema": "geo"}}',
        )
        databases = Settings(_env_file=None).SOURCE_DATABASES  # type: ignore[call-arg]
        assert databases["SOURCE_DB_1"].schema_name == "geo"

    @pytest.mark.parametrize("schema", ["geo; DROP TABLE", ""])
    def test_invalid_schema_is_rejected(self, monkeypatch: pytest.MonkeyPatch, schema: str) -> None:
        monkeypatch.setenv(
            "SOURCE_DATABASES",
            '{"SOURCE_DB_1": {"type": "copy", "connection_string": "postgresql://u:p@h/db",'
            f' "schema": "{schema}"}}}}',
        )
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]
