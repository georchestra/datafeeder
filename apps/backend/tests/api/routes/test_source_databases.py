"""Tests for the source databases listing endpoint."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import PostgresDsn
from sqlalchemy.exc import OperationalError

from src.api.routes.source_databases import (
    SourceDatabaseSummary,
    SourceSchema,
    list_source_database_tables,
    list_source_databases,
)
from src.core.config import CopySourceDatabase, DirectAccessSourceDatabase, SourceDatabase
from src.services.georchestra import GeorchestraContext


def _ctx(*roles: str, username: str = "someone") -> GeorchestraContext:
    return GeorchestraContext(
        username=username,
        roles=set(roles),
        email="",
        firstname="",
        lastname="",
        organization="MEL",
    )


_DSN = PostgresDsn("postgresql://u:p@h:5432/db")


def _copy(*roles: str, schema: str | None = None) -> CopySourceDatabase:
    return CopySourceDatabase(type="copy", connection_string=_DSN, roles=list(roles), schema=schema)


@pytest.fixture
def source_databases() -> Iterator[dict[str, SourceDatabase]]:
    """SOURCE_DATABASES as the routes see it, empty until a test declares entries."""
    databases: dict[str, SourceDatabase] = {}
    with patch("src.api.routes.source_databases.get_settings") as mock_get_settings:
        mock_get_settings.return_value.SOURCE_DATABASES = databases
        yield databases


@patch("src.api.routes.source_databases.get_settings")
def test_lists_key_type_and_label(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value.SOURCE_DATABASES = {
        "SOURCE_DB_1": CopySourceDatabase(
            type="copy",
            connection_string=PostgresDsn("postgresql://u:p@h:5432/db"),
            schema="geo",
        ),
        "PATRIMOINE": DirectAccessSourceDatabase(
            type="direct_access",
            connection_string=PostgresDsn("postgresql://u:p@h:5435/patrimoine"),
            jndi_reference="jdbc/patrimoine",
            label="Patrimoine",
        ),
    }

    assert list_source_databases(_ctx()) == [
        SourceDatabaseSummary(key="SOURCE_DB_1", type="copy", label=None, schema_name="geo"),
        SourceDatabaseSummary(key="PATRIMOINE", type="direct_access", label="Patrimoine"),
    ]


@patch("src.api.routes.source_databases.get_settings")
def test_empty_when_none_declared(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value.SOURCE_DATABASES = {}

    assert list_source_databases(_ctx()) == []


@pytest.mark.parametrize(
    ("user_roles", "expected"),
    [
        (set[str](), ["OPEN"]),
        ({"EDITOR"}, ["OPEN", "RESTRICTED"]),
        ({"EDITOR", "OTHER"}, ["OPEN", "RESTRICTED"]),
        ({"OTHER"}, ["OPEN"]),
        ({"ADMINISTRATOR"}, ["OPEN", "RESTRICTED"]),
    ],
)
def test_lists_only_databases_available_to_user_roles(
    source_databases: dict[str, SourceDatabase], user_roles: set[str], expected: list[str]
) -> None:
    source_databases["OPEN"] = _copy()
    source_databases["RESTRICTED"] = _copy("editor")

    assert [db.key for db in list_source_databases(_ctx(*user_roles))] == expected


@patch("src.api.routes.source_databases.list_tables_by_schema")
@patch("src.api.routes.source_databases.get_source_engine")
def test_tables_grouped_by_schema(
    mock_get_source_engine: MagicMock,
    mock_list_tables_by_schema: MagicMock,
    source_databases: dict[str, SourceDatabase],
) -> None:
    source_databases["SOURCE_DB_2"] = _copy()
    mock_list_tables_by_schema.return_value = {
        "geo": ["parcelles", "stations_mesure"],
        "referentiel": ["communes"],
    }

    assert list_source_database_tables("SOURCE_DB_2", _ctx()) == [
        SourceSchema(schema_name="geo", tables=["parcelles", "stations_mesure"]),
        SourceSchema(schema_name="referentiel", tables=["communes"]),
    ]
    mock_get_source_engine.assert_called_once_with("SOURCE_DB_2")
    mock_list_tables_by_schema.assert_called_once_with(mock_get_source_engine.return_value)


@patch("src.api.routes.source_databases.list_tables_by_schema")
@patch("src.api.routes.source_databases.get_source_engine")
def test_tables_restricted_to_configured_schema(
    _mock_get_source_engine: MagicMock,
    mock_list_tables_by_schema: MagicMock,
    source_databases: dict[str, SourceDatabase],
) -> None:
    source_databases["SOURCE_DB_2"] = _copy(schema="geo")
    mock_list_tables_by_schema.return_value = {
        "geo": ["parcelles"],
        "referentiel": ["communes"],
    }

    assert list_source_database_tables("SOURCE_DB_2", _ctx()) == [
        SourceSchema(schema_name="geo", tables=["parcelles"]),
    ]


@patch("src.api.routes.source_databases.logger")
@patch("src.api.routes.source_databases.list_tables_by_schema")
@patch("src.api.routes.source_databases.get_source_engine")
def test_tables_warn_when_configured_schema_has_no_table(
    _mock_get_source_engine: MagicMock,
    mock_list_tables_by_schema: MagicMock,
    mock_logger: MagicMock,
    source_databases: dict[str, SourceDatabase],
) -> None:
    source_databases["SOURCE_DB_2"] = _copy(schema="geo")
    mock_list_tables_by_schema.return_value = {"referentiel": ["communes"]}

    assert list_source_database_tables("SOURCE_DB_2", _ctx()) == []
    mock_logger.warning.assert_called_once()


@pytest.mark.parametrize(
    ("key", "user_roles"),
    [("NOPE", set[str]()), ("SOURCE_DB_2", {"OTHER"}), ("SOURCE_DB_2", set[str]())],
    ids=["unknown", "no_matching_role", "no_role"],
)
@patch("src.api.routes.source_databases.get_source_engine")
def test_tables_not_found(
    mock_get_source_engine: MagicMock,
    source_databases: dict[str, SourceDatabase],
    key: str,
    user_roles: set[str],
) -> None:
    source_databases["SOURCE_DB_2"] = _copy("EDITOR")

    with pytest.raises(HTTPException) as exc_info:
        list_source_database_tables(key, _ctx(*user_roles))

    assert exc_info.value.status_code == 404
    mock_get_source_engine.assert_not_called()


def test_anonymous_user_is_rejected(source_databases: dict[str, SourceDatabase]) -> None:
    source_databases["OPEN"] = _copy()

    for call in (
        lambda: list_source_databases(_ctx(username="")),
        lambda: list_source_database_tables("OPEN", _ctx(username="")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            call()
        assert exc_info.value.status_code == 401


@patch("src.api.routes.source_databases.list_tables_by_schema")
@patch("src.api.routes.source_databases.get_source_engine")
def test_tables_unreachable_database(
    _mock_get_source_engine: MagicMock,
    mock_list_tables_by_schema: MagicMock,
    source_databases: dict[str, SourceDatabase],
) -> None:
    source_databases["SOURCE_DB_2"] = _copy()
    mock_list_tables_by_schema.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )

    with pytest.raises(HTTPException) as exc_info:
        list_source_database_tables("SOURCE_DB_2", _ctx())

    assert exc_info.value.status_code == 503
