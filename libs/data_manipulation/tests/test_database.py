"""Tests for database utility functions."""

from unittest.mock import MagicMock, patch

from data_manipulation.database import schema_exists, table_exists


class TestSchemaExists:
    """Test cases for schema_exists function."""

    def test_schema_exists_returns_true(self) -> None:
        inspector = MagicMock()
        inspector.has_schema.return_value = True

        with patch("data_manipulation.database.inspect", return_value=inspector):
            assert schema_exists(MagicMock(), "public") is True

        inspector.has_schema.assert_called_once_with("public")

    def test_schema_not_exists_returns_false(self) -> None:
        inspector = MagicMock()
        inspector.has_schema.return_value = False

        with patch("data_manipulation.database.inspect", return_value=inspector):
            assert schema_exists(MagicMock(), "nonexistent") is False


class TestTableExists:
    """Test cases for table_exists function."""

    def test_table_exists_returns_true(self) -> None:
        inspector = MagicMock()
        inspector.has_table.return_value = True

        with patch("data_manipulation.database.inspect", return_value=inspector):
            assert table_exists(MagicMock(), "public", "my_table") is True

        inspector.has_table.assert_called_once_with("my_table", schema="public")

    def test_table_not_exists_returns_false(self) -> None:
        inspector = MagicMock()
        inspector.has_table.return_value = False

        with patch("data_manipulation.database.inspect", return_value=inspector):
            assert table_exists(MagicMock(), "public", "nonexistent") is False
