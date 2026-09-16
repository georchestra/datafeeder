from typing import TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import (
        _Element,  # pyright: ignore[reportPrivateUsage]
    )

from src.services.metadata_service import NS_19115_3, MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_EMPTY_TRANSFER_OPTIONS,
    SAMPLE_19115_3_NO_REVISION,
    SAMPLE_19115_3_PARTIAL_ONLINE_RESOURCES,
    SAMPLE_19115_3_WITH_ONLINE_RESOURCES,
)

ONLINE_RESOURCE_XPATH = (
    "mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions"
    "/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource"
)

LAYER_URLS: dict[str, Any] = {
    "layer_qualified_name": "psc:proj_3948",
    "ogcfeatures": "http://localhost:8080/geoserver/ogc/features/v1/collections/psc:proj_3948?f=json",
    "wfs": {"base": "http://localhost:8080/geoserver/psc/wfs"},
    "wms": {"base": "http://localhost:8080/geoserver/psc/wms"},
}


def _resource_by_protocol(root: "_Element") -> dict[str, "_Element"]:
    resources = root.xpath(ONLINE_RESOURCE_XPATH, namespaces=NS_19115_3)
    result: dict[str, "_Element"] = {}
    for resource in resources:
        protocol = resource.xpath("cit:protocol/gco:CharacterString/text()", namespaces=NS_19115_3)
        result[protocol[0]] = resource
    return result


class TestAddOnlineResourcesFromLayerUrls:
    def test_adds_all_resources_when_none_exist(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_EMPTY_TRANSFER_OPTIONS)

        updated = MetadataService.add_online_resources_from_layer_urls_19115_3(root, LAYER_URLS)

        assert updated is True
        by_protocol = _resource_by_protocol(root)
        assert set(by_protocol) == {"OGC API Features", "OGC:WMS", "OGC:WFS"}

        ogcfeatures = by_protocol["OGC API Features"]
        assert (
            ogcfeatures.xpath("cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3)[0]
            == LAYER_URLS["ogcfeatures"]
        )
        assert (
            ogcfeatures.xpath("cit:name/gco:CharacterString/text()", namespaces=NS_19115_3)[0]
            == "psc:proj_3948"
        )
        assert (
            ogcfeatures.xpath("cit:description/gco:CharacterString/text()", namespaces=NS_19115_3)[
                0
            ]
            == "My Dataset"
        )

        wms = by_protocol["OGC:WMS"]
        assert (
            wms.xpath("cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3)[0]
            == LAYER_URLS["wms"]["base"]
        )

        wfs = by_protocol["OGC:WFS"]
        assert (
            wfs.xpath("cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3)[0]
            == LAYER_URLS["wfs"]["base"]
        )

    def test_does_not_touch_existing_resource_for_same_protocol(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_PARTIAL_ONLINE_RESOURCES)

        updated: bool = MetadataService.add_online_resources_from_layer_urls_19115_3(
            root, LAYER_URLS
        )

        assert updated is True
        by_protocol = _resource_by_protocol(root)
        assert (
            by_protocol["OGC:WMS"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == "http://existing/geoserver/psc/wms"
        )
        assert (
            by_protocol["OGC API Features"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == LAYER_URLS["ogcfeatures"]
        )
        assert (
            by_protocol["OGC:WFS"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == LAYER_URLS["wfs"]["base"]
        )

    def test_does_not_add_anything_when_all_protocols_already_exist(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_WITH_ONLINE_RESOURCES)

        updated: bool = MetadataService.add_online_resources_from_layer_urls_19115_3(
            root, LAYER_URLS
        )

        assert updated is False
        by_protocol = _resource_by_protocol(root)
        assert (
            by_protocol["OGC API Features"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == "http://existing/geoserver/ogc/features/v1/collections/psc:proj_3948?f=json"
        )
        assert (
            by_protocol["OGC:WMS"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == "http://existing/geoserver/psc/wms"
        )
        assert (
            by_protocol["OGC:WFS"].xpath(
                "cit:linkage/gco:CharacterString/text()", namespaces=NS_19115_3
            )[0]
            == "http://existing/geoserver/psc/wfs"
        )

    def test_is_noop_when_no_transfer_options(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_NO_REVISION)

        updated: bool = MetadataService.add_online_resources_from_layer_urls_19115_3(
            root, LAYER_URLS
        )

        assert updated is False
        assert root.xpath(ONLINE_RESOURCE_XPATH, namespaces=NS_19115_3) == []

    def test_ignores_missing_layer_url_keys(self) -> None:
        root: _Element = etree.fromstring(SAMPLE_19115_3_EMPTY_TRANSFER_OPTIONS)

        updated: bool = MetadataService.add_online_resources_from_layer_urls_19115_3(
            root,
            {"layer_qualified_name": "psc:proj_3948", "ogcfeatures": LAYER_URLS["ogcfeatures"]},
        )

        assert updated is True
        by_protocol = _resource_by_protocol(root)
        assert set(by_protocol) == {"OGC API Features"}
