from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

from src.services.metadata_schema import MetadataSchema

NS_19115_3 = {
    "mdb": "http://standards.iso.org/iso/19115/-3/mdb/2.0",
    "mri": "http://standards.iso.org/iso/19115/-3/mri/1.0",
    "cit": "http://standards.iso.org/iso/19115/-3/cit/2.0",
    "gco": "http://standards.iso.org/iso/19115/-3/gco/1.0",
    "lan": "http://standards.iso.org/iso/19115/-3/lan/1.0",
    "mrd": "http://standards.iso.org/iso/19115/-3/mrd/1.0",
}

_CODELIST_URL = (
    "http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_DateTypeCode"
)
_ONLINE_FUNCTION_CODELIST_URL = (
    "http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_OnLineFunctionCode"
)

# Maps a layer_urls key (from GeoserverService.build_layer_urls_for_metadata) to the
# ISO CI_OnlineResource protocol name it should be published under.
_LAYER_URL_PROTOCOLS = (
    ("ogcfeatures", "OGC API Features"),
    ("wms", "OGC:WMS"),
    ("wfs", "OGC:WFS"),
)

RESOURCE_TITLE_XPATH_19115_3 = "mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource/cit:description/gco:CharacterString"


class Iso19115_3Schema(MetadataSchema):
    @staticmethod
    def update_revision_date(root: _Element, revision_date: datetime) -> bool:
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        ns = NS_19115_3

        citations = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification/mri:citation/cit:CI_Citation",
            namespaces=ns,
        )
        updated = False
        for citation in citations:
            existing = citation.xpath(
                "cit:date/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
                "/@codeListValue='revision']/cit:date/*[self::gco:DateTime or self::gco:Date]",
                namespaces=ns,
            )
            if existing:
                date_node = existing[0]
                date_node.tag = f"{{{ns['gco']}}}DateTime"
                date_node.text = date_str
            else:
                cit_date_wrapper: _Element = etree.SubElement(citation, f"{{{ns['cit']}}}date")
                ci_date_el: _Element = etree.SubElement(cit_date_wrapper, f"{{{ns['cit']}}}CI_Date")
                cit_d: _Element = etree.SubElement(ci_date_el, f"{{{ns['cit']}}}date")
                etree.SubElement(cit_d, f"{{{ns['gco']}}}DateTime").text = date_str
                cit_dt: _Element = etree.SubElement(ci_date_el, f"{{{ns['cit']}}}dateType")
                etree.SubElement(
                    cit_dt,
                    f"{{{ns['cit']}}}CI_DateTypeCode",
                    attrib={"codeList": _CODELIST_URL, "codeListValue": "revision"},
                ).text = "revision"
            updated = True
        return updated

    @staticmethod
    def get_title(root: _Element) -> str | None:
        nodes = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification"
            "/mri:citation/cit:CI_Citation/cit:title/gco:CharacterString",
            namespaces=NS_19115_3,
        )
        return nodes[0].text if nodes and nodes[0].text else None

    @staticmethod
    def update_online_resources_when_title_changed(root: _Element, title: str) -> bool:
        changed = False
        for online in root.xpath(RESOURCE_TITLE_XPATH_19115_3, namespaces=NS_19115_3):
            if online.text != title:
                online.text = title
                changed = True
        return changed

    @staticmethod
    def add_online_resources_from_layer_urls_19115_3(
        root: _Element, layer_urls: dict[str, Any]
    ) -> bool:
        resource_added: bool = False
        ns = NS_19115_3

        distributions = root.xpath(
            "mdb:distributionInfo/mrd:MD_Distribution",
            namespaces=ns,
        )
        if not distributions:
            return resource_added
        distribution = distributions[0]

        transfer_options_parents = distribution.xpath("mrd:transferOptions", namespaces=ns)
        if transfer_options_parents:
            transfer_options_parent = transfer_options_parents[0]
        else:
            transfer_options_parent = etree.SubElement(
                distribution, f"{{{ns['mrd']}}}transferOptions"
            )

        digital_transfer_options_nodes = transfer_options_parent.xpath(
            "mrd:MD_DigitalTransferOptions", namespaces=ns
        )
        if digital_transfer_options_nodes:
            transfer_options = digital_transfer_options_nodes[0]
        else:
            transfer_options = etree.SubElement(
                transfer_options_parent, f"{{{ns['mrd']}}}MD_DigitalTransferOptions"
            )

        existing_protocols = set(
            transfer_options.xpath(
                "mrd:onLine/cit:CI_OnlineResource/cit:protocol/gco:CharacterString/text()",
                namespaces=ns,
            )
        )

        layer_name = layer_urls.get("layer_qualified_name", "")
        title_nodes = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification/mri:citation"
            "/cit:CI_Citation/cit:title/gco:CharacterString",
            namespaces=ns,
        )
        description = title_nodes[0].text if title_nodes and title_nodes[0].text else layer_name

        for key, protocol in _LAYER_URL_PROTOCOLS:
            if protocol in existing_protocols:
                continue
            resource_urls = layer_urls.get(key)
            if not resource_urls:
                continue
            linkage = resource_urls["base"] if isinstance(resource_urls, dict) else resource_urls

            online: _Element = etree.SubElement(transfer_options, f"{{{ns['mrd']}}}onLine")
            resource: _Element = etree.SubElement(online, f"{{{ns['cit']}}}CI_OnlineResource")

            linkage_el: _Element = etree.SubElement(resource, f"{{{ns['cit']}}}linkage")
            etree.SubElement(linkage_el, f"{{{ns['gco']}}}CharacterString").text = linkage

            protocol_el: _Element = etree.SubElement(resource, f"{{{ns['cit']}}}protocol")
            etree.SubElement(protocol_el, f"{{{ns['gco']}}}CharacterString").text = protocol

            name_el: _Element = etree.SubElement(resource, f"{{{ns['cit']}}}name")
            etree.SubElement(name_el, f"{{{ns['gco']}}}CharacterString").text = layer_name

            description_el: _Element = etree.SubElement(resource, f"{{{ns['cit']}}}description")
            etree.SubElement(description_el, f"{{{ns['gco']}}}CharacterString").text = description

            function_el: _Element = etree.SubElement(resource, f"{{{ns['cit']}}}function")
            etree.SubElement(
                function_el,
                f"{{{ns['cit']}}}CI_OnLineFunctionCode",
                attrib={"codeList": _ONLINE_FUNCTION_CODELIST_URL, "codeListValue": "download"},
            ).text = "download"
            resource_added = True
        return resource_added


ISO_19115_3_SCHEMA = Iso19115_3Schema()
