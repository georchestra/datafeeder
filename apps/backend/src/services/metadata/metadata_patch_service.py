from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai.metadata_generator_models import AttributeInfo, TemporalExtent

from src.services.metadata.metadata_19115_3_service import Metadata191153Service
from src.services.metadata.metadata_19139_service import Metadata19139Service

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

_SCHEMA_19115_3 = "19115-3"
_SCHEMA_19139 = "19139"


class MetadataPatchService:
    """Service focused on in-place metadata XML patch operations."""

    def __init__(self, gn_api: Any):
        self.gn_api = gn_api

    @staticmethod
    def get_schema(root: _Element) -> str | None:
        """Detect the ISO metadata schema from the root element's namespace tag.

        Inspects the root element's namespace URI to determine which ISO standard
        the metadata follows:
        - ISO 19115-3: http://standards.iso.org/iso/19115/-3/mdb/2.0
        - ISO 19139: http://www.isotc211.org/2005/gmd

        Args:
            root: The root element of the metadata XML document.

        Returns:
            Schema identifier string ("19115-3" or "19139"), or None if unsupported.
        """
        tag = str(root.tag)
        if "http://standards.iso.org/iso/19115/-3/mdb/2.0" in tag:
            return _SCHEMA_19115_3
        if "http://www.isotc211.org/2005/gmd" in tag:
            return _SCHEMA_19139
        return None

    @staticmethod
    def detect_schema(root: _Element) -> str | None:
        """Backward-compatible alias for get_schema."""
        return MetadataPatchService.get_schema(root)

    @staticmethod
    def get_id_info(root: _Element, schema: str) -> _Element | None:
        """Get the ID info element for the given schema.

        Args:
            root: The root element of the metadata XML document.
            schema: Schema identifier ("19115-3" or "19139").

        Returns:
            The MD_DataIdentification element or None if not found.
        """
        if schema == _SCHEMA_19115_3:
            return Metadata191153Service.get_id_info(root)
        if schema == _SCHEMA_19139:
            return Metadata19139Service.get_id_info(root)
        return None

    @staticmethod
    def patch_abstract(schema: str, id_info: _Element, abstract: str) -> None:
        """Patch abstract for the given schema and id_info element.

        Args:
            schema: Schema identifier ("19115-3" or "19139").
            id_info: The MD_DataIdentification element.
            abstract: The abstract text to set.
        """
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_abstract(id_info, abstract)
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_abstract(id_info, abstract)

    @staticmethod
    def patch_title(schema: str, id_info: _Element, title: str) -> None:
        """Patch title for the given schema and id_info element.

        Args:
            schema: Schema identifier ("19115-3" or "19139").
            id_info: The MD_DataIdentification element.
            title: The title text to set.
        """
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_title(id_info, title)
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_title(id_info, title)

    @staticmethod
    def patch_keywords(
        schema: str,
        id_info: _Element,
        keywords: list[str],
        generate_by_ai: bool = False,
    ) -> None:
        """Patch keywords for the given schema and id_info element.

        Args:
            schema: Schema identifier ("19115-3" or "19139").
            id_info: The MD_DataIdentification element.
            keywords: List of keyword strings to set.
            generate_by_ai: Whether to mark keywords with AI generation marker.
        """
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_keywords(id_info, keywords, generate_by_ai=generate_by_ai)
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_keywords(id_info, keywords, generate_by_ai=generate_by_ai)

    @staticmethod
    def patch_topic_categories(
        schema: str,
        id_info: _Element,
        topic_categories: list[str],
    ) -> None:
        """Patch topic categories for the given schema and id_info element.

        Args:
            schema: Schema identifier ("19115-3" or "19139").
            id_info: The MD_DataIdentification element.
            topic_categories: List of topic category strings.
        """
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_topic_categories(id_info, topic_categories)
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_topic_categories(id_info, topic_categories)

    @staticmethod
    def patch_attribute_catalogue(
        schema: str | None,
        root: _Element,
        attribute_descriptions: list[AttributeInfo],
        table_name: str = "",
    ) -> None:
        """Patch attribute catalogue for the given schema.

        Args:
            schema: Schema identifier ("19115-3" or "19139"). If None, detected from root.
            root: The root element of the metadata XML document.
            attribute_descriptions: List of attribute metadata to inject.
            table_name: Table name for the feature catalogue.
        """
        if schema is None:
            schema = MetadataPatchService.get_schema(root)
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_attribute_catalogue(
                root,
                attribute_descriptions,
                table_name,
            )
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_attribute_catalogue(
                root,
                attribute_descriptions,
                table_name,
            )

    @staticmethod
    def patch_temporal_extent(
        schema: str | None,
        root: _Element,
        temporal_extent: TemporalExtent,
    ) -> None:
        """Patch temporal extent for the given schema.

        Args:
            schema: Schema identifier ("19115-3" or "19139"). If None, detected from root.
            root: The root element of the metadata XML document.
            temporal_extent: The temporal extent metadata to inject.
        """
        if schema is None:
            schema = MetadataPatchService.get_schema(root)
        if schema == _SCHEMA_19115_3:
            Metadata191153Service.patch_temporal_extent(root, temporal_extent)
        elif schema == _SCHEMA_19139:
            Metadata19139Service.patch_temporal_extent(root, temporal_extent)
