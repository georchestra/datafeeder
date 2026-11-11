"""Tests for resolving the joined dataset of a JoinConfig to its final table."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation.models import IntegrityTransformation, JoinConfig, JoinedColumn, JoinTarget
from fastapi import HTTPException

from src.services.join_target import (
    JOIN_UNAVAILABLE,
    get_join_target,
    joins_geom,
    resolve_join_target,
)


def _join(columns: list[str] | None = None) -> JoinConfig:
    return JoinConfig(
        integrity_link_id=uuid4(),
        source_column="insee",
        target_column="code_insee",
        columns=[
            JoinedColumn(original_name=col) for col in (["nom"] if columns is None else columns)
        ],
    )


TARGET = JoinTarget(table_schema="org_b", table_name="communes")


def _session(row: tuple[str, str] | None) -> MagicMock:
    session = MagicMock()
    session.exec.return_value.first.return_value = row
    return session


def _resolve(join: JoinConfig | None, target: JoinTarget | None) -> MagicMock:
    """Resolve *join* with get_join_target returning *target*; return that mock."""
    with patch("src.services.join_target.get_join_target", return_value=target) as get:
        resolve_join_target(join, MagicMock())
    return get


def _sql(clause: object) -> str:
    return str(clause.compile(compile_kwargs={"literal_binds": True}))  # type: ignore[attr-defined]


class TestGetJoinTarget:
    def test_query_is_restricted_to_joinable_datasets(self) -> None:
        session = _session(None)
        link_id = uuid4()

        with patch("src.services.join_target.table_exists") as table_exists:
            assert get_join_target(link_id, session) is None
        table_exists.assert_not_called()

        sql = _sql(session.exec.call_args.args[0].whereclause)
        assert link_id.hex in sql.replace("-", "")
        assert "is_reference_dataset" in sql
        assert "integrity_owner" not in sql

    @pytest.mark.parametrize("exists", [True, False])
    def test_final_table_must_exist_in_the_data_database(self, exists: bool) -> None:
        with (
            patch("src.services.join_target.get_data_schema", side_effect=str.lower),
            patch("src.services.join_target.table_exists", return_value=exists) as table_exists,
        ):
            result = get_join_target(uuid4(), _session(("ORG_B", "communes")))

        assert result == (TARGET if exists else None)
        assert table_exists.call_args.args[1:] == ("org_b", "communes")


class TestResolveJoinTarget:
    def test_final_table_of_the_joined_dataset(self) -> None:
        join = _join()

        with patch("src.services.join_target.get_join_target", return_value=TARGET) as get:
            assert resolve_join_target(join, MagicMock()) == TARGET
        assert get.call_args.args[0] == join.integrity_link_id

    @pytest.mark.parametrize("join", [None, _join(columns=[])])
    def test_no_join(self, join: JoinConfig | None) -> None:
        _resolve(join, TARGET).assert_not_called()

    def test_joined_dataset_not_joinable(self) -> None:
        with pytest.raises(HTTPException) as exc:
            _resolve(_join(), None)

        assert exc.value.status_code == 422
        assert exc.value.detail == JOIN_UNAVAILABLE


class TestJoinsGeom:
    def test_joined_geom(self) -> None:
        assert joins_geom(IntegrityTransformation(join=_join(columns=["nom", "geom"])))

    def test_joined_columns_without_geom(self) -> None:
        assert not joins_geom(IntegrityTransformation(join=_join()))

    def test_no_join(self) -> None:
        assert not joins_geom(IntegrityTransformation())
        assert not joins_geom(None)
