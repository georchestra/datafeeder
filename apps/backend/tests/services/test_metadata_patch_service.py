from __future__ import annotations

from ai.metadata_generator_models import AttributeInfo, TemporalExtent
from lxml import etree

from src.services.metadata.metadata_19115_3_service import NS_19115_3, Metadata191153Service
from src.services.metadata.metadata_19139_service import NS_19139, Metadata19139Service
from src.services.metadata.metadata_patch_service import MetadataPatchService


def _root_19115_3():
    return etree.fromstring(
        """
        <mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                         xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0"
                         xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                         xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0">
          <mdb:identificationInfo>
            <mri:MD_DataIdentification>
              <mri:citation>
                <cit:CI_Citation>
                  <cit:title><gco:CharacterString>Old title</gco:CharacterString></cit:title>
                </cit:CI_Citation>
              </mri:citation>
              <mri:abstract><gco:CharacterString>Old abstract</gco:CharacterString></mri:abstract>
              <mri:topicCategory><mri:MD_TopicCategoryCode>old</mri:MD_TopicCategoryCode></mri:topicCategory>
            </mri:MD_DataIdentification>
          </mdb:identificationInfo>
        </mdb:MD_Metadata>
        """
    )


def _root_19139():
    return etree.fromstring(
        """
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                         xmlns:gco="http://www.isotc211.org/2005/gco">
          <gmd:identificationInfo>
            <gmd:MD_DataIdentification>
              <gmd:citation>
                <gmd:CI_Citation>
                  <gmd:title><gco:CharacterString>Old title</gco:CharacterString></gmd:title>
                </gmd:CI_Citation>
              </gmd:citation>
              <gmd:abstract><gco:CharacterString>Old abstract</gco:CharacterString></gmd:abstract>
            </gmd:MD_DataIdentification>
          </gmd:identificationInfo>
        </gmd:MD_Metadata>
        """
    )


def test_detect_schema_recognizes_supported_namespaces() -> None:
    root_19115_3 = _root_19115_3()
    root_19139 = _root_19139()

    assert MetadataPatchService.detect_schema(root_19115_3) == "19115-3"
    assert MetadataPatchService.detect_schema(root_19139) == "19139"
    assert MetadataPatchService.detect_schema(etree.fromstring("<root />")) is None


def test_patch_19115_3_fields_updates_core_text_and_keywords() -> None:
    root = _root_19115_3()
    id_info = root.xpath("mdb:identificationInfo/mri:MD_DataIdentification", namespaces=NS_19115_3)[
        0
    ]

    Metadata191153Service.patch_title(id_info, "New title")
    Metadata191153Service.patch_abstract(id_info, "New abstract")
    Metadata191153Service.patch_keywords(id_info, ["water", "transport"], generate_by_ai=True)
    Metadata191153Service.patch_topic_categories(id_info, ["environment"])

    assert (
        root.xpath(
            "string(mdb:identificationInfo/mri:MD_DataIdentification/mri:citation/cit:CI_Citation/cit:title/gco:CharacterString)",
            namespaces=NS_19115_3,
        )
        == "New title"
    )
    assert (
        root.xpath(
            "string(mdb:identificationInfo/mri:MD_DataIdentification/mri:abstract/gco:CharacterString)",
            namespaces=NS_19115_3,
        )
        == "New abstract"
    )
    assert root.xpath(
        "mdb:identificationInfo/mri:MD_DataIdentification/mri:descriptiveKeywords"
        "/mri:MD_Keywords/mri:keyword/gco:CharacterString/text()",
        namespaces=NS_19115_3,
    ) == ["water", "transport"]
    assert (
        root.xpath(
            "string(mdb:identificationInfo/mri:MD_DataIdentification"
            "/mri:descriptiveKeywords/mri:MD_Keywords/mri:thesaurusName"
            "/cit:CI_Citation/cit:title/gco:CharacterString)",
            namespaces=NS_19115_3,
        )
        == "ai-keywords-generated"
    )
    assert root.xpath(
        "mdb:identificationInfo/mri:MD_DataIdentification/mri:topicCategory"
        "/mri:MD_TopicCategoryCode/text()",
        namespaces=NS_19115_3,
    ) == ["environment"]


