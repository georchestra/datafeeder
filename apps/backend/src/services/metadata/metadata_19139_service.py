from __future__ import annotations

from typing import TYPE_CHECKING

from ai.metadata_generator_models import AttributeInfo, TemporalExtent
from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

NS_19139 = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


class Metadata19139Service:
    """ISO 19139 XML patch operations."""

    @staticmethod
    def get_id_info(root: _Element) -> _Element | None:
        id_info_list = root.xpath(
            "gmd:identificationInfo/gmd:MD_DataIdentification",
            namespaces=NS_19139,
        )
        if not id_info_list:
            return None
        return id_info_list[0]

    @staticmethod
    def patch_title(id_info: _Element, title: str) -> None:
        title_els = id_info.xpath(
            "gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString", namespaces=NS_19139
        )
        if title_els:
            title_els[0].text = title

    @staticmethod
    def patch_abstract(id_info: _Element, abstract: str) -> None:
        abstract_els = id_info.xpath("gmd:abstract/gco:CharacterString", namespaces=NS_19139)
        if abstract_els:
            abstract_els[0].text = abstract
            return

        wrapper: _Element = etree.SubElement(id_info, f"{{{NS_19139['gmd']}}}abstract")
        etree.SubElement(wrapper, f"{{{NS_19139['gco']}}}CharacterString").text = abstract

    @staticmethod
    def patch_keywords(
        id_info: _Element, keywords: list[str], generate_by_ai: bool = False
    ) -> None:
        ns_gmd = NS_19139["gmd"]
        ns_gco = NS_19139["gco"]

        Metadata19139Service.remove_keywords_block(id_info)

        desc_kw: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}descriptiveKeywords")
        md_kw: _Element = etree.SubElement(desc_kw, f"{{{ns_gmd}}}MD_Keywords")
        for kw in keywords:
            kw_el: _Element = etree.SubElement(md_kw, f"{{{ns_gmd}}}keyword")
            etree.SubElement(kw_el, f"{{{ns_gco}}}CharacterString").text = kw

        if generate_by_ai:
            Metadata19139Service.patch_keywords_citation(md_kw, "ai-keywords-generated")

    @staticmethod
    def patch_keywords_citation(md_kw: _Element, citation_text: str) -> None:
        ns_gmd = NS_19139["gmd"]
        ns_gco = NS_19139["gco"]
        thesaurus_name_el: _Element = etree.SubElement(md_kw, f"{{{ns_gmd}}}thesaurusName")
        ci_citation: _Element = etree.SubElement(thesaurus_name_el, f"{{{ns_gmd}}}CI_Citation")
        title_el: _Element = etree.SubElement(ci_citation, f"{{{ns_gmd}}}title")
        etree.SubElement(title_el, f"{{{ns_gco}}}CharacterString").text = citation_text

    @staticmethod
    def remove_keywords_block(id_info: _Element) -> None:
        for block in id_info.xpath("gmd:descriptiveKeywords", namespaces=NS_19139):
            id_info.remove(block)

    @staticmethod
    def patch_topic_categories(id_info: _Element, topic_categories: list[str]) -> None:
        ns_gmd = NS_19139["gmd"]
        for tc in id_info.xpath("gmd:topicCategory", namespaces=NS_19139):
            id_info.remove(tc)
        for cat in topic_categories:
            topic_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}topicCategory")
            etree.SubElement(topic_wrapper, f"{{{ns_gmd}}}MD_TopicCategoryCode").text = cat

    @staticmethod
    def patch_attribute_catalogue(
        root: _Element,
        attribute_descriptions: list[AttributeInfo],
        table_name: str = "",
    ) -> None:
        ns_gmd = NS_19139["gmd"]
        ns_gco = NS_19139["gco"]
        ns_gfc = "http://www.isotc211.org/2005/gfc"

        for block in root.xpath("gmd:contentInfo", namespaces=NS_19139):
            anchor = block.xpath(
                ".//gfc:FC_FeatureCatalogue/gfc:name/gco:CharacterString[. = 'datafeeder-generated']",
                namespaces={**NS_19139, "gfc": ns_gfc},
            )
            if anchor:
                root.remove(block)

        content_info: _Element = etree.SubElement(root, f"{{{ns_gmd}}}contentInfo")
        fc: _Element = etree.SubElement(content_info, f"{{{ns_gfc}}}FC_FeatureCatalogue")

        name_el: _Element = etree.SubElement(fc, f"{{{ns_gfc}}}name")
        etree.SubElement(name_el, f"{{{ns_gco}}}CharacterString").text = "datafeeder-generated"
        ver_el: _Element = etree.SubElement(fc, f"{{{ns_gfc}}}versionNumber")
        etree.SubElement(ver_el, f"{{{ns_gco}}}CharacterString").text = "1.0"

        ft_wrapper: _Element = etree.SubElement(fc, f"{{{ns_gfc}}}featureType")
        fc_ft: _Element = etree.SubElement(ft_wrapper, f"{{{ns_gfc}}}FC_FeatureType")

        tn_el: _Element = etree.SubElement(fc_ft, f"{{{ns_gfc}}}typeName")
        tn_el.text = table_name or "dataset"
        ia_el: _Element = etree.SubElement(fc_ft, f"{{{ns_gfc}}}isAbstract")
        etree.SubElement(ia_el, f"{{{ns_gco}}}Boolean").text = "false"

        for attr in attribute_descriptions:
            coc: _Element = etree.SubElement(fc_ft, f"{{{ns_gfc}}}carrierOfCharacteristics")
            fa: _Element = etree.SubElement(coc, f"{{{ns_gfc}}}FC_FeatureAttribute")

            mn: _Element = etree.SubElement(fa, f"{{{ns_gfc}}}memberName")
            mn.text = attr.name

            defn: _Element = etree.SubElement(fa, f"{{{ns_gfc}}}definition")
            etree.SubElement(defn, f"{{{ns_gco}}}CharacterString").text = attr.description

            card: _Element = etree.SubElement(fa, f"{{{ns_gfc}}}cardinality")
            etree.SubElement(card, f"{{{ns_gco}}}CharacterString").text = "0..1"

            code_el: _Element = etree.SubElement(fa, f"{{{ns_gfc}}}code")
            etree.SubElement(code_el, f"{{{ns_gco}}}CharacterString").text = attr.name

            vt: _Element = etree.SubElement(fa, f"{{{ns_gfc}}}valueType")
            type_name: _Element = etree.SubElement(vt, f"{{{ns_gco}}}TypeName")
            aname: _Element = etree.SubElement(type_name, f"{{{ns_gco}}}aName")
            etree.SubElement(aname, f"{{{ns_gco}}}CharacterString").text = attr.type

    @staticmethod
    def patch_temporal_extent(root: _Element, temporal_extent: TemporalExtent) -> None:
        ns_gmd = NS_19139["gmd"]
        ns_gco = NS_19139["gco"]
        ns_gml = "http://www.opengis.net/gml/3.2"

        id_info_list = root.xpath(
            "gmd:identificationInfo/gmd:MD_DataIdentification", namespaces=NS_19139
        )
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        for extent_el in id_info.xpath("gmd:extent", namespaces=NS_19139):
            if extent_el.xpath(
                ".//gmd:temporalElement//gco:CharacterString[contains(., 'datafeeder-generated-temporal')]",
                namespaces=NS_19139,
            ):
                id_info.remove(extent_el)

        extent_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}extent")
        ex_extent: _Element = etree.SubElement(extent_wrapper, f"{{{ns_gmd}}}EX_Extent")

        desc_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gmd}}}description")
        etree.SubElement(
            desc_el, f"{{{ns_gco}}}CharacterString"
        ).text = "datafeeder-generated-temporal"

        temporal_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gmd}}}temporalElement")
        ex_temporal: _Element = etree.SubElement(temporal_el, f"{{{ns_gmd}}}EX_TemporalExtent")
        extent_inner: _Element = etree.SubElement(ex_temporal, f"{{{ns_gmd}}}extent")

        if temporal_extent.type == "period":
            time_el: _Element = etree.SubElement(extent_inner, f"{{{ns_gml}}}TimePeriod")
            time_el.set(f"{{{ns_gml}}}id", "ai-temporal-period")
            begin_el: _Element = etree.SubElement(time_el, f"{{{ns_gml}}}beginPosition")
            begin_el.text = temporal_extent.begin or ""
            if not temporal_extent.begin:
                begin_el.set("indeterminatePosition", "unknown")
            end_el: _Element = etree.SubElement(time_el, f"{{{ns_gml}}}endPosition")
            end_el.text = temporal_extent.end or ""
            if not temporal_extent.end:
                end_el.set("indeterminatePosition", "unknown")
        else:
            time_el = etree.SubElement(extent_inner, f"{{{ns_gml}}}TimeInstant")
            time_el.set(f"{{{ns_gml}}}id", "ai-temporal-instant")
            pos_el: _Element = etree.SubElement(time_el, f"{{{ns_gml}}}timePosition")
            pos_el.text = temporal_extent.instant or temporal_extent.begin or ""
