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

    def test_direct_access_roles_default_to_empty(self) -> None:
        database = DirectAccessSourceDatabase(
            type="direct_access",
            connection_string=PostgresDsn("postgresql://u:p@h/db"),
            jndi_reference="jdbc/patrimoine",
        )
        assert database.roles == []

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
