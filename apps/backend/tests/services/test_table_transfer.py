"""Tests for the parsing and checks of a table transfer stream (no database)."""

import gzip
import io
from unittest.mock import MagicMock

import pytest

from src.services.table_transfer import (
    TableDefinition,
    TableTransferError,
    TransferColumn,
    _check_definition,  # pyright: ignore[reportPrivateUsage]
    _decompressed_chunks,  # pyright: ignore[reportPrivateUsage]
    _split_definition,  # pyright: ignore[reportPrivateUsage]
)

DEFINITION = b'{"columns":[{"name":"n","type":"integer"},{"name":"geom","type":"geometry"}]}'


def _chunks(data: bytes) -> list[bytes]:
    return list(_decompressed_chunks(io.BytesIO(data)))


class TestDecompression:
    def test_decompresses_the_stream(self) -> None:
        assert b"".join(_chunks(gzip.compress(b"rows" * 1000))) == b"rows" * 1000

    def test_truncated_stream_is_rejected(self) -> None:
        data = gzip.compress(b"rows" * 1000)
        with pytest.raises(TableTransferError, match="Truncated"):
            _chunks(data[: len(data) // 2])

    def test_not_gzip_is_rejected(self) -> None:
        with pytest.raises(TableTransferError, match="Invalid gzip"):
            _chunks(b"plain text")


class TestSplitDefinition:
    def test_definition_and_first_rows_split_across_chunks(self) -> None:
        line = DEFINITION + b"\n1\tAB\n"

        definition, rest = _split_definition(iter([line[:10], line[10:]]))

        assert [c.name for c in definition.columns] == ["n", "geom"]
        assert rest == b"1\tAB\n"

    def test_missing_definition_is_rejected(self) -> None:
        with pytest.raises(TableTransferError, match="No table definition"):
            _split_definition(iter([b"no newline"]))

    @pytest.mark.parametrize("line", [b"not json", b'{"columns":[]}'])
    def test_invalid_definition_is_rejected(self, line: bytes) -> None:
        with pytest.raises(TableTransferError):
            _split_definition(iter([line + b"\n"]))


def _definition(*types: str, **kwargs: list[str]) -> TableDefinition:
    return TableDefinition(
        columns=[TransferColumn(name=f"c{i}", type=t) for i, t in enumerate(types)], **kwargs
    )


class TestCheckDefinition:
    @pytest.mark.parametrize(
        "column_type",
        [
            "integer",
            "geometry(MultiPolygon,2154)",
            "timestamp(3) without time zone",
            "character varying(20)[]",
            "numeric(10,2)",
        ],
    )
    def test_format_type_outputs_are_resolved_by_postgresql(self, column_type: str) -> None:
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (column_type,)

        _check_definition(conn, _definition(column_type))

        assert conn.execute.call_args.args[1] == [column_type]

    @pytest.mark.parametrize(
        "column_type", ["int); DROP TABLE x; --", "int, b int", "text; SELECT 1"]
    )
    def test_injection_is_rejected_before_postgresql(self, column_type: str) -> None:
        conn = MagicMock()
        with pytest.raises(TableTransferError, match="Invalid type"):
            _check_definition(conn, _definition(column_type))
        conn.execute.assert_not_called()

    def test_type_unknown_to_postgresql_is_rejected(self) -> None:
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (None,)
        with pytest.raises(TableTransferError, match="does not exist"):
            _check_definition(conn, _definition("nosuchtype"))

    def test_index_on_unknown_column_is_rejected(self) -> None:
        with pytest.raises(TableTransferError, match="Unknown columns"):
            _check_definition(MagicMock(), _definition("integer", primary_key=["other"]))
