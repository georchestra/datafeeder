from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from geonetwork import GnApi
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
from src.services.metadata_schema import MetadataSchema, NoopSchema
from src.services.metadata_schema_19115_3 import Iso19115_3Schema
from src.services.metadata_schema_19139 import Iso19139Schema

logger = get_logger()


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
        metadata_admin_default_group_name: str = "sample",
    ):
        """Initialize with GeoNetwork API client and paths to metadata files.

        Args:
            gn_api_url: GeoNetwork API URL (e.g., http://geonetwork:8080/geonetwork/srv/api)
            datadir_path: Path to datadir (e.g., /etc/georchestra)
            credentials: Optional GnApi credentials
            verify_tls: Whether to verify TLS certificates
            gn_sync_mode: "ORG" to resolve group by org name; "ROLE" to use user's GN memberships
            metadata_default_group_name: Fallback group name when user has no non-system groups
            metadata_admin_default_group_name: Fallback group name when user has admin profile
        """
        self.gn_api: Any = GnApi(api_url=gn_api_url, credentials=credentials, verifytls=verify_tls)
        self.template_path: str = f"{datadir_path}/datafeeder/metadata_template-19115-3.xml"
        self.xslt_path: str = f"{datadir_path}/datafeeder/metadata_transform-19115-3.xsl"
        self.org_based_sync: bool = gn_sync_mode == "ORG"
        self.metadata_default_group_name: str = metadata_default_group_name
        self.metadata_admin_default_group_name: str = metadata_admin_default_group_name

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
        user_id, profile = self.resolve_user_id(integrity_link)
        group_id = self.resolve_group_id(integrity_link, user_id, profile)
        template_uuid = self.choose_group_and_template(group_id)[1]
        logger.info(f"Using template {template_uuid} for group {group_id}")

        if template_uuid is None:
            xml_doc: _ElementTree = etree.parse(self.template_path)
        else:
            resp = self.gn_api.get_metadataxml(template_uuid)
            xml_doc: _ElementTree = etree.ElementTree(etree.fromstring(resp))

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
            metadata_uuid: str = response_data.get("uuid") or response_data.get("id")
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

    def set_record_ownership(self, integrity_link: IntegrityLink) -> None:
        """Set ownership of a GeoNetwork metadata record.

        Resolves user and group IDs, then sets ownership via GeoNetwork API.
        Group resolution strategy depends on ``self.org_based_sync``:
        - True  → match *integrity_link.integrity_organization* against all GN groups (org-based sync)
        - False → use the user's own GN group memberships, with fallback

        Args:
            integrity_link: IntegrityLink record whose id is the published metadata UUID,
                and whose owner/organization identify the GeoNetwork user and group
        """

        metadata_uuid = str(integrity_link.id)
        username = integrity_link.integrity_owner

        user_id, profile = self.resolve_user_id(integrity_link)

        if user_id is None:
            logger.warning(
                "Cannot set ownership: user '%s' not found in GeoNetwork",
                username,
            )
            return

        group_id = self.resolve_group_id(integrity_link, user_id, profile)
        group_id = self.choose_group_and_template(group_id)[0]

        if group_id is None:
            logger.warning(
                "Cannot set ownership: no group resolved for user '%s' (strategy=%s)",
                username,
                "org-based" if self.org_based_sync else "user-groups",
            )
            return

        # 3. Set ownership
        resp = self.gn_api.session.put(
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

    def resolve_user_id(self, integrity_link: IntegrityLink) -> tuple[int | None, str | None]:
        resp = self.gn_api.session.get(f"{self.gn_api.api_url}/users")
        resp.raise_for_status()
        users = resp.json()
        return next(
            (
                (u["id"], u["profile"])
                for u in users
                if u["username"] == integrity_link.integrity_owner
            ),
            (None, None),
        )

    def resolve_group_id(
        self, integrity_link: IntegrityLink, user_id: int | None, profile: str | None
    ) -> list[int]:
        if self.org_based_sync or user_id is None:
            group_id = self._resolve_group_by_org_name(integrity_link.integrity_organization)
        else:
            group_id = self._resolve_group_from_user(user_id, profile)
        return group_id

    def _resolve_group_by_org_name(self, group_name: str) -> list[int]:
        """Resolve a GeoNetwork group ID by matching organization name.

        Args:
            group_name: Organization/group name to look up (case-insensitive)

        Returns:
            Group ID or None if not found
        """
        logger.info(
            "Resolving group by organization name '%s' (org-based sync)",
            group_name,
        )
        resp = self.gn_api.session.get(f"{self.gn_api.api_url}/groups")
        resp.raise_for_status()
        groups = resp.json()
        return [g["id"] for g in groups if g["name"].lower() == group_name.lower()]

    def _resolve_group_from_user(self, user_id: int, profile: str | None) -> list[int]:
        """Resolve a GeoNetwork group from the user's own memberships.

        Fetches the user's group memberships, filters out system groups
        (id <= 2: intranet, guest, all), and returns the first non-system group.
        Falls back to ``self.metadata_default_group_name`` via org-name lookup.

        Args:
            user_id: GeoNetwork user ID

        Returns:
            Group ID or None if no suitable group found
        """
        logger.info(
            "Resolving group from user %s memberships (user-groups sync)",
            user_id,
        )
        if profile == "Administrator":
            logger.info(
                "User %s has admin profile, falling back to default admin group '%s'",
                user_id,
                self.metadata_admin_default_group_name,
            )
            return self._resolve_group_by_org_name(self.metadata_admin_default_group_name)

        resp = self.gn_api.session.get(f"{self.gn_api.api_url}/users/{user_id}/groups")
        resp.raise_for_status()
        memberships = resp.json()

        # Filter out system groups (groupId <= 2)
        non_system = [g["id"]["groupId"] for g in memberships if g["id"]["groupId"] > 2]

        if non_system:
            return non_system

        logger.info(
            "User %s has no non-system groups, falling back to default group '%s'",
            user_id,
            self.metadata_default_group_name,
        )
        return self._resolve_group_by_org_name(self.metadata_default_group_name)

    def detect_schema(self, metadata_uuid: str) -> MetadataSchema:
        """Fetch a GeoNetwork metadata record and return its schema instance.

        Args:
            metadata_uuid: UUID of the metadata record in GeoNetwork.

        Returns:
            A schema instance wrapping the parsed record, ready to be
            processed by ``get_title``, the update methods, or
            ``add_online_resources_from_layer_urls_19115_3``. A ``NoopSchema``
            is returned if the record cannot be fetched.
        """
        try:
            xml_bytes: bytes = self.gn_api.get_metadataxml(metadata_uuid)
        except Exception as e:
            logger.warning("Could not fetch metadata XML for %s: %s", metadata_uuid, e)
            return NoopSchema(etree.Element("unknown"))

        return self.detect_schema_from_xml(xml_bytes)

    @staticmethod
    def detect_schema_from_xml(xml_bytes: bytes) -> MetadataSchema:
        """Parse raw metadata XML and return its schema instance.

        Args:
            xml_bytes: Raw UTF-8 encoded XML of the metadata record.

        Returns:
            A schema instance wrapping the parsed record, ready to be
            processed by ``get_title``, the update methods, or
            ``add_online_resources_from_layer_urls_19115_3``.
        """
        root: _Element = etree.fromstring(xml_bytes)
        tag = str(root.tag)
        if "http://standards.iso.org/iso/19115/-3/mdb/2.0" in tag:
            return Iso19115_3Schema(root)
        if "http://www.isotc211.org/2005/gmd" in tag:
            return Iso19139Schema(root)
        return NoopSchema(root)

    def get_title(self, metadata_uuid: str) -> str | None:
        """Fetch the title from an existing GeoNetwork metadata record.

        Args:
            metadata_uuid: UUID of the metadata record in GeoNetwork.

        Returns:
            Title string, or None if the record or title cannot be read.
        """
        schema = self.detect_schema(metadata_uuid)
        return schema.get_title()

    def update_revision_date(self, metadata_uuid: str, revision_date: datetime) -> None:
        """Fetch a GeoNetwork record, set its revision date, and save.

        Uses the GeoNetwork upload endpoint (POST /records with
        ``uuidprocessing="OVERWRITE"``) via ``GnApi.upload_metadata`` to update
        the XML while preserving the record's publication status/privileges.

        Args:
            metadata_uuid: UUID of the metadata record in GeoNetwork.
            revision_date: The datetime to set as revision date.
        """
        schema = self.detect_schema(metadata_uuid)
        updated = schema.update_revision_date(revision_date)
        if not updated:
            return

        updated_xml = etree.tostring(schema.root, xml_declaration=True, encoding="UTF-8")

        # Use POST /records with OVERWRITE — GeoNetwork does not expose a raw-PUT
        # record update endpoint. OVERWRITE on an existing record updates the XML
        # without altering its publication privileges.
        self.gn_api.upload_metadata(updated_xml, uuidprocessing="OVERWRITE")
        logger.info("Updated revision date for metadata record %s", metadata_uuid)

    def update_online_resources_from_layer_urls(
        self, metadata_uuid: str, layer_urls: dict[str, Any]
    ) -> None:
        try:
            schema = self.detect_schema(metadata_uuid)
            updated = schema.add_online_resources_from_layer_urls_19115_3(layer_urls)
            if updated:
                self.gn_api.upload_metadata(
                    etree.tostring(schema.root, xml_declaration=True, encoding="UTF-8"),
                    uuidprocessing="OVERWRITE",
                )
                logger.info("Updated online resources for metadata record %s", metadata_uuid)
        except Exception as e:
            logger.warning(
                "Failed to update online resources for metadata record %s: %s",
                metadata_uuid,
                e,
                exc_info=True,
            )

    def update_online_resources_when_title_changed(self, xml_bytes: bytes, title: str) -> bytes:
        schema = self.detect_schema_from_xml(xml_bytes)
        schema.update_online_resources_when_title_changed(title)

        return etree.tostring(schema.root, xml_declaration=True, encoding="UTF-8")

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

    def get_templates_uuid(self, groups_id: list[int]) -> dict[str, list[str]]:
        group_owner_clause = " OR ".join(f'groupOwner:"{group_id}"' for group_id in groups_id)
        req = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "default_operator": "AND",
                                "query": f'(isTemplate:"y") AND ({group_owner_clause}) AND (documentStandard:"iso19115-3.2018")',
                            }
                        }
                    ]
                }
            },
            "_source": {"includes": ["groupOwner"]},
            "from": 0,
            "size": 1000,
        }
        resp = self.gn_api.search(req)
        templates_by_group_owner: dict[str, list[str]] = {}
        for md in resp["hits"]["hits"]:
            group_owner = md["_source"]["groupOwner"]
            templates_by_group_owner.setdefault(group_owner, []).append(md["_id"])
        return templates_by_group_owner

    def choose_group_and_template(self, groups_id: list[int]) -> tuple[int | None, str | None]:
        if len(groups_id) == 0:
            return (None, None)
        templates_by_group_owner = self.get_templates_uuid(groups_id)
        if len(templates_by_group_owner) == 0:
            return sorted(groups_id)[0], None
        group_owner = sorted(templates_by_group_owner.keys(), key=int)[0]
        template = sorted(templates_by_group_owner[group_owner], key=str)[0]
        return int(group_owner), template
