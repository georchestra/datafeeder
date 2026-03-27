from __future__ import annotations

import re
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
        ).text = f"Dataset imported via Datafeeder: {integrity_link.integrity_title or 'Untitled'}"

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

        etree.SubElement(props, "creationDate").text = created_at.strftime("%Y-%m-%dT%H:%M:%S")
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

        if layer_urls and "ogcfeatures" in layer_urls:
            ogcfeatures = layer_urls["ogcfeatures"]

            resource = etree.SubElement(online_resources, "onlineResource")
            etree.SubElement(resource, "linkage").text = ogcfeatures
            etree.SubElement(resource, "protocol").text = "OGC API Features"
            etree.SubElement(resource, "name").text = layer_name
            etree.SubElement(resource, "description").text = "OGC API Features"

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
        tag = root.tag
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
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%S")
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
        date_str = revision_date.strftime("%Y-%m-%dT%H:%M:%S")
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

        Uses the GeoNetwork save endpoint (PUT /records/{uuid}) to preserve
        the record's publication status.

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

        session = self.gn_api.session
        resp = session.put(
            f"{self.gn_api.api_url}/records/{metadata_uuid}",
            data=updated_xml,
            headers={"Content-Type": "application/xml"},
        )
        resp.raise_for_status()
        logger.info("Updated revision date for metadata record %s", metadata_uuid)

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
                    org_name = search.group(0)
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
