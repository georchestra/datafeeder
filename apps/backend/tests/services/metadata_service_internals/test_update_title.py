from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import (
        _Element,  # pyright: ignore[reportPrivateUsage]
    )


from src.services.metadata_service import NS_19115_3, NS_19139, MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_WITH_ONLINE_RESOURCES,
    SAMPLE_19139_WITH_ONLINE_RESOURCES,
)

RESOURCE_TITLE_XPATH_19115_3 = "mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource/cit:description/gco:CharacterString"

RESOURCE_TITLE_XPATH_19139 = "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:description/gco:CharacterString"


class TestUpdateTitle:
    def test_update_title_19115_3(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)

        updated = MetadataService._update_online_resources_when_title_changed_19115_3(  # pyright: ignore[reportPrivateUsage]
            root, "New Title"
        )

        nodes = updated.xpath(RESOURCE_TITLE_XPATH_19115_3, namespaces=NS_19115_3)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title"
        assert nodes[1].text == "New Title"
        assert nodes[2].text == "New Title"

    def test_update_title_19139(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19139_WITH_ONLINE_RESOURCES)

        updated = MetadataService._update_online_resources_when_title_changed_19139(  # pyright: ignore[reportPrivateUsage]
            root, "New Title"
        )

        nodes = updated.xpath(RESOURCE_TITLE_XPATH_19139, namespaces=NS_19139)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title"
        assert nodes[1].text == "New Title"
        assert nodes[2].text == "New Title"

    @patch("src.services.metadata_service.GnApi")
    def test_update_online_resources_when_title_changed_19139(self, mock_gn_api: MagicMock) -> None:
        datadir = Path(__file__).resolve().parents[4] / "docker" / "datadir"
        service = MetadataService(gn_api_url="http://test/api", datadir_path=str(datadir))

        updated = service.update_online_resources_when_title_changed(
            SAMPLE_19139_WITH_ONLINE_RESOURCES, "New Title 1"
        )

        nodes = etree.fromstring(updated).xpath(RESOURCE_TITLE_XPATH_19139, namespaces=NS_19139)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title 1"
        assert nodes[1].text == "New Title 1"
        assert nodes[2].text == "New Title 1"

    @patch("src.services.metadata_service.GnApi")
    def test_update_online_resources_when_title_changed_19115_3(
        self, mock_gn_api: MagicMock
    ) -> None:
        datadir = Path(__file__).resolve().parents[4] / "docker" / "datadir"
        service = MetadataService(gn_api_url="http://test/api", datadir_path=str(datadir))

        updated = service.update_online_resources_when_title_changed(
            SAMPLE_19115_3_WITH_ONLINE_RESOURCES, "New Title 2"
        )

        nodes = etree.fromstring(updated).xpath(RESOURCE_TITLE_XPATH_19115_3, namespaces=NS_19115_3)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title 2"
        assert nodes[1].text == "New Title 2"
        assert nodes[2].text == "New Title 2"
