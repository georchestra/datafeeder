from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from geonetwork import GnApi  # type: ignore[import-untyped]
from lxml import etree  # type: ignore[import-untyped]

from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink

logger = get_logger()


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

    def generate_metadata(
        self,
        integrity_link: IntegrityLink,
        user_email: str = "",
        user_first_name: str = "",
        user_last_name: str = "",
    ) -> str:
        """Generate ISO 19115-3 metadata XML from IntegrityLink.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name

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

        # Build individual name from first + last name, fallback to username
        if user_first_name or user_last_name:
            individual_name = f"{user_first_name} {user_last_name}".strip()
        else:
            individual_name = integrity_link.integrity_owner

        # Dataset responsible party (owner)
        dataset_party = etree.SubElement(props, "datasetResponsibleParty")
        etree.SubElement(dataset_party, "individualName").text = individual_name
        etree.SubElement(
            dataset_party, "organizationName"
        ).text = integrity_link.integrity_organization
        # Add email if available
        if user_email:
            etree.SubElement(dataset_party, "email").text = user_email

        # Metadata responsible party (same as dataset owner)
        metadata_party = etree.SubElement(props, "metadataResponsibleParty")
        etree.SubElement(metadata_party, "individualName").text = individual_name
        etree.SubElement(
            metadata_party, "organizationName"
        ).text = integrity_link.integrity_organization
        # Add email if available
        if user_email:
            etree.SubElement(metadata_party, "email").text = user_email

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
        root = xml_doc.getroot()

        # Embed props into the XML document (XSLT parameters can't be node-sets)
        root.insert(0, props)

        xslt_doc = etree.parse(self.xslt_path)
        transform = etree.XSLT(xslt_doc)

        result = transform(xml_doc)
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
        try:
            response = self.gn_api.upload_metadata(
                metadata=metadata_xml,
                groupid=group_id,
                uuidprocessing="GENERATEUUID",
                publish=publish,
            )

            # Parse JSON response and extract UUID
            response_data = response.json()
            metadata_uuid: str = response_data.get("uuid") or response_data.get("id")  # type: ignore[assignment]
            logger.info(f"Published metadata with UUID: {metadata_uuid}")
        except Exception as e:
            logger.error(f"Failed to publish metadata: {e}", exc_info=True)
            raise
        return metadata_uuid

    def create_and_publish_metadata(
        self,
        integrity_link: IntegrityLink,
        user_email: str = "",
        user_first_name: str = "",
        user_last_name: str = "",
    ) -> str:
        """Generate and publish metadata in one operation.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name

        Returns:
            Metadata UUID from GeoNetwork
        """
        metadata_xml = self.generate_metadata(
            integrity_link,
            user_email=user_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
        )
        return self.publish_metadata(metadata_xml)
