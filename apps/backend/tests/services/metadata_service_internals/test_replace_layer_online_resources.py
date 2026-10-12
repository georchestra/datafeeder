from typing import TYPE_CHECKING, Any
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

NEW_LAYER_URLS: dict[str, Any] = {
    "layer_qualified_name": "c2c:proj_3948",
    "ogcfeatures": "http://new/geoserver/ogc/features/v1/collections/c2c:proj_3948?f=json",
    "wfs": {"base": "http://new/geoserver/c2c/wfs"},
    "wms": {"base": "http://new/geoserver/c2c/wms"},
}
EXPECTED_LINKAGES = {
    "OGC API Features": NEW_LAYER_URLS["ogcfeatures"],
    "OGC:WMS": "http://new/geoserver/c2c/wms",
    "OGC:WFS": "http://new/geoserver/c2c/wfs",
}

RESOURCES_19115_3 = (
    "mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions"
    "/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource"
)
RESOURCES_19139 = (
    "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions"
    "/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource"
)


def _links(
    root: "_Element", resources_xpath: str, ns: dict[str, str], prefix: str, linkage: str
) -> dict[str, tuple[str, str]]:
    """{protocol: (name, linkage)} of the online resources of a record."""
    result: dict[str, tuple[str, str]] = {}
    for resource in root.xpath(resources_xpath, namespaces=ns):
        protocol = resource.xpath(f"{prefix}:protocol/gco:CharacterString/text()", namespaces=ns)
        name = resource.xpath(f"{prefix}:name/gco:CharacterString/text()", namespaces=ns)
        url = resource.xpath(f"{linkage}/text()", namespaces=ns)
        result[protocol[0]] = (name[0], url[0])
    return result


class TestReplaceLayerOnlineResources:
    def test_19115_3_links_follow_the_moved_layer(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)

        schema = Iso19115_3Schema(root, MagicMock())
        schema.replace_layer_online_resources("psc:proj_3948", NEW_LAYER_URLS)

        assert schema.updated is True
        links = _links(
            root, RESOURCES_19115_3, NS_19115_3, "cit", "cit:linkage/gco:CharacterString"
        )
        assert links == {p: ("c2c:proj_3948", url) for p, url in EXPECTED_LINKAGES.items()}

    def test_19139_links_follow_the_moved_layer(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19139_WITH_ONLINE_RESOURCES)

        schema = Iso19139Schema(root, MagicMock())
        schema.replace_layer_online_resources("psc:proj_3948", NEW_LAYER_URLS)

        assert schema.updated is True
        links = _links(root, RESOURCES_19139, NS_19139, "gmd", "gmd:linkage/gmd:URL")
        assert links == {p: ("c2c:proj_3948", url) for p, url in EXPECTED_LINKAGES.items()}

    def test_links_of_other_layers_are_kept(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)
        before = etree.tostring(root)

        schema = Iso19115_3Schema(root, MagicMock())
        schema.replace_layer_online_resources("other:layer", NEW_LAYER_URLS)

        assert schema.updated is False
        assert etree.tostring(root) == before