def test_patch_attribute_catalogue_19115_3_inserts_feature_catalogue() -> None:
    root = _root_19115_3()

    Metadata191153Service.patch_attribute_catalogue(
        root,
        [AttributeInfo(name="population", type="integer", description="Population")],
        table_name="cities",
    )

    namespaces = {**NS_19115_3, "gfc": "http://standards.iso.org/iso/19110/gfc/1.1"}
    assert (
        root.xpath(
            "string(mdb:contentInfo/gfc:FC_FeatureCatalogue/gfc:name/gco:CharacterString)",
            namespaces=namespaces,
        )
        == "datafeeder-generated"
    )
    assert (
        root.xpath(
            "string(mdb:contentInfo/gfc:FC_FeatureCatalogue/gfc:featureType"
            "/gfc:FC_FeatureType/gfc:typeName)",
            namespaces=namespaces,
        )
        == "cities"
    )
    assert (
        root.xpath(
            "string(mdb:contentInfo/gfc:FC_FeatureCatalogue/gfc:featureType"
            "/gfc:FC_FeatureType/gfc:carrierOfCharacteristics"
            "/gfc:FC_FeatureAttribute/gfc:memberName)",
            namespaces=namespaces,
        )
        == "population"
    )


def test_patch_temporal_extent_19139_inserts_period_extent() -> None:
    root = _root_19139()

    Metadata19139Service.patch_temporal_extent(
        root,
        TemporalExtent(type="period", begin="2024-01-01", end="2024-12-31"),
    )

    namespaces = {**NS_19139, "gml": "http://www.opengis.net/gml/3.2"}
    assert (
        root.xpath(
            "string(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent"
            "/gmd:EX_Extent/gmd:description/gco:CharacterString)",
            namespaces=namespaces,
        )
        == "datafeeder-generated-temporal"
    )
    assert (
        root.xpath(
            "string(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent"
            "/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent"
            "/gmd:extent/gml:TimePeriod/gml:beginPosition)",
            namespaces=namespaces,
        )
        == "2024-01-01"
    )
    assert (
        root.xpath(
            "string(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent"
            "/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent"
            "/gmd:extent/gml:TimePeriod/gml:endPosition)",
            namespaces=namespaces,
        )
        == "2024-12-31"
    )


def test_patch_keywords_19115_3_with_generate_by_ai_true() -> None:
    """Test that keywords with generate_by_ai=True adds AI thesaurus marker."""
    root = _root_19115_3()
    id_info = root.xpath("mdb:identificationInfo/mri:MD_DataIdentification", namespaces=NS_19115_3)[
        0
    ]

    Metadata191153Service.patch_keywords(id_info, ["water", "transport"], generate_by_ai=True)

    assert (
        root.xpath(
            "string(mdb:identificationInfo/mri:MD_DataIdentification"
            "/mri:descriptiveKeywords/mri:MD_Keywords/mri:thesaurusName"
            "/cit:CI_Citation/cit:title/gco:CharacterString)",
            namespaces=NS_19115_3,
        )
        == "ai-keywords-generated"
    )


def test_patch_keywords_19115_3_with_generate_by_ai_false() -> None:
    """Test that keywords with generate_by_ai=False does NOT add AI thesaurus marker."""
    root = _root_19115_3()
    id_info = root.xpath("mdb:identificationInfo/mri:MD_DataIdentification", namespaces=NS_19115_3)[
        0
    ]

    Metadata191153Service.patch_keywords(id_info, ["water", "transport"], generate_by_ai=False)

    # Verify keywords are added
    assert root.xpath(
        "mdb:identificationInfo/mri:MD_DataIdentification/mri:descriptiveKeywords"
        "/mri:MD_Keywords/mri:keyword/gco:CharacterString/text()",
        namespaces=NS_19115_3,
    ) == ["water", "transport"]

    # Verify thesaurus marker is NOT present
    thesaurus_nodes = root.xpath(
        "mdb:identificationInfo/mri:MD_DataIdentification"
        "/mri:descriptiveKeywords/mri:MD_Keywords/mri:thesaurusName",
        namespaces=NS_19115_3,
    )
    assert len(thesaurus_nodes) == 0


def test_patch_keywords_19139_with_generate_by_ai_false() -> None:
    """Test that keywords with generate_by_ai=False does NOT add AI thesaurus marker."""
    root = _root_19139()
    id_info = root.xpath("gmd:identificationInfo/gmd:MD_DataIdentification", namespaces=NS_19139)[0]

    Metadata19139Service.patch_keywords(id_info, ["water", "transport"], generate_by_ai=False)

    # Verify keywords are added
    assert root.xpath(
        "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords"
        "/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
        namespaces=NS_19139,
    ) == ["water", "transport"]

    # Verify thesaurus marker is NOT present
    thesaurus_nodes = root.xpath(
        "gmd:identificationInfo/gmd:MD_DataIdentification"
        "/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName",
        namespaces=NS_19139,
    )
    assert len(thesaurus_nodes) == 0
