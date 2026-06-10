from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ai.metadata_generator import AttributeInfo, TemporalExtent  # type: ignore[import-untyped]
from geonetwork import GnApi  # type: ignore[import-untyped]
from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import (
        XSLT,
        _Element,  # pyright: ignore[reportPrivateUsage]
        _ElementTree,  # pyright: ignore[reportPrivateUsage]
        _XSLTResultTree,  # pyright: ignore[reportPrivateUsage]
    )

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import RuleValue

logger = get_logger()

# ISO schema identifiers used for metadata record detection
_SCHEMA_19115_3 = "19115-3"
_SCHEMA_19139 = "19139"

NS_19115_3 = {
    "mdb": "http://standards.iso.org/iso/19115/-3/mdb/2.0",
    "mri": "http://standards.iso.org/iso/19115/-3/mri/1.0",
    "cit": "http://standards.iso.org/iso/19115/-3/cit/2.0",
    "gco": "http://standards.iso.org/iso/19115/-3/gco/1.0",
}

NS_19139 = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}

_CODELIST_URL = (
    "http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CI_DateTypeCode"
)


class MetadataService:
    """Service to generate and publish ISO 19115-3 metadata to GeoNetwork."""

    def __init__(
        self,
        gn_api_url: str,
        datadir_path: str,
        credentials: Any = None,
        verify_tls: bool = False,
        gn_sync_mode: str = "ORG",
        metadata_default_group_name: str = "sample",
    ):
        """Initialize with GeoNetwork API client and paths to metadata files.

        Args:
            gn_api_url: GeoNetwork API URL (e.g., http://geonetwork:8080/geonetwork/srv/api)
            datadir_path: Path to datadir (e.g., /etc/georchestra)
            credentials: Optional GnApi credentials
            verify_tls: Whether to verify TLS certificates
            gn_sync_mode: "ORG" to resolve group by org name; "ROLE" to use user's GN memberships
            metadata_default_group_name: Fallback group name when user has no non-system groups
        """
        self.gn_api: Any = GnApi(api_url=gn_api_url, credentials=credentials, verifytls=verify_tls)
        self.template_path: str = f"{datadir_path}/datafeeder-python/metadata_template-19115-3.xml"
        self.xslt_path: str = f"{datadir_path}/datafeeder-python/metadata_transform-19115-3.xsl"
        self.org_based_sync: bool = gn_sync_mode == "ORG"
        self.metadata_default_group_name: str = metadata_default_group_name

    def generate_metadata(
        self,
        integrity_link: IntegrityLink,
        user_email: str = "",
        user_first_name: str = "",
        user_last_name: str = "",
        organization_name: str = "",
        layer_urls: dict[str, Any] | None = None,
    ) -> str:
        """Generate ISO 19115-3 metadata XML from IntegrityLink.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name
            organization_name: Long display name of the organization (falls back to integrity_organization)
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
        etree.SubElement(props, "abstract").text = ""

        # Build individual name from first + last name, fallback to username
        if user_first_name or user_last_name:
            individual_name = f"{user_first_name} {user_last_name}".strip()
        else:
            individual_name = integrity_link.integrity_owner

        org_display_name = organization_name or integrity_link.integrity_organization

        # Dataset responsible party (owner)
        dataset_party: _Element = etree.SubElement(props, "datasetResponsibleParty")
        etree.SubElement(dataset_party, "individualName").text = individual_name
        etree.SubElement(dataset_party, "organizationName").text = org_display_name
        # Add email if available
        if user_email:
            etree.SubElement(dataset_party, "email").text = user_email

        # Metadata responsible party (same as dataset owner)
        metadata_party: _Element = etree.SubElement(props, "metadataResponsibleParty")
        etree.SubElement(metadata_party, "individualName").text = individual_name
        etree.SubElement(metadata_party, "organizationName").text = org_display_name
        # Add email if available
        if user_email:
            etree.SubElement(metadata_party, "email").text = user_email

        # Dates
        created_at = integrity_link.created_at or datetime.now(timezone.utc)
        last_retrieval = integrity_link.last_retrieval_timestamp or datetime.now(timezone.utc)

        etree.SubElement(props, "creationDate").text = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        etree.SubElement(props, "metadataPublicationDate").text = last_retrieval.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        layer_name = ""
        online_resources: _Element = etree.SubElement(props, "onlineResources")

        if layer_urls:
            layer_name = layer_urls.get("layer_qualified_name", "")

        if layer_urls and "ogcfeatures" in layer_urls:
            ogcfeatures = layer_urls["ogcfeatures"]

            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = ogcfeatures
            etree.SubElement(resource, "protocol").text = "OGC API Features"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = (
                integrity_link.integrity_title or "Untitled Dataset"
            )

        # Build online resources from GeoServer layer URLs
        if layer_urls and "wms" in layer_urls and layer_urls["wms"]:
            wms = layer_urls["wms"]

            # WMS
            resource: _Element = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = wms.get("base", "")
            etree.SubElement(resource, "protocol").text = "OGC:WMS"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = (
                integrity_link.integrity_title or "Untitled Dataset"
            )

        if layer_urls and "wfs" in layer_urls:
            wfs = layer_urls["wfs"]

            # WFS
            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = wfs.get("base", "")
            etree.SubElement(resource, "protocol").text = "OGC:WFS"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = (
                integrity_link.integrity_title or "Untitled Dataset"
            )

            # WFS GetFeature
            # ignore GetFeature for now

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
        organization_name: str = "",
        layer_urls: dict[str, Any] | None = None,
    ) -> str:
        """Generate and publish metadata in one operation.

        Args:
            integrity_link: IntegrityLink record with data to populate metadata
            user_email: User email address
            user_first_name: User first name
            user_last_name: User last name
            organization_name: Long display name of the organization (falls back to integrity_organization)
            layer_urls: Optional dictionary containing WMS/WFS URLs from GeoServer layer

        Returns:
            Metadata UUID from GeoNetwork
        """
        metadata_xml = self.generate_metadata(
            integrity_link,
            user_email=user_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            organization_name=organization_name,
            layer_urls=layer_urls,
        )
        return self.publish_metadata(metadata_xml)

    def set_record_ownership(self, metadata_uuid: str, username: str, group_name: str) -> None:
        """Set ownership of a GeoNetwork metadata record.

        Resolves user and group IDs, then sets ownership via GeoNetwork API.
        Group resolution strategy depends on ``self.org_based_sync``:
        - True  → match *group_name* against all GN groups (org-based sync)
        - False → use the user's own GN group memberships, with fallback

        Args:
            metadata_uuid: UUID of the published metadata record
            username: Owner username to match in GeoNetwork
            group_name: Group name to match in GeoNetwork (used only when org_based_sync=True)
        """
        session = self.gn_api.session

        # 1. Find user ID by username
        resp = session.get(f"{self.gn_api.api_url}/users")
        resp.raise_for_status()
        users = resp.json()
        user_id = next((u["id"] for u in users if u["username"] == username), None)

        if user_id is None:
            logger.warning(
                "Cannot set ownership: user '%s' not found in GeoNetwork",
                username,
            )
            return

        # 2. Resolve group ID based on sync strategy
        if self.org_based_sync:
            group_id = self._resolve_group_by_org_name(session, group_name)
        else:
            group_id = self._resolve_group_from_user(session, user_id)

        if group_id is None:
            logger.warning(
                "Cannot set ownership: no group resolved for user '%s' (strategy=%s)",
                username,
                "org-based" if self.org_based_sync else "user-groups",
            )
            return

        # 3. Set ownership
        resp = session.put(
            f"{self.gn_api.api_url}/records/{metadata_uuid}/ownership",
            params={"groupIdentifier": group_id, "userIdentifier": user_id},
        )
        resp.raise_for_status()
        logger.info(
            "Set metadata %s ownership to user=%s (id=%s), group_id=%s",
            metadata_uuid,
            username,
            user_id,
            group_id,
        )

    def _resolve_group_by_org_name(self, session: Any, group_name: str) -> int | None:
        """Resolve a GeoNetwork group ID by matching organization name.

        Args:
            session: Authenticated HTTP session
            group_name: Organization/group name to look up (case-insensitive)

        Returns:
            Group ID or None if not found
        """
        logger.info(
            "Resolving group by organization name '%s' (org-based sync)",
            group_name,
        )
        resp = session.get(f"{self.gn_api.api_url}/groups")
        resp.raise_for_status()
        groups = resp.json()
        return next(
            (g["id"] for g in groups if g["name"].lower() == group_name.lower()),
            None,
        )

    def _resolve_group_from_user(self, session: Any, user_id: int) -> int | None:
        """Resolve a GeoNetwork group from the user's own memberships.

        Fetches the user's group memberships, filters out system groups
        (id <= 2: intranet, guest, all), and returns the first non-system group.
        Falls back to ``self.metadata_default_group_name`` via org-name lookup.

        Args:
            session: Authenticated HTTP session
            user_id: GeoNetwork user ID

        Returns:
            Group ID or None if no suitable group found
        """
        logger.info(
            "Resolving group from user %s memberships (user-groups sync)",
            user_id,
        )
        resp = session.get(f"{self.gn_api.api_url}/users/{user_id}/groups")
        resp.raise_for_status()
        memberships = resp.json()

        # Filter out system groups (groupId <= 2)
        non_system = [g["id"]["groupId"] for g in memberships if g["id"]["groupId"] > 2]

        if non_system:
            return non_system[0]

        # Fallback: resolve by default group name
        logger.info(
            "User %s has no non-system groups, falling back to default group '%s'",
            user_id,
            self.metadata_default_group_name,
        )
        return self._resolve_group_by_org_name(session, self.metadata_default_group_name)

    @staticmethod
    def _detect_schema(root: _Element) -> str | None:
        """Detect the ISO metadata schema from the root element's namespace tag.

        Returns:
            Schema identifier string, or None if unsupported.
        """
        tag = str(root.tag)
        if "http://standards.iso.org/iso/19115/-3/mdb/2.0" in tag:
            return _SCHEMA_19115_3
        if "http://www.isotc211.org/2005/gmd" in tag:
            return _SCHEMA_19139
        return None

    @staticmethod
    def _update_revision_date_19115_3(root: _Element, revision_date: datetime) -> None:
        """Insert or replace the data revision date in an ISO 19115-3 record.

        Only updates the citation-level ``mri:citation/cit:CI_Citation/cit:date``
        element (data revision date). The metadata-level ``mdb:dateInfo`` is not
        modified. Always writes a ``gco:DateTime``; replaces an existing
        ``gco:Date`` or ``gco:DateTime`` if present.
        """
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        ns = NS_19115_3

        citations = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification/mri:citation/cit:CI_Citation",
            namespaces=ns,
        )
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

    @staticmethod
    def _update_revision_date_19139(root: _Element, revision_date: datetime) -> None:
        """Insert or replace the data revision date in an ISO 19139 record.

        Always writes a ``gco:DateTime``; replaces an existing ``gco:Date`` or
        ``gco:DateTime`` if present. The metadata-level ``gmd:dateStamp`` is not
        modified.
        """
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        ns = NS_19139
        codelist_19139 = (
            "http://standards.iso.org/iso/19139/resources/codelist/gmxCodelists.xml#CI_DateTypeCode"
        )

        citations = root.xpath(
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

    def update_revision_date(self, metadata_uuid: str, revision_date: datetime) -> None:
        """Fetch a GeoNetwork record, set its revision date, and save.

        Uses the GeoNetwork upload endpoint (POST /records with
        ``uuidprocessing="OVERWRITE"``) via ``GnApi.upload_metadata`` to update
        the XML while preserving the record's publication status/privileges.

        Args:
            metadata_uuid: UUID of the metadata record in GeoNetwork.
            revision_date: The datetime to set as revision date.
        """
        xml_bytes: bytes = self.gn_api.get_metadataxml(metadata_uuid)
        root: _Element = etree.fromstring(xml_bytes)

        schema = self._detect_schema(root)
        if schema is None:
            logger.warning(
                "Unsupported metadata schema for record %s (root tag: %s), "
                "skipping revision date update",
                metadata_uuid,
                root.tag,
            )
            return

        if schema == _SCHEMA_19115_3:
            self._update_revision_date_19115_3(root, revision_date)
        else:
            self._update_revision_date_19139(root, revision_date)

        updated_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

        # Use POST /records with OVERWRITE — GeoNetwork does not expose a raw-PUT
        # record update endpoint. OVERWRITE on an existing record updates the XML
        # without altering its publication privileges.
        self.gn_api.upload_metadata(updated_xml, uuidprocessing="OVERWRITE")
        logger.info("Updated revision date for metadata record %s", metadata_uuid)

    def upload_metadata_xml(self, xml_bytes: bytes) -> None:
        """Upload raw XML bytes to GeoNetwork via OVERWRITE.

        OVERWRITE keeps existing publication privileges intact.

        Args:
            xml_bytes: Raw UTF-8 encoded XML of the metadata record.

        Raises:
            Exception: If the GeoNetwork upload fails.
        """
        self.gn_api.upload_metadata(xml_bytes, uuidprocessing="OVERWRITE")
        logger.info("Uploaded metadata XML to GeoNetwork")

    def delete_record(self, metadata_uuid: str) -> None:
        """Delete a metadata record from GeoNetwork.

        Treats 404 as success. Logs and suppresses other errors.

        Args:
            metadata_uuid: UUID of the metadata record to delete
        """
        try:
            session = self.gn_api.session
            response = session.delete(f"{self.gn_api.api_url}/records/{metadata_uuid}")
            if response.status_code == 404:
                logger.info(f"Metadata record not found (already deleted): {metadata_uuid}")
                return
            if response.status_code not in (200, 204):
                logger.error(
                    f"Unexpected status {response.status_code} deleting metadata record {metadata_uuid}"
                )
            else:
                logger.info(f"Deleted metadata record: {metadata_uuid}")
        except Exception as e:
            logger.error(
                f"Failed to delete metadata record {metadata_uuid}: {e}",
                exc_info=True,
            )

    def sync_record_sharing(
        self,
        metadata_uuid: str,
        privileges: list[tuple[str, RuleValue]],
    ) -> None:
        """Sync sharing privileges to a GeoNetwork record.

        Args:
            metadata_uuid: UUID of the GeoNetwork record
            privileges: Pre-resolved list of (org_name, rule_value) tuples.
                        Caller is responsible for resolving geOrchestra org IDs to names.

        Replaces all existing record privileges (clear=True).

        Raises:
            ValueError: If a GeoNetwork group cannot be resolved for an org name.
            Exception: If the GeoNetwork API call fails.
        """
        resp = self.gn_api.session.get(f"{self.gn_api.api_url}/groups")
        resp.raise_for_status()
        groups = resp.json()
        group_id_by_name = {g["name"].lower(): g["id"] for g in groups}

        gn_privileges: list[dict[str, Any]] = []
        settings = get_settings()
        for org_name, rule_value in privileges:
            if settings.METADATA_GROUPS_LABEL_FILTER_REGEX:
                search = re.search(settings.METADATA_GROUPS_LABEL_FILTER_REGEX, org_name)
                if search and search.lastindex:
                    org_name = search.group(1)
            gn_group_id = group_id_by_name.get(org_name.lower())
            if gn_group_id is None:
                raise ValueError(f"No GN group found for org '{org_name}'")

            is_write = rule_value == RuleValue.WRITE
            gn_privileges.append(
                {
                    "group": gn_group_id,
                    "operations": {
                        "view": True,
                        "download": True,
                        "editing": is_write,
                        "notify": False,
                        "dynamic": False,
                        "featured": False,
                    },
                }
            )

        sharing = {"clear": True, "privileges": gn_privileges}
        self.gn_api.put_sharing_record(metadata_uuid, sharing)
        logger.info(
            "Synced sharing for record %s: %d privilege(s)",
            metadata_uuid,
            len(gn_privileges),
        )

    def toggle_publish_metadata_record(self, metadata_uuid: str, publish: bool) -> None:
        """Toggle publication status of a metadata record in GeoNetwork.

        Args:
            metadata_uuid: UUID of the metadata record
            publish: True to publish (make visible/public), False to unpublish (make private)

        Raises:
            Exception: If the operation fails
        """
        try:
            if publish:
                self.gn_api.put_publish_record(metadata_uuid)
                logger.info(f"Successfully published metadata record: {metadata_uuid}")
            else:
                self.gn_api.put_unpublish_record(metadata_uuid)
                logger.info(f"Successfully unpublished metadata record: {metadata_uuid}")
        except Exception as e:
            action = "publish" if publish else "unpublish"
            logger.error(
                f"Failed to {action} metadata record {metadata_uuid}: {e}",
                exc_info=True,
            )
            raise

    def update_ai_metadata(
        self,
        metadata_uuid: str,
        title: str,
        abstract: str,
        keywords: list[str],
        topic_categories: list[str],
        attribute_descriptions: list[AttributeInfo] | None = None,
        temporal_extent: TemporalExtent | None = None,
    ) -> None:
        """Patch title, abstract, keywords, topic categories, attribute catalog and temporal extent.

        Fetches the current XML, updates the relevant fields in-place, then
        re-uploads with OVERWRITE so publication privileges are preserved.
        Supports both ISO 19115-3 and ISO 19139 schemas.

        Args:
            metadata_uuid: UUID of the GeoNetwork metadata record.
            title: AI-inferred title for the dataset.
            abstract: AI-generated abstract text.
            keywords: AI-generated keyword list.
            topic_categories: AI-generated ISO 19115 topic category codes (one or more).
            attribute_descriptions: AI-generated attribute/column descriptions (optional).
            temporal_extent: AI-inferred temporal extent (optional).
        """
        xml_bytes: bytes = self.gn_api.get_metadataxml(metadata_uuid)
        root: _Element = etree.fromstring(xml_bytes)

        schema = self._detect_schema(root)
        if schema is None:
            logger.warning(
                "Unsupported metadata schema for record %s — skipping AI metadata update",
                metadata_uuid,
            )
            return

        if schema == _SCHEMA_19115_3:
            self._patch_ai_fields_19115_3(root, title, abstract, keywords, topic_categories)
            if attribute_descriptions:
                self._patch_attribute_catalogue_19115_3(root, attribute_descriptions)
            if temporal_extent and temporal_extent.type != "unknown":
                self._patch_temporal_extent_19115_3(root, temporal_extent)
        else:
            self._patch_ai_fields_19139(root, title, abstract, keywords, topic_categories)
            if attribute_descriptions:
                self._patch_attribute_catalogue_19139(root, attribute_descriptions)
            if temporal_extent and temporal_extent.type != "unknown":
                self._patch_temporal_extent_19139(root, temporal_extent)

        updated_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
        self.gn_api.upload_metadata(updated_xml, uuidprocessing="OVERWRITE")
        logger.info("Updated AI metadata fields for record %s", metadata_uuid)

    @staticmethod
    def _patch_ai_fields_19115_3(
        root: _Element,
        title: str,
        abstract: str,
        keywords: list[str],
        topic_categories: list[str],
    ) -> None:
        """Patch title, abstract, keywords and topicCategory in an ISO 19115-3 record."""
        ns = NS_19115_3
        id_info_list = root.xpath(
            "mdb:identificationInfo/mri:MD_DataIdentification",
            namespaces=ns,
        )
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        # --- title ---
        title_els = id_info.xpath(
            "mri:citation/cit:CI_Citation/cit:title/gco:CharacterString", namespaces=ns
        )
        if title_els:
            title_els[0].text = title
        abstract_els = id_info.xpath("mri:abstract/gco:CharacterString", namespaces=ns)
        if abstract_els:
            abstract_els[0].text = abstract
        else:
            abstract_wrapper: _Element = etree.SubElement(id_info, f"{{{ns['mri']}}}abstract")
            etree.SubElement(abstract_wrapper, f"{{{ns['gco']}}}CharacterString").text = abstract

        # --- keywords ---
        ns_mri = ns["mri"]
        ns_gco = ns["gco"]
        existing_kw_blocks = id_info.xpath("mri:descriptiveKeywords", namespaces=ns)
        # Remove any existing AI-tagged keyword block (identified by a special anchor in thesaurusName)
        for block in existing_kw_blocks:
            anchor_texts = block.xpath(
                "mri:MD_Keywords/mri:thesaurusName//gco:CharacterString[contains(., 'ai-generated')]",
                namespaces=ns,
            )
            if anchor_texts:
                id_info.remove(block)

        # Add a fresh keyword block
        desc_kw: _Element = etree.SubElement(id_info, f"{{{ns_mri}}}descriptiveKeywords")
        md_kw: _Element = etree.SubElement(desc_kw, f"{{{ns_mri}}}MD_Keywords")
        for kw in keywords:
            kw_el: _Element = etree.SubElement(md_kw, f"{{{ns_mri}}}keyword")
            etree.SubElement(kw_el, f"{{{ns_gco}}}CharacterString").text = kw
        # Tag this block so we can identify it in future updates
        thesaurus_name: _Element = etree.SubElement(md_kw, f"{{{ns_mri}}}thesaurusName")
        ci_citation: _Element = etree.SubElement(thesaurus_name, f"{{{ns['cit']}}}CI_Citation")
        title_el: _Element = etree.SubElement(ci_citation, f"{{{ns['cit']}}}title")
        etree.SubElement(title_el, f"{{{ns_gco}}}CharacterString").text = "ai-generated"

        # --- topicCategory ---
        ns_mri_uri = f"{{{ns_mri}}}"
        for tc in id_info.xpath("mri:topicCategory", namespaces=ns):
            id_info.remove(tc)
        for cat in topic_categories:
            topic_wrapper: _Element = etree.SubElement(id_info, f"{ns_mri_uri}topicCategory")
            etree.SubElement(topic_wrapper, f"{ns_mri_uri}MD_TopicCategoryCode").text = cat

    @staticmethod
    def _patch_ai_fields_19139(
        root: _Element,
        title: str,
        abstract: str,
        keywords: list[str],
        topic_categories: list[str],
    ) -> None:
        """Patch title, abstract, keywords and topicCategory in an ISO 19139 record."""
        ns = NS_19139
        ns_gmd = ns["gmd"]
        ns_gco = ns["gco"]

        id_info_list = root.xpath(
            "gmd:identificationInfo/gmd:MD_DataIdentification",
            namespaces=ns,
        )
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        # --- title ---
        title_els = id_info.xpath(
            "gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString", namespaces=ns
        )
        if title_els:
            title_els[0].text = title

        # --- abstract ---
        abstract_els = id_info.xpath("gmd:abstract/gco:CharacterString", namespaces=ns)
        if abstract_els:
            abstract_els[0].text = abstract
        else:
            wrapper: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}abstract")
            etree.SubElement(wrapper, f"{{{ns_gco}}}CharacterString").text = abstract

        # --- keywords ---
        for block in id_info.xpath("gmd:descriptiveKeywords", namespaces=ns):
            anchor_texts = block.xpath(
                "gmd:MD_Keywords/gmd:thesaurusName//gco:CharacterString[contains(., 'ai-generated')]",
                namespaces=ns,
            )
            if anchor_texts:
                id_info.remove(block)

        desc_kw: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}descriptiveKeywords")
        md_kw: _Element = etree.SubElement(desc_kw, f"{{{ns_gmd}}}MD_Keywords")
        for kw in keywords:
            kw_el: _Element = etree.SubElement(md_kw, f"{{{ns_gmd}}}keyword")
            etree.SubElement(kw_el, f"{{{ns_gco}}}CharacterString").text = kw
        thesaurus_name: _Element = etree.SubElement(md_kw, f"{{{ns_gmd}}}thesaurusName")
        ci_citation: _Element = etree.SubElement(thesaurus_name, f"{{{ns_gmd}}}CI_Citation")
        title_el: _Element = etree.SubElement(ci_citation, f"{{{ns_gmd}}}title")
        etree.SubElement(title_el, f"{{{ns_gco}}}CharacterString").text = "ai-generated"

        # --- topicCategory ---
        for tc in id_info.xpath("gmd:topicCategory", namespaces=ns):
            id_info.remove(tc)
        for cat in topic_categories:
            topic_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}topicCategory")
            etree.SubElement(topic_wrapper, f"{{{ns_gmd}}}MD_TopicCategoryCode").text = cat

    @staticmethod
    def _patch_attribute_catalogue_19115_3(
        root: _Element,
        attribute_descriptions: list[AttributeInfo],
    ) -> None:
        """Add feature catalogue description and supplemental info for ISO 19115-3 records.

        Uses two complementary storage locations:
        - mdb:contentInfo/mrc:MD_FeatureCatalogueDescription: ISO 19115-3 standard location
          with one MD_FeatureTypeInfo per attribute (name + SQL type in ScopedName codeSpace).
        - mri:supplementalInformation: full text table (name | type | description) rendered
          in GeoNetwork's default metadata view.
        """
        ns = NS_19115_3
        ns_mdb = ns["mdb"]
        ns_mrc = "http://standards.iso.org/iso/19115/-3/mrc/2.0"
        ns_mri = ns["mri"]
        ns_gco = ns["gco"]

        # --- Remove any existing AI-tagged contentInfo block ---
        for block in root.xpath("mdb:contentInfo", namespaces=ns):
            anchor = block.xpath(
                ".//mrc:MD_FeatureCatalogueDescription/mrc:featureCatalogueCitation"
                "//gco:CharacterString[contains(., 'ai-generated')]",
                namespaces={**ns, "mrc": ns_mrc},
            )
            if anchor:
                root.remove(block)

        # --- Build mdb:contentInfo/mrc:MD_FeatureCatalogueDescription ---
        content_info: _Element = etree.SubElement(root, f"{{{ns_mdb}}}contentInfo")
        feat_cat_desc: _Element = etree.SubElement(
            content_info, f"{{{ns_mrc}}}MD_FeatureCatalogueDescription"
        )
        included: _Element = etree.SubElement(feat_cat_desc, f"{{{ns_mrc}}}includedWithDataset")
        etree.SubElement(included, f"{{{ns_gco}}}Boolean").text = "true"

        for attr in attribute_descriptions:
            ft_info: _Element = etree.SubElement(feat_cat_desc, f"{{{ns_mrc}}}featureTypes")
            md_ft: _Element = etree.SubElement(ft_info, f"{{{ns_mrc}}}MD_FeatureTypeInfo")
            ft_name: _Element = etree.SubElement(md_ft, f"{{{ns_mrc}}}featureTypeName")
            scoped: _Element = etree.SubElement(ft_name, f"{{{ns_gco}}}ScopedName")
            scoped.set("codeSpace", attr.type)
            scoped.text = attr.name

        # Tag the citation so we can identify and remove it on re-generation
        citation_wrapper: _Element = etree.SubElement(
            feat_cat_desc, f"{{{ns_mrc}}}featureCatalogueCitation"
        )
        cit_ns = ns["cit"]
        ci_cit: _Element = etree.SubElement(citation_wrapper, f"{{{cit_ns}}}CI_Citation")
        cit_title: _Element = etree.SubElement(ci_cit, f"{{{cit_ns}}}title")
        etree.SubElement(cit_title, f"{{{ns_gco}}}CharacterString").text = "ai-generated"

        # --- supplementalInformation: full attribute table as text ---
        id_info_list = root.xpath("mdb:identificationInfo/mri:MD_DataIdentification", namespaces=ns)
        if not id_info_list:
            return
        id_info = id_info_list[0]
        existing_suppl = id_info.xpath("mri:supplementalInformation", namespaces=ns)
        table_lines = ["Catalogue d'attributs :"]
        table_lines += [f"- {a.name} | {a.type} | {a.description}" for a in attribute_descriptions]
        suppl_text = "\n".join(table_lines)
        if existing_suppl:
            cs = existing_suppl[0].find(f"{{{ns_gco}}}CharacterString")
            if cs is not None:
                cs.text = suppl_text
            else:
                etree.SubElement(
                    existing_suppl[0], f"{{{ns_gco}}}CharacterString"
                ).text = suppl_text
        else:
            suppl_el: _Element = etree.SubElement(id_info, f"{{{ns_mri}}}supplementalInformation")
            etree.SubElement(suppl_el, f"{{{ns_gco}}}CharacterString").text = suppl_text

    @staticmethod
    def _patch_attribute_catalogue_19139(
        root: _Element,
        attribute_descriptions: list[AttributeInfo],
    ) -> None:
        """Add feature catalogue description and supplemental info for ISO 19139 records."""
        ns = NS_19139
        ns_gmd = ns["gmd"]
        ns_gco = ns["gco"]

        # --- Remove any existing AI-tagged contentInfo block ---
        for block in root.xpath("gmd:contentInfo", namespaces=ns):
            anchor = block.xpath(
                ".//gmd:MD_FeatureCatalogueDescription/gmd:featureCatalogueCitation"
                "//gco:CharacterString[contains(., 'ai-generated')]",
                namespaces=ns,
            )
            if anchor:
                root.remove(block)

        # --- Build gmd:contentInfo/gmd:MD_FeatureCatalogueDescription ---
        content_info: _Element = etree.SubElement(root, f"{{{ns_gmd}}}contentInfo")
        feat_cat_desc: _Element = etree.SubElement(
            content_info, f"{{{ns_gmd}}}MD_FeatureCatalogueDescription"
        )
        included: _Element = etree.SubElement(feat_cat_desc, f"{{{ns_gmd}}}includedWithDataset")
        etree.SubElement(included, f"{{{ns_gco}}}Boolean").text = "true"

        for attr in attribute_descriptions:
            ft_info: _Element = etree.SubElement(feat_cat_desc, f"{{{ns_gmd}}}featureTypes")
            md_ft: _Element = etree.SubElement(ft_info, f"{{{ns_gmd}}}MD_FeatureTypeInfo")
            ft_name: _Element = etree.SubElement(md_ft, f"{{{ns_gmd}}}featureTypeName")
            scoped: _Element = etree.SubElement(ft_name, f"{{{ns_gco}}}ScopedName")
            scoped.set("codeSpace", attr.type)
            scoped.text = attr.name

        citation_wrapper: _Element = etree.SubElement(
            feat_cat_desc, f"{{{ns_gmd}}}featureCatalogueCitation"
        )
        ci_cit: _Element = etree.SubElement(citation_wrapper, f"{{{ns_gmd}}}CI_Citation")
        cit_title: _Element = etree.SubElement(ci_cit, f"{{{ns_gmd}}}title")
        etree.SubElement(cit_title, f"{{{ns_gco}}}CharacterString").text = "ai-generated"

        # --- supplementalInformation ---
        id_info_list = root.xpath("gmd:identificationInfo/gmd:MD_DataIdentification", namespaces=ns)
        if not id_info_list:
            return
        id_info = id_info_list[0]
        existing_suppl = id_info.xpath("gmd:supplementalInformation", namespaces=ns)
        table_lines = ["Catalogue d'attributs :"]
        table_lines += [f"- {a.name} | {a.type} | {a.description}" for a in attribute_descriptions]
        suppl_text = "\n".join(table_lines)
        if existing_suppl:
            cs = existing_suppl[0].find(f"{{{ns_gco}}}CharacterString")
            if cs is not None:
                cs.text = suppl_text
            else:
                etree.SubElement(
                    existing_suppl[0], f"{{{ns_gco}}}CharacterString"
                ).text = suppl_text
        else:
            suppl_el: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}supplementalInformation")
            etree.SubElement(suppl_el, f"{{{ns_gco}}}CharacterString").text = suppl_text

    @staticmethod
    def _patch_temporal_extent_19115_3(
        root: _Element,
        temporal_extent: TemporalExtent,
    ) -> None:
        """Inject or replace a temporal extent in an ISO 19115-3 record.

        Structure:
          mri:extent/gex:EX_Extent/gex:temporalElement/gex:EX_TemporalExtent
            /gex:extent/gml:TimePeriod  (or gml:TimeInstant)
        """
        ns = NS_19115_3
        ns_mri = ns["mri"]
        ns_gex = "http://standards.iso.org/iso/19115/-3/gex/1.0"
        ns_gml = "http://www.opengis.net/gml/3.2"

        id_info_list = root.xpath("mdb:identificationInfo/mri:MD_DataIdentification", namespaces=ns)
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        # Remove any existing AI-tagged temporal extent block
        for extent_el in id_info.xpath("mri:extent", namespaces=ns):
            if extent_el.xpath(
                ".//gex:temporalElement//gco:CharacterString[contains(., 'ai-generated-temporal')]",
                namespaces={**ns, "gex": ns_gex},
            ):
                id_info.remove(extent_el)

        extent_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_mri}}}extent")
        ex_extent: _Element = etree.SubElement(extent_wrapper, f"{{{ns_gex}}}EX_Extent")

        # Tag for future removal
        desc_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gex}}}description")
        etree.SubElement(desc_el, f"{{{ns['gco']}}}CharacterString").text = "ai-generated-temporal"

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
            # instant
            time_el = etree.SubElement(extent_inner, f"{{{ns_gml}}}TimeInstant")
            time_el.set(f"{{{ns_gml}}}id", "ai-temporal-instant")
            pos_el: _Element = etree.SubElement(time_el, f"{{{ns_gml}}}timePosition")
            pos_el.text = temporal_extent.instant or temporal_extent.begin or ""

    @staticmethod
    def _patch_temporal_extent_19139(
        root: _Element,
        temporal_extent: TemporalExtent,
    ) -> None:
        """Inject or replace a temporal extent in an ISO 19139 record.

        Structure:
          gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent
            /gmd:extent/gml:TimePeriod  (or gml:TimeInstant)
        """
        ns = NS_19139
        ns_gmd = ns["gmd"]
        ns_gco = ns["gco"]
        ns_gml = "http://www.opengis.net/gml/3.2"

        id_info_list = root.xpath("gmd:identificationInfo/gmd:MD_DataIdentification", namespaces=ns)
        if not id_info_list:
            return
        id_info: _Element = id_info_list[0]

        # Remove any existing AI-tagged temporal extent block
        for extent_el in id_info.xpath("gmd:extent", namespaces=ns):
            if extent_el.xpath(
                ".//gmd:temporalElement//gco:CharacterString[contains(., 'ai-generated-temporal')]",
                namespaces=ns,
            ):
                id_info.remove(extent_el)

        extent_wrapper: _Element = etree.SubElement(id_info, f"{{{ns_gmd}}}extent")
        ex_extent: _Element = etree.SubElement(extent_wrapper, f"{{{ns_gmd}}}EX_Extent")

        # Tag for future removal
        desc_el: _Element = etree.SubElement(ex_extent, f"{{{ns_gmd}}}description")
        etree.SubElement(desc_el, f"{{{ns_gco}}}CharacterString").text = "ai-generated-temporal"

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
            # instant
            time_el = etree.SubElement(extent_inner, f"{{{ns_gml}}}TimeInstant")
            time_el.set(f"{{{ns_gml}}}id", "ai-temporal-instant")
            pos_el: _Element = etree.SubElement(time_el, f"{{{ns_gml}}}timePosition")
            pos_el.text = temporal_extent.instant or temporal_extent.begin or ""
