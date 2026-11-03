"""Copy of a final table between platforms, as a gzip stream.

The stream is one JSON line (the table definition), then the rows in PostgreSQL COPY text
format, whose geometries are hex EWKB: it does not depend on the PostgreSQL or PostGIS version.
"""

import re
import zlib
from collections.abc import Iterator
from typing import IO, Any, LiteralString, cast

from data_manipulation.transformation.sql_transform import ID_COLUMN
from psycopg import Connection, errors, sql
from pydantic import BaseModel, ValidationError

from src.core.db import data_engine
from src.core.logging import get_logger

logger = get_logger()

GZIP_WBITS = 16 + zlib.MAX_WBITS
READ_SIZE = 1024 * 1024
MAX_DEFINITION_SIZE = 1024 * 1024
# Output of format_type(), e.g. "geometry(MultiPolygon,2154)", "timestamp(3) without time
# zone", "character varying[]"; checked with to_regtype as well
_TYPE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_ .\"]*(\([A-Za-z0-9_, ]*\))?[A-Za-z ]*(\[\])*$")


class TableTransferError(Exception):
    """The stream cannot be restored (invalid definition or data)."""


class TableNotFoundError(Exception):
    """The table to dump does not exist (anymore)."""


class TableExistsError(Exception):
    """The table to restore already exists."""


class TransferColumn(BaseModel):
    name: str
    type: str
    not_null: bool = False


class TableDefinition(BaseModel):
    columns: list[TransferColumn]
    primary_key: list[str] = []
    # Columns with a single-column GIST index
    gist_columns: list[str] = []


def _driver_connection(sa_connection: Any) -> Connection[Any]:
    """psycopg connection, whose transaction is ended with its own commit() or rollback()."""
    return sa_connection.connection.driver_connection


def _read_definition(conn: Connection[Any], table: sql.Composable) -> TableDefinition:
    oid = sql.SQL("{}::regclass").format(sql.Literal(table.as_string(conn)))
    columns = conn.execute(
        sql.SQL(
            "SELECT attname, format_type(atttypid, atttypmod), attnotnull FROM pg_attribute "
            "WHERE attrelid = {} AND attnum > 0 AND NOT attisdropped ORDER BY attnum"
        ).format(oid)
    ).fetchall()
    primary_key = conn.execute(
        sql.SQL(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = {} AND i.indisprimary "
            "ORDER BY array_position(i.indkey::int2[], a.attnum)"
        ).format(oid)
    ).fetchall()
    gist_columns = conn.execute(
        sql.SQL(
            "SELECT DISTINCT a.attname FROM pg_index i "
            "JOIN pg_class c ON c.oid = i.indexrelid "
            "JOIN pg_am am ON am.oid = c.relam "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0] "
            "WHERE i.indrelid = {} AND am.amname = 'gist' AND i.indnatts = 1"
        ).format(oid)
    ).fetchall()
    return TableDefinition(
        columns=[TransferColumn(name=n, type=t, not_null=nn) for n, t, nn in columns],
        primary_key=[row[0] for row in primary_key],
        gist_columns=[row[0] for row in gist_columns],
    )


def dump_table(schema: str, table_name: str, output: IO[bytes]) -> None:
    """Write the gzip stream of the table, read in a single snapshot, to output.

    Written in full before being sent: the lock and the connection are not held for as long
    as the client takes to read it. Raises TableNotFoundError if the table does not exist.
    """
    table = sql.Identifier(schema, table_name)
    compressor = zlib.compressobj(wbits=GZIP_WBITS)
    with data_engine.connect() as sa_connection:
        conn = _driver_connection(sa_connection)
        try:
            # A re-ingestion replacing the table waits for the end of the dump
            conn.execute(sql.SQL("LOCK TABLE {} IN ACCESS SHARE MODE").format(table))
            definition = _read_definition(conn, table)
            output.write(compressor.compress(definition.model_dump_json().encode() + b"\n"))
            columns = sql.SQL(", ").join(sql.Identifier(c.name) for c in definition.columns)
            with conn.cursor() as cursor:
                with cursor.copy(sql.SQL("COPY {} ({}) TO STDOUT").format(table, columns)) as copy:
                    for data in copy:
                        output.write(compressor.compress(data))
            conn.rollback()
        except errors.UndefinedTable as e:
            raise TableNotFoundError(f"Table {schema}.{table_name} not found") from e
    output.write(compressor.flush())


def _decompressed_chunks(stream: IO[bytes]) -> Iterator[bytes]:
    decompressor = zlib.decompressobj(wbits=GZIP_WBITS)
    try:
        while data := stream.read(READ_SIZE):
            if decompressor.eof:
                raise TableTransferError("Data after the end of the gzip stream")
            if chunk := decompressor.decompress(data):
                yield chunk
        if not decompressor.eof:
            raise TableTransferError("Truncated stream")
    except zlib.error as e:
        raise TableTransferError(f"Invalid gzip stream: {e}") from e


