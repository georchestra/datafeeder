"""Tests for database source type in staging endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation.validators import validate_schema_name, validate_table_name
from fastapi import HTTPException

from src.api.routes.ingestion.staging import (
    _process_import_source,  # pyright: ignore[reportPrivateUsage]
    dag_success_callback,
)
from src.models.data_import import ImportType


class TestDbIdentifierValidation:
    """Test schema/table validation via data_manipulation.validators."""

    @pytest.mark.parametrize(
        "name",
        [
            "public",
            "my_data_table",
            "a",
            "schema123",
            "a" * 63,
        ],
    )
    def test_valid_schema_names_accepted(self, name: str) -> None:
        assert validate_schema_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "public",
            "my_data_table",
            "a",
            "schema123",
            "a" * 63,
        ],
    )
    def test_valid_table_names_accepted(self, name: str) -> None:
        assert validate_table_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "Public",
            "123table",
            "my-schema",
            "_leading_underscore",
            "a" * 64,
            "table; DROP TABLE",
            "schema.table",
        ],
    )
    def test_invalid_names_rejected(self, name: str) -> None:
        with pytest.raises(ValueError):
            validate_schema_name(name)

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_schema_name("")


class TestProcessImportSourceDatabase:
    """Test _process_import_source for ImportType.DATABASE."""

    @pytest.mark.asyncio
    async def test_valid_database_source(self) -> None:
        result = await _process_import_source(
            type=ImportType.DATABASE,
            db_schema="geo",
            db_table="rivers",
        )
        assert result.source == "db://geo/rivers"
        assert result.url == "db://geo/rivers"
        assert result.source_file_name is None
        assert result.source_file_type is None
        assert result.auth_enabled is False

    @pytest.mark.asyncio
    async def test_missing_schema_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema=None,
                db_table="rivers",
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_table_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="geo",
                db_table=None,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_schema_returns_422(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="Invalid",
                db_table="rivers",
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_table_returns_422(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="geo",
                db_table="123bad",
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_schema_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="",
                db_table="rivers",
            )
        assert exc_info.value.status_code == 400


class TestDagSuccessCallbackDeleteGuard:
    """Test that delete_temp_file is not called for database sources."""

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_not_called_for_database_source(self, mock_delete: MagicMock) -> None:
        """Verify delete_temp_file is skipped when source_import_type is DATABASE."""
        mock_integrity_link = MagicMock()
        mock_integrity_link.source_url = "db://geo/rivers"
        mock_integrity_link.source_import_type = ImportType.DATABASE
        mock_integrity_link.created_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_integrity_link

        dag_success_callback(session=mock_session, integrity_link_id=str(uuid4()))

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_called_for_file_source(self, mock_delete: MagicMock) -> None:
        """Verify delete_temp_file is called when source_import_type is FILE."""
        mock_integrity_link = MagicMock()
        mock_integrity_link.source_url = "/tmp/somefile.csv"
        mock_integrity_link.source_import_type = ImportType.FILE
        mock_integrity_link.created_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_integrity_link

        dag_success_callback(session=mock_session, integrity_link_id=str(uuid4()))

        mock_delete.assert_called_once_with("/tmp/somefile.csv")
