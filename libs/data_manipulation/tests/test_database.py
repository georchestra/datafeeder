"""Tests for database utility functions."""

from unittest.mock import MagicMock, Mock

from data_manipulation.database import schema_exists, table_exists


class TestSchemaExists:
    """Test cases for schema_exists function."""

    def test_schema_exists_returns_true(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("public",)
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        assert schema_exists(mock_engine, "public") is True

    def test_schema_not_exists_returns_false(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        assert schema_exists(mock_engine, "nonexistent") is False


class TestTableExists:
    """Test cases for table_exists function."""

    def test_table_exists_returns_true(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("my_table",)
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        assert table_exists(mock_engine, "public", "my_table") is True

    def test_table_not_exists_returns_false(self) -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        assert table_exists(mock_engine, "public", "nonexistent") is False
