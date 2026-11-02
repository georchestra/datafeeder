"""Tests for the metadata record creation of a new dataset."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext
from src.services.metadata_publication import publish_new_record

AUTHOR = GeorchestraContext(
    username="alice",
    roles={"USER"},
    email="alice@example.com",
    firstname="Alice",
    lastname="Liddell",
    organization="MEL",
)


def _link() -> IntegrityLink:
    return IntegrityLink(
        id=uuid4(),
        integrity_owner="alice",
        integrity_organization="MEL",
        source_import_type=ImportType.EMPTY,
    )


@pytest.fixture
def console() -> Iterator[MagicMock]:
    with patch("src.services.metadata_publication.ConsoleService") as console_cls:
        yield console_cls.return_value


def _contact(metadata_service: MagicMock) -> dict[str, Any]:
    return metadata_service.create_and_publish_metadata.call_args.kwargs


def test_contact_is_the_organization(console: MagicMock) -> None:
    console.get_organization.return_value = {"name": "Métropole", "mail": "mel@example.com"}
    metadata_service, link = MagicMock(), _link()

    publish_new_record(metadata_service, link, AUTHOR, {"wms": {}})

    console.get_organization.assert_called_once_with("MEL")
    assert _contact(metadata_service) == {
        "user_email": "mel@example.com",
        "user_first_name": "Métropole",
        "user_last_name": "",
        "organization_name": "Métropole",
        "layer_urls": {"wms": {}},
    }
    assert link.metadata_id == str(link.id)
    metadata_service.set_record_ownership.assert_called_once_with(link)


def test_contact_is_the_author_without_organization(console: MagicMock) -> None:
    console.get_organization.return_value = None
    metadata_service = MagicMock()

    publish_new_record(metadata_service, _link(), AUTHOR)

    assert _contact(metadata_service) == {
        "user_email": "alice@example.com",
        "user_first_name": "Alice",
        "user_last_name": "Liddell",
        "organization_name": "",
        "layer_urls": None,
    }


def test_organization_without_name_or_mail_falls_back_to_the_author(console: MagicMock) -> None:
    console.get_organization.return_value = {}
    metadata_service = MagicMock()

    publish_new_record(metadata_service, _link(), AUTHOR)

    contact = _contact(metadata_service)
    assert contact["user_email"] == "alice@example.com"
    assert contact["user_first_name"] == "Alice"
    assert contact["user_last_name"] == "Liddell"


@pytest.mark.usefixtures("console")
def test_ownership_failure_is_soft() -> None:
    metadata_service, link = MagicMock(), _link()
    metadata_service.set_record_ownership.side_effect = RuntimeError("GN down")

    publish_new_record(metadata_service, link, AUTHOR)

    assert link.metadata_id == str(link.id)


@pytest.mark.usefixtures("console")
def test_creation_failure_propagates() -> None:
    metadata_service, link = MagicMock(), _link()
    metadata_service.create_and_publish_metadata.side_effect = RuntimeError("GN down")

    with pytest.raises(RuntimeError):
        publish_new_record(metadata_service, link, AUTHOR)

    assert link.metadata_id is None
    metadata_service.set_record_ownership.assert_not_called()
