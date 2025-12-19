from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from geonetwork import GnApi  # type: ignore[import-untyped]
from lxml import etree  # type: ignore[import-untyped]

from src.models.integrity_link import IntegrityLink


class MetadataService:
    """Service to generate and publish ISO 19115-3 metadata to GeoNetwork."""

    def __init__(
        self, gn_api_url: str, datadir_path: str, credentials: Any = None, verify_tls: bool = False
    ):
        """Initialize with GeoNetwork API client and paths to metadata files.

        Args:
            gn_api_url: GeoNetwork API URL (e.g., http://geonetwork:8080/geonetwork/srv/api)
            datadir_path: Path to datadir (e.g., /etc/georchestra)
            credentials: Optional GnApi credentials
            verify_tls: Whether to verify TLS certificates
        """
        self.gn_api = GnApi(api_url=gn_api_url, credentials=credentials, verifytls=verify_tls)
        self.template_path = f"{datadir_path}/datakern/metadata_template-19115-3.xml"
        self.xslt_path = f"{datadir_path}/datakern/metadata_transform-19115-3.xsl"

    def generate_metadata(self, integrity_link: IntegrityLink) -> str:
        """Generate ISO 19115-3 metadata XML from IntegrityLink.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata

        Returns:
            Generated metadata XML as string
        """
        # Build properties XML for XSLT transformation
        props = etree.Element("properties")

        # Generate new UUID for metadata
        etree.SubElement(props, "metadataId").text = str(uuid4())

        # Core properties from IntegrityLink
        etree.SubElement(props, "title").text = integrity_link.integrity_title or "Untitled Dataset"
        etree.SubElement(
            props, "abstract"
        ).text = f"Dataset imported via DataKern: {integrity_link.integrity_title or 'Untitled'}"

        # Dataset responsible party (owner)
        dataset_party = etree.SubElement(props, "datasetResponsibleParty")
        etree.SubElement(dataset_party, "individualName").text = integrity_link.integrity_owner
        etree.SubElement(
            dataset_party, "organizationName"
        ).text = integrity_link.integrity_organization

        # Metadata responsible party (same as dataset owner)
        metadata_party = etree.SubElement(props, "metadataResponsibleParty")
        etree.SubElement(metadata_party, "individualName").text = integrity_link.integrity_owner
        etree.SubElement(
            metadata_party, "organizationName"
        ).text = integrity_link.integrity_organization

        # Dates
        created_at = integrity_link.created_at or datetime.now(timezone.utc)
        last_retrieval = integrity_link.last_retrieval_timestamp or datetime.now(timezone.utc)

        etree.SubElement(props, "creationDate").text = created_at.strftime("%Y-%m-%d")
        etree.SubElement(props, "metadataPublicationDate").text = last_retrieval.strftime(
            "%Y-%m-%d"
        )

        # Keywords (use title as keyword)
        keywords = etree.SubElement(props, "keywords")
        etree.SubElement(keywords, "keyword").text = integrity_link.integrity_title or "dataset"

        # Lineage
        etree.SubElement(
            props, "lineage"
        ).text = f"Imported from staging table {integrity_link.staging_table_name}"

        # Apply XSLT transformation
        xml_doc = etree.parse(self.template_path)
        xslt_doc = etree.parse(self.xslt_path)
        transform = etree.XSLT(xslt_doc)

        result = transform(xml_doc, props=props)
        return etree.tostring(result, encoding="unicode")

    def publish_metadata(
        self, metadata_xml: str, group_id: str = "100", publish: bool = True
    ) -> str:
        """Publish metadata to GeoNetwork.

        Args:
            metadata_xml: ISO 19115-3 metadata XML string
            group_id: GeoNetwork group ID (default: '100' = public)
            publish: Whether to publish the metadata

        Returns:
            Metadata UUID from GeoNetwork
        """
        response = self.gn_api.upload_metadata(
            metadata=metadata_xml, groupid=group_id, uuidprocessing="GENERATEUUID", publish=publish
        )

        # Extract UUID from response
        metadata_uuid: str = response.get("uuid") or response.get("id")  # type: ignore[assignment]
        return metadata_uuid

    def create_and_publish_metadata(self, integrity_link: IntegrityLink) -> str:
        """Generate and publish metadata in one operation.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata

        Returns:
            Metadata UUID from GeoNetwork
        """
        metadata_xml = self.generate_metadata(integrity_link)
        return self.publish_metadata(metadata_xml)
