from __future__ import annotations

from typing import TYPE_CHECKING

from ai.metadata_generator_models import AttributeInfo, TemporalExtent
from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

NS_19115_3 = {
    "mdb": "http://standards.iso.org/iso/19115/-3/mdb/2.0",
    "mri": "http://standards.iso.org/iso/19115/-3/mri/1.0",
    "cit": "http://standards.iso.org/iso/19115/-3/cit/2.0",
    "gco": "http://standards.iso.org/iso/19115/-3/gco/1.0",
}


class Metadata191153Service:
    """ISO 19115-3 XML patch operations."""

    @staticmethod
    def get_id_info(root: _Element) -> _Element | None:
        id_info_list = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification",
            namespaces=NS_19115_3,
        )
        if not id_info_list:
            return None
        return id_info_list[0]

    @staticmethod
    def patch_title(id_info: _Element, title: str) -> None:
        title_els = id_info.xpath(
            "mri:citation/cit:CI_Citation/cit:title/gco:CharacterString", namespaces=NS_19115_3
        )
        if title_els:
            title_els[0].text = title

    @staticmethod
    def patch_abstract(id_info: _Element, abstract: str) -> None:
        abstract_els = id_info.xpath("mri:abstract/gco:CharacterString", namespaces=NS_19115_3)
        if abstract_els:
            abstract_els[0].text = abstract
            return

        abstract_wrapper: _Element = etree.SubElement(id_info, f"{{{NS_19115_3['mri']}}}abstract")
        etree.SubElement(
            abstract_wrapper, f"{{{NS_19115_3['gco']}}}CharacterString"
        ).text = abstract

    @staticmethod
    def patch_keywords(
        id_info: _Element, keywords: list[str], generate_by_ai: bool = False
    ) -> None:
        ns_mri = NS_19115_3["mri"]
        ns_gco = NS_19115_3["gco"]

        Metadata191153Service.remove_keywords_block(id_info)

        desc_kw: _Element = etree.SubElement(id_info, f"{{{ns_mri}}}descriptiveKeywords")
        md_kw: _Element = etree.SubElement(desc_kw, f"{{{ns_mri}}}MD_Keywords")
        for kw in keywords:
            kw_el: _Element = etree.SubElement(md_kw, f"{{{ns_mri}}}keyword")
            etree.SubElement(kw_el, f"{{{ns_gco}}}CharacterString").text = kw

        if generate_by_ai:
            Metadata191153Service.patch_keywords_citation(md_kw, "ai-keywords-generated")

    @staticmethod
    def patch_keywords_citation(md_kw: _Element, citation_text: str) -> None:
        ns_mri = NS_19115_3["mri"]
        ns_gco = NS_19115_3["gco"]
        thesaurus_name_el: _Element = etree.SubElement(md_kw, f"{{{ns_mri}}}thesaurusName")
        ci_citation: _Element = etree.SubElement(
            thesaurus_name_el, f"{{{NS_19115_3['cit']}}}CI_Citation"
        )
        title_el: _Element = etree.SubElement(ci_citation, f"{{{NS_19115_3['cit']}}}title")
        etree.SubElement(title_el, f"{{{ns_gco}}}CharacterString").text = citation_text

    @staticmethod
    def remove_keywords_block(id_info: _Element) -> None:
        existing_kw_blocks = id_info.xpath("mri:descriptiveKeywords", namespaces=NS_19115_3)
        for block in existing_kw_blocks:
            id_info.remove(block)

    @staticmethod
    def patch_topic_categories(id_info: _Element, topic_categories: list[str]) -> None:
        ns_mri_uri = f"{{{NS_19115_3['mri']}}}"
        for tc in id_info.xpath("mri:topicCategory", namespaces=NS_19115_3):
            id_info.remove(tc)
        for cat in topic_categories:
            topic_wrapper: _Element = etree.SubElement(id_info, f"{ns_mri_uri}topicCategory")
            etree.SubElement(topic_wrapper, f"{ns_mri_uri}MD_TopicCategoryCode").text = cat

    @staticmethod
    def patch_attribute_catalogue(
        root: _Element,
        attribute_descriptions: list[AttributeInfo],
        table_name: str = "",
    ) -> None:
        ns_mdb = NS_19115_3["mdb"]
        ns_gco = NS_19115_3["gco"]
        ns_gfc = "http://standards.iso.org/iso/19110/gfc/1.1"

        for block in root.xpath("mdb:contentInfo", namespaces=NS_19115_3):
            anchor = block.xpath(
                ".//gfc:FC_FeatureCatalogue/gfc:name/gco:CharacterString[. = 'datafeeder-generated']",
                namespaces={**NS_19115_3, "gfc": ns_gfc},
            )
            if anchor:
                root.remove(block)

        content_info: _Element = etree.SubElement(root, f"{{{ns_mdb}}}contentInfo")
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
        ns_mri = NS_19115_3["mri"]
        ns_gex = "http://standards.iso.org/iso/19115/-3/gex/1.0"
        ns_gml = "http://www.opengis.net/gml/3.2"

        id_info_list = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification", namespaces=NS_19115_3
        )
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        for extent_el in id_info.xpath("mri:extent", namespaces=NS_19115_3):
            if extent_el.xpath(
                ".//gex:temporalElement//gco:CharacterString[contains(., 'datafeeder-generated-temporal')]",
                namespaces={**NS_19115_3, "gex": ns_gex},
            ):
                id_info.remove(extent_el)

        extent_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_mri}}}extent")
        ex_extent: _Element = etree.SubElement(extent_wrapper, f"{{{ns_gex}}}EX_Extent")

        desc_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gex}}}description")
        etree.SubElement(
            desc_el, f"{{{NS_19115_3['gco']}}}CharacterString"
        ).text = "datafeeder-generated-temporal"

        temporal_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gex}}}temporalElement")
        ex_temporal: _Element = etree.SubElement(temporal_el, f"{{{ns_gex}}}EX_TemporalExtent")
        extent_inner: _Element = etree.SubElement(ex_temporal, f"{{{ns_gex}}}extent")

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
