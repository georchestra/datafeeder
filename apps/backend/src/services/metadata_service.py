from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from geonetwork import GnApi  # type: ignore[import-untyped]
from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import (
        XSLT,
        _Element,  # pyright: ignore[reportPrivateUsage]
        _ElementTree,  # pyright: ignore[reportPrivateUsage]
        _XSLTResultTree,  # pyright: ignore[reportPrivateUsage]
    )

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
        self.gn_api: Any = GnApi(api_url=gn_api_url, credentials=credentials, verifytls=verify_tls)
        self.template_path: str = f"{datadir_path}/datakern/metadata_template-19115-3.xml"
        self.xslt_path: str = f"{datadir_path}/datakern/metadata_transform-19115-3.xsl"

    def generate_metadata(
        self,
        integrity_link: IntegrityLink,
        user_email: str = "",
        user_first_name: str = "",
        user_last_name: str = "",
        layer_urls: dict[str, Any] | None = None,
    ) -> str:
        """Generate ISO 19115-3 metadata XML from IntegrityLink.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name
            layer_urls: Optional dictionary containing WMS/WFS URLs from GeoServer layer

        Returns:
            Generated metadata XML as string
        """
        # Build properties XML for XSLT transformation
        props: _Element = etree.Element("properties")

        # Use IntegrityLink ID as metadata UUID
        etree.SubElement(props, "metadataId").text = str(integrity_link.id)

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
        dataset_party: _Element = etree.SubElement(props, "datasetResponsibleParty")
        etree.SubElement(dataset_party, "individualName").text = individual_name
        etree.SubElement(
            dataset_party, "organizationName"
        ).text = integrity_link.integrity_organization
        # Add email if available
        if user_email:
            etree.SubElement(dataset_party, "email").text = user_email

        # Metadata responsible party (same as dataset owner)
        metadata_party: _Element = etree.SubElement(props, "metadataResponsibleParty")
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
        keywords: _Element = etree.SubElement(props, "keywords")
        etree.SubElement(keywords, "keyword").text = integrity_link.integrity_title or "dataset"

        layer_name = ""
        online_resources: _Element = etree.SubElement(props, "onlineResources")

        if layer_urls:
            layer_name = layer_urls.get("layer_qualified_name", "")

        # Build online resources from GeoServer layer URLs
        if layer_urls and "wms" in layer_urls and layer_urls["wms"]:
            wms = layer_urls["wms"]

            # WMS GetCapabilities
            resource: _Element = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = wms.get("capabilities", "")
            etree.SubElement(resource, "protocol").text = "OGC:WMS"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = "WMS GetCapabilities"

            # WMS GetMap
            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = wms.get("getmap", "")
            etree.SubElement(resource, "protocol").text = "OGC:WMS"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = "WMS GetMap"

        if layer_urls and "wfs" in layer_urls:
            wfs = layer_urls["wfs"]

            # WFS GetCapabilities
            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = wfs.get("capabilities", "")
            etree.SubElement(resource, "protocol").text = "OGC:WFS"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = "WFS GetCapabilities"

            # WFS GetFeature
            # ignore GetFeature for now

        if layer_urls and "ogcfeatures" in layer_urls:
            ogcfeatures = layer_urls["ogcfeatures"]

            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = ogcfeatures
            etree.SubElement(resource, "protocol").text = "OGC API Features"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = "OGC API Features"

        # Lineage
        etree.SubElement(
            props, "lineage"
        ).text = f"Imported from staging table {integrity_link.staging_table_name}"

        # Apply XSLT transformation
        xml_doc: _ElementTree = etree.parse(self.template_path)
        root: _Element = xml_doc.getroot()

        # Embed props into the XML document (XSLT parameters can't be node-sets)
        root.insert(0, props)

        xslt_doc: _ElementTree = etree.parse(self.xslt_path)
        transform: XSLT = etree.XSLT(xslt_doc)

        result: _XSLTResultTree = transform(xml_doc)
        return str(etree.tostring(result, encoding="unicode"))

    def publish_metadata(
        self, metadata_xml: str, group_id: str = "100", publish: bool = False
    ) -> str:
        """Publish metadata to GeoNetwork.

        Args:
            metadata_xml: ISO 19115-3 metadata XML string
            group_id: GeoNetwork group ID (default: '100' = public)
            publish: Whether to publish the metadata publicly (default: False = private, owner only)

        Returns:
            Metadata UUID from GeoNetwork
        """
        try:
            response: Any = self.gn_api.upload_metadata(
                metadata=metadata_xml,
                groupid=group_id,
                uuidprocessing="OVERWRITE",
                publish=publish,
            )

            # Parse JSON response and extract UUID
            response_data: Any = response.json()
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
        layer_urls: dict[str, Any] | None = None,
    ) -> str:
        """Generate and publish metadata in one operation.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name
            layer_urls: Optional dictionary containing WMS/WFS URLs from GeoServer layer

        Returns:
            Metadata UUID from GeoNetwork
        """
        metadata_xml = self.generate_metadata(
            integrity_link,
            user_email=user_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            layer_urls=layer_urls,
        )
        return self.publish_metadata(metadata_xml)

    def set_record_ownership(self, metadata_uuid: str, username: str, group_name: str) -> None:
        """Set ownership of a GeoNetwork metadata record.

        Queries all GN users/groups to find IDs by name, then sets ownership.

        Args:
            metadata_uuid: UUID of the published metadata record
            username: Owner username to match in GeoNetwork
            group_name: Group name to match in GeoNetwork
        """
        session = self.gn_api.session

        # 1. Find user ID by username
        resp = session.get(f"{self.gn_api.api_url}/users")
        resp.raise_for_status()
        users = resp.json()
        user_id = next((u["id"] for u in users if u["username"] == username), None)

        # 2. Find group ID by name (case-insensitive)
        resp = session.get(f"{self.gn_api.api_url}/groups")
        resp.raise_for_status()
        groups = resp.json()
        group_id = next(
            (g["id"] for g in groups if g["name"].lower() == group_name.lower()),
            None,
        )

        if user_id is None or group_id is None:
            logger.warning(
                "Cannot set ownership: user '%s' (id=%s) and/or group '%s' (id=%s) not found in GeoNetwork",
                username,
                user_id,
                group_name,
                group_id,
            )
            return

        # 3. Set ownership
        resp = session.put(
            f"{self.gn_api.api_url}/records/{metadata_uuid}/ownership",
            params={"groupIdentifier": group_id, "userIdentifier": user_id},
        )
        resp.raise_for_status()
        logger.info(
            "Set metadata %s ownership to user=%s (id=%s), group=%s (id=%s)",
            metadata_uuid,
            username,
            user_id,
            group_name,
            group_id,
        )
