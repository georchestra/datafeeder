"""Tests for the source databases listing endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import PostgresDsn

from src.api.routes.source_databases import SourceDatabaseSummary, list_source_databases
from src.core.config import CopySourceDatabase, DirectAccessSourceDatabase
from src.services.georchestra import GeorchestraContext


def _ctx(admin: bool = True) -> GeorchestraContext:
    return GeorchestraContext(
        username="admin" if admin else "someone",
        roles={"ADMINISTRATOR"} if admin else {"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="MEL",
    )


@patch("src.api.routes.source_databases.get_settings")
def test_lists_key_type_and_label(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value.SOURCE_DATABASES = {
        "SOURCE_DB_1": CopySourceDatabase(
            type="copy", connection_string=PostgresDsn("postgresql://u:p@h:5432/db")
        ),
        "PATRIMOINE": DirectAccessSourceDatabase(
            type="direct_access",
            connection_string=PostgresDsn("postgresql://u:p@h:5435/patrimoine"),
            jndi_reference="jdbc/patrimoine",
            label="Patrimoine",
        ),
    }

    assert list_source_databases(_ctx()) == [
        SourceDatabaseSummary(key="SOURCE_DB_1", type="copy", label=None),
        SourceDatabaseSummary(key="PATRIMOINE", type="direct_access", label="Patrimoine"),
    ]


@patch("src.api.routes.source_databases.get_settings")
def test_empty_when_none_declared(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value.SOURCE_DATABASES = {}

    assert list_source_databases(_ctx()) == []


@patch("src.api.routes.source_databases.get_settings")
def test_requires_administrator(mock_get_settings: MagicMock) -> None:
    with pytest.raises(HTTPException) as exc_info:
        list_source_databases(_ctx(admin=False))

    assert exc_info.value.status_code == 403
    mock_get_settings.assert_not_called()
