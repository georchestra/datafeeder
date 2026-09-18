from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import (
        _Element,  # pyright: ignore[reportPrivateUsage]
    )


from src.services.metadata_schema_19115_3 import NS_19115_3, Iso19115_3Schema
from src.services.metadata_schema_19139 import NS_19139, Iso19139Schema
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_WITH_ONLINE_RESOURCES,
    SAMPLE_19139_WITH_ONLINE_RESOURCES,
)

RESOURCE_TITLE_XPATH_19115_3 = "mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource/cit:description/gco:CharacterString"

RESOURCE_TITLE_XPATH_19139 = "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:description/gco:CharacterString"


class TestUpdateTitle:
    def test_update_title_19115_3(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)

        schema = Iso19115_3Schema(root, MagicMock())
        schema.update_online_resources_when_title_changed("New Title")

        assert schema.updated is True
        nodes = root.xpath(RESOURCE_TITLE_XPATH_19115_3, namespaces=NS_19115_3)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title"
        assert nodes[1].text == "New Title"
        assert nodes[2].text == "New Title"

    def test_update_title_19115_3_is_noop_when_title_unchanged(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)
        current_title = root.xpath(RESOURCE_TITLE_XPATH_19115_3, namespaces=NS_19115_3)[0].text

        schema = Iso19115_3Schema(root, MagicMock())
        schema.update_online_resources_when_title_changed(current_title)

        assert schema.updated is False

    def test_update_title_19139(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19139_WITH_ONLINE_RESOURCES)

        schema = Iso19139Schema(root, MagicMock())
        schema.update_online_resources_when_title_changed("New Title")

        assert schema.updated is True
        nodes = root.xpath(RESOURCE_TITLE_XPATH_19139, namespaces=NS_19139)
        assert len(nodes) == 3
        assert nodes[0].text == "New Title"
        assert nodes[1].text == "New Title"
        assert nodes[2].text == "New Title"

    def test_update_title_19139_is_noop_when_title_unchanged(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19139_WITH_ONLINE_RESOURCES)
        current_title = root.xpath(RESOURCE_TITLE_XPATH_19139, namespaces=NS_19139)[0].text

        schema = Iso19139Schema(root, MagicMock())
        schema.update_online_resources_when_title_changed(current_title)

        assert schema.updated is False
