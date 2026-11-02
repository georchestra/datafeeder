"""Tests for the direct access dataset creation endpoint."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import PostgresDsn

from src.api.routes.ingestion.direct_access_dataset import (
    CreateDirectAccessDatasetRequest,
    create_direct_access_dataset,
)
from src.core.config import CopySourceDatabase, DirectAccessSourceDatabase
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext
from src.services.layer_publication import TableExtent

MODULE = "src.api.routes.ingestion.direct_access_dataset"


def _ctx(roles: set[str] | None = None) -> GeorchestraContext:
    return GeorchestraContext(
        username="alice",
        roles=roles if roles is not None else {"USER"},
        email="alice@example.com",
        firstname="Alice",
        lastname="Liddell",
        organization="MEL",
    )


def _request(**overrides: str) -> CreateDirectAccessDatasetRequest:
    fields = {"db_key": "PATRIMOINE", "schema_name": "geo", "table_name": "rivers"}
    fields.update(overrides)
    return CreateDirectAccessDatasetRequest(**fields)  # type: ignore[arg-type]


def _session(duplicate: object = None) -> MagicMock:
    session = MagicMock()
    session.exec.return_value.first.return_value = duplicate

    def _flush() -> None:
        session.add.call_args[0][0].id = uuid4()

    session.flush.side_effect = _flush
    return session


def _added_link(session: MagicMock) -> IntegrityLink:
    return session.add.call_args[0][0]


def _geoserver(datastore_schema: str | None = None) -> MagicMock:
    geoserver = MagicMock()
    geoserver.get_datastore_schema.return_value = datastore_schema
    geoserver.create_workspace = AsyncMock()
    geoserver.create_layer = AsyncMock()
    return geoserver


@pytest.fixture
def settings() -> Iterator[MagicMock]:
    with patch(f"{MODULE}.get_settings") as get_settings:
        s = get_settings.return_value
        s.SOURCE_DATABASES = {
            "PATRIMOINE": DirectAccessSourceDatabase(
                type="direct_access",
                connection_string=PostgresDsn("postgresql://u:p@h:5432/patrimoine"),
                jndi_reference="jdbc/patrimoine",
                roles=["PATRIMOINE_EDITOR"],
            ),
            "COPY_DB": CopySourceDatabase(
                type="copy", connection_string=PostgresDsn("postgresql://u:p@h:5432/db")
            ),
        }
        s.CONSOLE_INTERNAL_URL = "http://console"
        s.GEONETWORK_XML_RECORD_URL = "http://gn/{metadata_id}.xml"
        s.DATAHUB_PUBLIC_URL = "http://datahub/{metadata_id}"
        yield s


@pytest.fixture
def source_db() -> Iterator[MagicMock]:
    """A source database where schema geo and table rivers exist, with a geometry."""
    with (
        patch(f"{MODULE}.get_source_engine") as get_engine,
        patch(f"{MODULE}.schema_exists", return_value=True),
        patch(f"{MODULE}.table_exists", return_value=True),
        patch(
            f"{MODULE}.read_source_table_extent",
            return_value=TableExtent(
                is_geographic=True,
                epsg=2154,
                bbox={"minx": 1.0, "miny": 2.0, "maxx": 3.0, "maxy": 4.0},
            ),
        ),
        patch(f"{MODULE}.ConsoleService") as console,
    ):
        console.return_value.get_organization.return_value = None
        yield get_engine


async def _create(
    session: MagicMock,
    geoserver: MagicMock,
    metadata: MagicMock,
    request: CreateDirectAccessDatasetRequest | None = None,
    roles: set[str] | None = None,
) -> MagicMock:
    with patch(f"{MODULE}.IntegrityLinkResponse.model_validate") as validate:
        await create_direct_access_dataset(
            request or _request(),
            session,
            _ctx(roles if roles is not None else {"PATRIMOINE_EDITOR"}),
            geoserver,
            metadata,
        )
    return validate


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_creates_link_metadata_datastore_and_layer() -> None:
    session, geoserver, metadata = _session(), _geoserver(), MagicMock()

    await _create(session, geoserver, metadata)

    link = _added_link(session)
    assert link.source_import_type == ImportType.DIRECT_ACCESS
    assert link.source_url == "db://PATRIMOINE/geo/rivers"
    assert link.integrity_title == "rivers"
    assert link.final_table_name is None
    assert link.metadata_id == str(link.id)
    assert link.data_id == "mel:rivers"
    metadata.create_and_publish_metadata.assert_called_once()
    metadata.set_record_ownership.assert_called_once_with(link)
    geoserver.create_workspace.assert_awaited_once_with(
        workspace_name="mel",
        datastore_name="patrimoine_geo",
        jndi_reference="jdbc/patrimoine",
        pg_schema="geo",
    )
    layer = geoserver.create_layer.await_args.kwargs
    assert layer["datastore_name"] == "patrimoine_geo"
    assert layer["table_name"] == "rivers"
    assert layer["epsg"] == 2154
    assert layer["is_geographic"] is True
    session.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_reuses_existing_datastore() -> None:
    session, geoserver = _session(), _geoserver(datastore_schema="geo")

    await _create(session, geoserver, MagicMock(), _request(title="  Rivières  "))

    geoserver.create_workspace.assert_not_awaited()
    geoserver.create_layer.assert_awaited_once()
    assert _added_link(session).integrity_title == "Rivières"


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings")
@pytest.mark.parametrize("db_key", ["UNKNOWN", "COPY_DB"])
async def test_rejects_unknown_or_copy_database(db_key: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _create(_session(), _geoserver(), MagicMock(), _request(db_key=db_key))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_requires_one_of_the_database_roles() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _create(_session(), _geoserver(), MagicMock(), roles={"USER"})
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_administrator_bypasses_database_roles() -> None:
    session = _session()
    await _create(session, _geoserver(), MagicMock(), roles={"ADMINISTRATOR"})
    session.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_rejects_table_name_geoserver_would_rename() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _create(_session(), _geoserver(), MagicMock(), _request(table_name="Rivers"))
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_rejects_missing_table() -> None:
    with patch(f"{MODULE}.table_exists", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await _create(_session(), _geoserver(), MagicMock())
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_rejects_table_already_published_by_the_organization() -> None:
    session = _session(duplicate=uuid4())
    with pytest.raises(HTTPException) as exc_info:
        await _create(session, _geoserver(), MagicMock())
    assert exc_info.value.status_code == 409
    session.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_metadata_failure_rolls_back() -> None:
    session, geoserver, metadata = _session(), _geoserver(), MagicMock()
    metadata.create_and_publish_metadata.side_effect = RuntimeError("GN down")

    with pytest.raises(HTTPException) as exc_info:
        await _create(session, geoserver, metadata)

    assert exc_info.value.status_code == 500
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    geoserver.create_layer.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_geoserver_failure_deletes_metadata_and_rolls_back() -> None:
    session, geoserver, metadata = _session(), _geoserver(), MagicMock()
    geoserver.create_layer.side_effect = RuntimeError("GS down")

    with pytest.raises(HTTPException) as exc_info:
        await _create(session, geoserver, metadata)

    assert exc_info.value.status_code == 500
    metadata.delete_record.assert_called_once_with(str(_added_link(session).id))
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.usefixtures("settings", "source_db")
async def test_datastore_on_another_schema_fails() -> None:
    session, geoserver, metadata = _session(), _geoserver(datastore_schema="other"), MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await _create(session, geoserver, metadata)

    assert exc_info.value.status_code == 500
    geoserver.create_layer.assert_not_awaited()
    metadata.delete_record.assert_called_once()
