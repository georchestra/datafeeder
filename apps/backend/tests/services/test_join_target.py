"""Tests for resolving the joined dataset of a JoinConfig to its final table."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation.models import IntegrityTransformation, JoinConfig, JoinTarget
from fastapi import HTTPException

from src.core.security import AccessLevel
from src.services.join_target import joins_geom, resolve_join_target


def _join(columns: list[str] | None = None) -> JoinConfig:
    return JoinConfig(
        integrity_link_id=uuid4(),
        source_column="insee",
        target_column="code_insee",
        columns=["nom"] if columns is None else columns,
    )


def _resolve(join: JoinConfig | None, load: MagicMock) -> JoinTarget | None:
    with (
        patch("src.services.join_target.load_authorized_integrity_link", load),
        patch("src.services.join_target.get_data_schema", side_effect=str.lower),
    ):
        return resolve_join_target(join, MagicMock(), MagicMock(), [])


def _loads(final_table_name: str | None) -> MagicMock:
    link = MagicMock(integrity_organization="ORG_B", final_table_name=final_table_name)
    return MagicMock(return_value=(link, MagicMock()))


class TestResolveJoinTarget:
    def test_final_table_of_the_joined_dataset(self) -> None:
        join = _join()
        load = _loads("communes")

        assert _resolve(join, load) == JoinTarget(table_schema="org_b", table_name="communes")
        assert load.call_args.args[0] == str(join.integrity_link_id)
        assert load.call_args.args[1] == AccessLevel.METADATA_READ

    def test_no_join(self) -> None:
        load = _loads("communes")

        assert _resolve(None, load) is None
        load.assert_not_called()

    def test_empty_columns_means_no_join(self) -> None:
        load = _loads("communes")

        assert _resolve(_join(columns=[]), load) is None
        load.assert_not_called()

    def test_unreadable_joined_dataset(self) -> None:
        load = MagicMock(side_effect=HTTPException(status_code=403, detail="Forbidden"))

        with pytest.raises(HTTPException) as exc:
            _resolve(_join(), load)

        assert exc.value.status_code == 403
        assert "Joined dataset" in exc.value.detail

    def test_joined_dataset_without_final_table(self) -> None:
        with pytest.raises(HTTPException) as exc:
            _resolve(_join(), _loads(None))

        assert exc.value.status_code == 422


class TestJoinsGeom:
    def test_joined_geom(self) -> None:
        assert joins_geom(IntegrityTransformation(join=_join(columns=["nom", "geom"])))

    def test_joined_columns_without_geom(self) -> None:
        assert not joins_geom(IntegrityTransformation(join=_join()))

    def test_no_join(self) -> None:
        assert not joins_geom(IntegrityTransformation())
        assert not joins_geom(None)
