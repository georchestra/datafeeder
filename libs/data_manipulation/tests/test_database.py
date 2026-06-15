"""Tests for database utility functions."""

from unittest.mock import MagicMock, patch

from data_manipulation.database import schema_exists, table_exists


class TestSchemaExists:
    """Test cases for schema_exists function."""

    @patch("data_manipulation.database.inspect")
    def test_schema_exists_returns_true(self, mock_inspect: MagicMock) -> None:
        mock_inspect.return_value.has_schema.return_value = True

        assert schema_exists(MagicMock(), "public") is True
        mock_inspect.return_value.has_schema.assert_called_once_with("public")

    @patch("data_manipulation.database.inspect")
    def test_schema_not_exists_returns_false(self, mock_inspect: MagicMock) -> None:
        mock_inspect.return_value.has_schema.return_value = False

        assert schema_exists(MagicMock(), "nonexistent") is False
        mock_inspect.return_value.has_schema.assert_called_once_with("nonexistent")


class TestTableExists:
    """Test cases for table_exists function."""

    @patch("data_manipulation.database.inspect")
    def test_table_exists_returns_true(self, mock_inspect: MagicMock) -> None:
        mock_inspect.return_value.has_table.return_value = True

        assert table_exists(MagicMock(), "public", "my_table") is True
        mock_inspect.return_value.has_table.assert_called_once_with("my_table", schema="public")

    @patch("data_manipulation.database.inspect")
    def test_table_not_exists_returns_false(self, mock_inspect: MagicMock) -> None:
        mock_inspect.return_value.has_table.return_value = False

        assert table_exists(MagicMock(), "public", "nonexistent") is False
        mock_inspect.return_value.has_table.assert_called_once_with("nonexistent", schema="public")
