"""Tests for the empty dataset creation endpoint."""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.api.routes.ingestion.empty_dataset import (
    CreateEmptyDatasetRequest,
    create_empty_dataset,
)
from src.models.data_import import ImportType
from src.services.georchestra import GeorchestraContext


def _geo_ctx(
    username: str = "testuser",
    organization: str = "testorg",
    email: str = "test@example.com",
    firstname: str = "Test",
    lastname: str = "User",
) -> GeorchestraContext:
    return GeorchestraContext(
        username=username,
        roles=set(),
        email=email,
        firstname=firstname,
        lastname=lastname,
        organization=organization,
    )


def _mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.CONSOLE_INTERNAL_URL = "http://console"
    settings.GEONETWORK_URL = "http://geonetwork"
    settings.GEONETWORK_USERNAME = "admin"
    settings.GEONETWORK_PASSWORD = "geonetwork"
    settings.DATADIR_PATH = "/datadir"
    settings.GN_SYNC_MODE = "ORG"
    return settings


def _make_session_with_link(link_id: UUID | None = None) -> MagicMock:
    """Return a mock session whose flush() assigns an ID to the first added object."""
    link_id = link_id or uuid4()
    session = MagicMock()

    def _flush_side_effect() -> None:
        added = session.add.call_args[0][0]
        added.id = link_id

    session.flush.side_effect = _flush_side_effect
    return session


class TestCreateEmptyDataset:
    """Tests for the create_empty_dataset endpoint."""

    def test_successful_creation_returns_201_with_empty_type(self) -> None:
        """Happy path: valid title → integrity link persisted with EMPTY import type."""
        link_id = uuid4()
        session = _make_session_with_link(link_id)

        session.refresh.return_value = None

        # Patch model_validate to avoid needing a fully wired SQLModel
        with (
            patch(
                "src.api.routes.ingestion.empty_dataset.get_settings",
                return_value=_mock_settings(),
            ),
            patch("src.api.routes.ingestion.empty_dataset.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.empty_dataset.MetadataService") as mock_ms_cls,
            patch(
                "src.api.routes.ingestion.empty_dataset.IntegrityLinkResponse.model_validate",
                return_value=MagicMock(
                    id=link_id,
                    source_import_type=ImportType.EMPTY,
                    integrity_title="My Dataset",
                ),
            ),
        ):
            mock_console_cls.return_value.get_organization.return_value = {
                "name": "Test Org",
                "mail": "org@example.com",
            }
            mock_ms_cls.return_value = MagicMock()

            result = create_empty_dataset(
                request=CreateEmptyDatasetRequest(title="My Dataset"),
                session=session,
                geo_ctx=_geo_ctx(),
            )

        assert result.source_import_type == ImportType.EMPTY
        assert result.integrity_title == "My Dataset"
        # flush + final commit must both have been called
        session.flush.assert_called_once()
        session.commit.assert_called_once()

    def test_no_title_creates_link_with_untitled_dataset(self) -> None:
        """A request without a title creates the integrity link with integrity_title='Untitled Dataset'."""
        link_id = uuid4()
        session = _make_session_with_link(link_id)

        session.refresh.return_value = None

        with (
            patch(
                "src.api.routes.ingestion.empty_dataset.get_settings",
                return_value=_mock_settings(),
            ),
            patch("src.api.routes.ingestion.empty_dataset.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.empty_dataset.MetadataService") as mock_ms_cls,
            patch(
                "src.api.routes.ingestion.empty_dataset.IntegrityLinkResponse.model_validate",
                return_value=MagicMock(
                    id=link_id,
                    source_import_type=ImportType.EMPTY,
                    integrity_title="Untitled Dataset",
                ),
            ),
        ):
            mock_console_cls.return_value.get_organization.return_value = None
            mock_ms_cls.return_value = MagicMock()

            result = create_empty_dataset(
                request=CreateEmptyDatasetRequest(),
                session=session,
                geo_ctx=_geo_ctx(),
            )

        added_link = session.add.call_args[0][0]
        assert added_link.integrity_title == "Untitled Dataset"
        assert result.integrity_title == "Untitled Dataset"
        session.add.assert_called_once()
        session.flush.assert_called_once()

    def test_metadata_publication_failure_rolls_back_and_raises_500(self) -> None:
        """If metadata creation fails the DB transaction is rolled back and HTTP 500 is raised."""
        link_id = uuid4()
        session = _make_session_with_link(link_id)

        with (
            patch(
                "src.api.routes.ingestion.empty_dataset.get_settings",
                return_value=_mock_settings(),
            ),
            patch("src.api.routes.ingestion.empty_dataset.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.empty_dataset.MetadataService") as mock_ms_cls,
        ):
            mock_console_cls.return_value.get_organization.return_value = None
            mock_ms = MagicMock()
            mock_ms.create_and_publish_metadata.side_effect = RuntimeError("GeoNetwork down")
            mock_ms_cls.return_value = mock_ms

            with pytest.raises(HTTPException) as exc_info:
                create_empty_dataset(
                    request=CreateEmptyDatasetRequest(title="My Dataset"),
                    session=session,
                    geo_ctx=_geo_ctx(),
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "import.metadataPublication.error"
        # The link must have been flushed (to get an ID) but rolled back on failure
        session.flush.assert_called_once()
        session.rollback.assert_called_once()
        # No final commit should have happened
        session.commit.assert_not_called()