def _split_definition(chunks: Iterator[bytes]) -> tuple[TableDefinition, bytes]:
    """Definition line, and the start of the rows read with it."""
    buffer = b""
    for chunk in chunks:
        buffer += chunk
        if b"\n" in buffer:
            line, rest = buffer.split(b"\n", 1)
            try:
                definition = TableDefinition.model_validate_json(line)
            except ValidationError as e:
                raise TableTransferError(f"Invalid table definition: {e}") from e
            if not definition.columns:
                raise TableTransferError("The table definition has no column")
            return definition, rest
        if len(buffer) > MAX_DEFINITION_SIZE:
            break
    raise TableTransferError("No table definition at the start of the stream")


def _check_definition(conn: Connection[Any], definition: TableDefinition) -> None:
    names = [c.name for c in definition.columns]
    if len(set(names)) != len(names):
        raise TableTransferError("Duplicate column names")
    unknown = (set(definition.primary_key) | set(definition.gist_columns)) - set(names)
    if unknown:
        raise TableTransferError(f"Unknown columns in the indexes: {sorted(unknown)}")
    for column in definition.columns:
        # The type is inlined in CREATE TABLE: only accept a type name that PostgreSQL resolves
        if not _TYPE_PATTERN.match(column.type):
            raise TableTransferError(f"Invalid type '{column.type}' of column {column.name}")
        try:
            with conn.transaction():
                resolved = conn.execute("SELECT to_regtype(%s)", [column.type]).fetchone()
        # Syntax error in the type name, or invalid modifier (e.g. "numeric(5000)")
        except (errors.SyntaxError, errors.DataError) as e:
            raise TableTransferError(f"Invalid type '{column.type}': {e}") from e
        if resolved is None or resolved[0] is None:
            raise TableTransferError(
                f"Type '{column.type}' of column {column.name} does not exist on this platform"
            )


def _create_table(
    conn: Connection[Any], table: sql.Composable, definition: TableDefinition
) -> None:
    column_definitions: list[sql.Composable] = []
    for column in definition.columns:
        # Type checked by _check_definition
        column_type = cast(LiteralString, column.type)
        parts: list[sql.Composable] = [sql.Identifier(column.name), sql.SQL(column_type)]
        if column.not_null:
            parts.append(sql.SQL("NOT NULL"))
        if column.name == ID_COLUMN and column.type == "uuid":
            parts.append(sql.SQL("DEFAULT gen_random_uuid()"))
        column_definitions.append(sql.SQL(" ").join(parts))
    conn.execute(
        sql.SQL("CREATE TABLE {} ({})").format(table, sql.SQL(", ").join(column_definitions))
    )


def _create_indexes(
    conn: Connection[Any], table_name: str, table: sql.Composable, definition: TableDefinition
) -> None:
    for column in definition.gist_columns:
        conn.execute(
            sql.SQL("CREATE INDEX {} ON {} USING GIST ({})").format(
                sql.Identifier(f"idx_{table_name}_{column}"), table, sql.Identifier(column)
            )
        )
    if definition.primary_key:
        conn.execute(
            sql.SQL("ALTER TABLE {} ADD PRIMARY KEY ({})").format(
                table, sql.SQL(", ").join(sql.Identifier(c) for c in definition.primary_key)
            )
        )


def restore_table(stream: IO[bytes], schema: str, table_name: str) -> int:
    """Create the table from a dump_table stream, in one transaction. Returns the row count.

    Raises TableTransferError for an invalid stream, TableExistsError if the table was created
    meanwhile; nothing is created then. Server-side failures propagate as they are.
    """
    table = sql.Identifier(schema, table_name)
    chunks = _decompressed_chunks(stream)
    definition, first_rows = _split_definition(chunks)
    with data_engine.connect() as sa_connection:
        conn = _driver_connection(sa_connection)
        try:
            _check_definition(conn, definition)
            try:
                _create_table(conn, table, definition)
            # UniqueViolation (on pg_type) when a concurrent restore created it first
            except (errors.DuplicateTable, errors.UniqueViolation) as e:
                raise TableExistsError(f"Table {schema}.{table_name} exists") from e
            columns = sql.SQL(", ").join(sql.Identifier(c.name) for c in definition.columns)
            try:
                with conn.cursor() as cursor:
                    copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(table, columns)
                    with cursor.copy(copy_sql) as copy:
                        if first_rows:
                            copy.write(first_rows)
                        for chunk in chunks:
                            copy.write(chunk)
                    row_count = cursor.rowcount
                # After the COPY: faster than maintaining them row by row
                _create_indexes(conn, table_name, table, definition)
            # Invalid value or row format, NULL in a NOT NULL column, duplicate primary key
            except (errors.DataError, errors.IntegrityError) as e:
                logger.warning(f"Data rejected restoring {schema}.{table_name}: {e}")
                raise TableTransferError(f"Data rejected by PostgreSQL: {e}") from e
            conn.execute(sql.SQL("ANALYZE {}").format(table))
        except BaseException:
            conn.rollback()
            raise
        conn.commit()
    logger.info(f"Restored {schema}.{table_name} ({row_count} rows)")
    return row_count
