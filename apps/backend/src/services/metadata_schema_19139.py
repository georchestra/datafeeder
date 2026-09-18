from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

from src.services.metadata_schema import MetadataSchema

NS_19139 = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}

RESOURCE_TITLE_XPATH_19139 = "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:description/gco:CharacterString"


class Iso19139Schema(MetadataSchema):
    def update_revision_date(self, revision_date: datetime) -> None:
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        ns = NS_19139
        codelist_19139 = (
            "http://standards.iso.org/iso/19139/resources/codelist/gmxCodelists.xml#CI_DateTypeCode"
        )

        citations = self.root.xpath(
            "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation",
            namespaces=ns,
        )
        for citation in citations:
            existing = citation.xpath(
                "gmd:date/gmd:CI_Date[gmd:dateType/gmd:CI_DateTypeCode"
                "/@codeListValue='revision']/gmd:date/*[self::gco:DateTime or self::gco:Date]",
                namespaces=ns,
            )
            if existing:
                date_node = existing[0]
                date_node.tag = f"{{{ns['gco']}}}DateTime"
                date_node.text = date_str
            else:
                date_wrapper: _Element = etree.SubElement(citation, f"{{{ns['gmd']}}}date")
                ci_date_el: _Element = etree.SubElement(date_wrapper, f"{{{ns['gmd']}}}CI_Date")
                d_el: _Element = etree.SubElement(ci_date_el, f"{{{ns['gmd']}}}date")
                etree.SubElement(d_el, f"{{{ns['gco']}}}DateTime").text = date_str
                dt_el: _Element = etree.SubElement(ci_date_el, f"{{{ns['gmd']}}}dateType")
                etree.SubElement(
                    dt_el,
                    f"{{{ns['gmd']}}}CI_DateTypeCode",
                    attrib={"codeList": codelist_19139, "codeListValue": "revision"},
                ).text = "revision"
            self.updated = True

    def get_title(self) -> str | None:
        nodes = self.root.xpath(
            "gmd:identificationInfo/gmd:MD_DataIdentification"
            "/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString",
            namespaces=NS_19139,
        )
        return nodes[0].text if nodes and nodes[0].text else None

    def update_online_resources_when_title_changed(self, title: str) -> None:
        for online in self.root.xpath(RESOURCE_TITLE_XPATH_19139, namespaces=NS_19139):
            if online.text != title:
                online.text = title
                self.updated = True
