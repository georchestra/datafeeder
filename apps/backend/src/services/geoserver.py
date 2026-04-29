from enum import StrEnum
from typing import Any

from data_manipulation.geoserver import WorkspaceCreationResult
from data_manipulation.geoserver import (
    create_layer as dm_create_layer,
)
from data_manipulation.geoserver import (
    create_workspace as dm_create_workspace,
)
from data_manipulation.geoserver import (
    update_layer_bbox as dm_update_layer_bbox,
)
from geoservercloud import GeoServerCloud  # type: ignore[import-untyped]
from pydantic import BaseModel

from src.core.logging import get_logger
from src.models.integrity_link_rule import RuleValue

logger = get_logger()

# All ACL calls use self.geoserver.rest_service.rest_client (geoservercloud, requests-based, sync).
# Accept-Encoding: identity is required to prevent GeoServer's ByteArrayMessageConverter (OGC API)
# from intercepting PUT/POST requests and throwing "Reading is not supported".
_ACL_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Encoding": "identity",
}


class GeoServerAclError(Exception):
    """Raised when a GeoServer ACL API call returns an HTTP error."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"HTTP {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class AclAccessType(StrEnum):
    """GeoServer layer ACL access type."""

    READ = "r"
    WRITE = "w"


ACL_ROLE_EVERYONE = "*"
"""GeoServer ACL wildcard role granting access to everyone (anonymous included)."""


class WMSUrls(BaseModel):
    """WMS service URLs."""

    base: str
    capabilities: str
    getmap: str
    legend: str


class WFSUrls(BaseModel):
    """WFS service URLs."""

    base: str
    capabilities: str
    getfeature: str


class LayerCreationResult(BaseModel):
    """Result of layer creation."""

    workspace: str
    datastore: str
    layer: str
    layer_qualified_name: str
    table: str
    wms: WMSUrls | None
    wfs: WFSUrls | None
    ogcfeatures: str


class GeoServerService:
    """Service to interact with GeoServer API."""

    def __init__(
        self,
        base_url: str,  # e.g., "http://localhost:8080/geoserver"
        username: str,  # e.g., "admin"
        password: str,  # e.g., "admin"
        public_url: str,
    ):
        self.geoserver = GeoServerCloud(
            url=base_url,
            user=username,
            password=password,
        )
        self.public_url = public_url
        self.base_url = base_url
        self._auth = (username, password)

    async def workspace_exists(self, workspace_name: str) -> bool:
        """
        Check if a workspace exists in GeoServer.

        Args:
            workspace_name: Name of the workspace to check

        Returns:
            True if workspace exists, False otherwise
        """
        try:
            _content, status_code = self.geoserver.get_workspace(workspace_name)
            return status_code == 200
        except Exception:
            return False

    async def datastore_exists(self, workspace_name: str, datastore_name: str) -> bool:
        """
        Check if a datastore exists in a workspace.

        Args:
            workspace_name: Name of the workspace
            datastore_name: Name of the datastore to check

        Returns:
            True if datastore exists, False otherwise
        """
        try:
            _content, status_code = self.geoserver.get_pg_datastore(workspace_name, datastore_name)
            return status_code == 200
        except Exception:
            return False

    async def create_workspace(
        self,
        workspace_name: str,
        datastore_name: str,
        jndi_reference: str = "jdbc/datafeeder",
        pg_schema: str | None = None,
    ) -> WorkspaceCreationResult:
        """
        Create a workspace and optionally a JNDI datastore in GeoServer.

        Args:
            workspace_name: Name of the workspace to create
            datastore_name: Name for the datastore
            jndi_reference: JNDI reference for database connection (defaults to "jdbc/datafeeder")
            pg_schema: PostgreSQL schema name (defaults to workspace_name if None)

        Returns:
            WorkspaceCreationResult: Response with workspace and datastore information
        """
        return dm_create_workspace(
            geoserver=self.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=f"Datafeeder datasets for {workspace_name}",
        )

    async def create_layer(
        self,
        workspace_name: str,
        datastore_name: str,
        table_name: str,
        title: str,
        abstract: str,
        epsg: int = 4326,
        is_geographic: bool = True,
        bbox: dict[str, float] = {"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0},
    ) -> LayerCreationResult:
        """
        Create a WFS and WMS layer from a database table.

        Args:
            workspace_name: Name of the workspace
            datastore_name: Name of the datastore
            table_name: Database table name
            title: Layer title
            abstract: Layer description/abstract
            epsg: EPSG code for the coordinate reference system (defaults to 4326)
            is_geographic: Whether the data has valid geometry (defaults to True)

        Returns:
            LayerCreationResult: Response with layer information including WMS and WFS URLs

        Raises:
            Exception: If the table doesn't exist in the database or GeoServer fails to create the layer
        """
        # Create the feature type (layer) using data_manipulation module
        dm_create_layer(
            geoserver=self.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            title=title,
            abstract=abstract,
            epsg=epsg,
            is_geographic=is_geographic,
            bbox=bbox,
        )

        # Build service URLs using build_layer_urls
        urls = self.build_layer_urls(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=is_geographic,
        )

        layer_qualified_name = urls["layer_qualified_name"]

        # Build WMS and WFS from URLs
        wms = None
        wfs = None
        if is_geographic and "wms" in urls:
            wms = WMSUrls(
                base=urls["wms"]["base"],
                capabilities=urls["wms"]["capabilities"],
                getmap=urls["wms"]["getmap"],
                legend=urls["wms"]["legend"],
            )
        if is_geographic and "wfs" in urls:
            wfs = WFSUrls(
                base=urls["wfs"]["base"],
                capabilities=urls["wfs"]["capabilities"],
                getfeature=urls["wfs"]["getfeature"],
            )

        return LayerCreationResult(
            workspace=workspace_name,
            datastore=datastore_name,
            layer=table_name,
            layer_qualified_name=layer_qualified_name,
            table=table_name,
            wms=wms,
            wfs=wfs,
            ogcfeatures=urls["ogcfeatures"],
        )

    def build_layer_urls(
        self,
        workspace_name: str,
        table_name: str,
        is_geographic: bool = True,
    ) -> dict[str, Any]:
        """Build all layer service URLs without making any GeoServer API call.

        Returns all URLs for WMS, WFS, and OGC Features services.
        """
        layer_qualified_name = f"{workspace_name}:{table_name}"
        result: dict[str, Any] = {
            "layer_qualified_name": layer_qualified_name,
            "ogcfeatures": f"{self.public_url}/ogc/features/v1/collections/{layer_qualified_name}?f=json",
        }
        if is_geographic:
            result["wfs"] = {
                "base": f"{self.public_url}/{workspace_name}/wfs",
                "capabilities": f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetCapabilities",
                "getfeature": f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames={layer_qualified_name}",
            }
            result["wms"] = {
                "base": f"{self.public_url}/{workspace_name}/wms",
                "capabilities": f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetCapabilities",
                "getmap": f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetMap&layers={layer_qualified_name}",
                "legend": f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetLegendGraphic&layer={layer_qualified_name}&format=image/png",
            }
        return result

    def build_layer_urls_for_metadata(
        self,
        workspace_name: str,
        table_name: str,
        is_geographic: bool = True,
    ) -> dict[str, Any]:
        """Build layer service URLs for metadata without making any GeoServer API call.

        Returns only the keys consumed by MetadataService.create_and_publish_metadata().
        """
        # Get all URLs from build_layer_urls
        all_urls = self.build_layer_urls(
            workspace_name=workspace_name,
            table_name=table_name,
            is_geographic=is_geographic,
        )

        # Filter to keep only URLs needed for metadata
        result: dict[str, Any] = {
            "layer_qualified_name": all_urls["layer_qualified_name"],
            "ogcfeatures": all_urls["ogcfeatures"],
        }
        if "wfs" in all_urls:
            result["wfs"] = {
                "base": all_urls["wfs"]["base"],
                "capabilities": all_urls["wfs"]["capabilities"],
            }
        if "wms" in all_urls:
            result["wms"] = {
                "base": all_urls["wms"]["base"],
                "capabilities": all_urls["wms"]["capabilities"],
                "getmap": all_urls["wms"]["getmap"],
            }
        return result

    def update_layer_title(
        self,
        workspace_name: str,
        datastore_name: str,
        layer_name: str,
        title: str,
    ) -> None:
        """Update the title of a GeoServer feature type.

        Args:
            workspace_name: Name of the GeoServer workspace
            datastore_name: Name of the datastore
            layer_name: Name of the feature type to update
            title: New title to set

        Raises:
            GeoServerAclError: If the REST call returns an unexpected status code
        """
        url = self.geoserver.rest_service.rest_endpoints.featuretype(
            workspace_name, datastore_name, layer_name
        )
        payload = {"featureType": {"title": title}}
        response = self.geoserver.rest_service.rest_client.put(url, json=payload)
        if response.status_code not in (200, 201):
            raise GeoServerAclError(response.status_code, response.content.decode())

    def delete_layer(
        self,
        workspace_name: str,
        datastore_name: str,
        layer_name: str,
    ) -> None:
        """Delete a GeoServer feature type (layer).

        Treats 404 as success. Logs and suppresses other errors.

        Args:
            workspace_name: Name of the GeoServer workspace
            datastore_name: Name of the datastore
            layer_name: Name of the feature type / layer to delete
        """
        try:
            _content, status_code = self.geoserver.delete_feature_type(
                workspace_name, datastore_name, layer_name
            )
            if status_code not in (200, 204, 404):
                logger.error(
                    f"Unexpected status {status_code} deleting GeoServer layer "
                    f"{workspace_name}:{layer_name}"
                )
        except Exception as e:
            logger.error(
                f"Failed to delete GeoServer layer {workspace_name}:{layer_name}: {e}",
                exc_info=True,
            )

    @staticmethod
    def _to_geoserver_role(role: str) -> str:
        """Ensure role name has ROLE_ prefix as required by GeoServer ACL.

        geOrchestra strips ROLE_ from header values; GeoServer requires it.
        Idempotent: already-prefixed values pass through unchanged.
        The EVERYONE wildcard ("*") is passed through as-is.
        """
        if role == ACL_ROLE_EVERYONE:
            return role  # "*" is the GeoServer ACL wildcard — do not prefix
        upper = role.strip().upper()
        if not upper.startswith("ROLE_"):
            return f"ROLE_{upper}"
        return upper

    def sync_layer_acl(
        self,
        workspace: str,
        layer_name: str,
        privileges: list[tuple[str, RuleValue]],
    ) -> None:
        """Sync GeoServer ACL rules for a layer from DataKern sharing rules.

        Replaces the read and write ACL rules for the given layer.
        Roles with READ access are concatenated into the .r rule;
        roles with WRITE access into the .w rule.
        If no roles exist for an access level, the corresponding ACL rule is deleted.

        Args:
            workspace: GeoServer workspace name
            layer_name: GeoServer layer/feature type name
            privileges: List of (role_name, rule_value) tuples

        Raises:
            GeoServerAclError: If a GeoServer ACL API call fails.
        """
        # WRITE implies READ: roles with write access must also appear in the read rule.
        read_roles = [self._to_geoserver_role(r) for r, _ in privileges]
        write_roles = [self._to_geoserver_role(r) for r, v in privileges if v == RuleValue.WRITE]

        acl_layer_name = f"{workspace}.{layer_name}"

        for access_type, roles in [
            (AclAccessType.READ, read_roles),
            (AclAccessType.WRITE, write_roles),
        ]:
            if roles:
                self.acl_layer_set_rule(acl_layer_name, access_type, roles)
            else:
                try:
                    self.acl_layer_delete(acl_layer_name, access_type)
                except GeoServerAclError as e:
                    if e.status_code != 404:
                        raise

        logger.info(
            "Synced GeoServer ACL for %s:%s — read: %s, write: %s",
            workspace,
            layer_name,
            read_roles,
            write_roles,
        )

    async def update_layer_bbox(
        self,
        workspace_name: str,
        datastore_name: str,
        table_name: str,
        bbox: dict[str, float],
        native_epsg: int = 4326,
    ) -> None:
        """
        Update the bounding box of an existing GeoServer layer.

        Args:
            workspace_name: Name of the workspace
            datastore_name: Name of the datastore
            table_name: Database table name
            bbox: PostGIS ST_Extent string
            native_epsg: Native CRS EPSG code (defaults to 4326)
        """
        dm_update_layer_bbox(
            geoserver=self.geoserver,
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=table_name,
            bbox=bbox,
            native_epsg=native_epsg,
        )

    @staticmethod
    def make_acl_layer_name(workspace: str, layer: str) -> str:
        """Build the layer name string expected by the GeoServer ACL API.

        Args:
            workspace: The workspace name, e.g. "psc".
            layer: The layer name, e.g. "layer_1821c889_b558_4088_b2ca_65979501860fgeojson".

        Returns:
            A dot-separated string in the format "workspace.layer".
        """
        return f"{workspace.lower()}.{layer}"

    def acl_layer_get(self, layer_name: str, access_type: AclAccessType) -> list[str] | None:
        """Return the roles for a specific layer ACL rule from GeoServer.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type to look up (READ or WRITE).

        Returns:
            List of roles if the rule exists, None otherwise.
        """
        rule_key = f"{layer_name}.{access_type}"
        rest_client = self.geoserver.rest_service.rest_client  # type: ignore[attr-defined]
        response = rest_client.get("/rest/security/acl/layers", headers=_ACL_HEADERS)
        if response.status_code >= 400:
            raise GeoServerAclError(response.status_code, response.text)
        all_rules: dict[str, str] = response.json()
        roles_str = all_rules.get(rule_key)
        if roles_str is None:
            return None
        return [r.strip() for r in roles_str.split(",")]

    def _acl_write(
        self, method: str, body: dict[str, str], params: dict[str, str] | None = None
    ) -> None:
        """POST or PUT to GeoServer ACL layers endpoint via geoservercloud rest_client.

        Raises:
            GeoServerAclError: on any non-2xx HTTP response (except 409 on POST).
        """
        rest_client = self.geoserver.rest_service.rest_client  # type: ignore[attr-defined]
        if method == "POST":
            response = rest_client.post(
                "/rest/security/acl/layers", json=body, headers=_ACL_HEADERS, params=params
            )
            if response.status_code == 409:
                raise GeoServerAclError(response.status_code, response.text)
        else:
            response = rest_client.put(
                "/rest/security/acl/layers", json=body, headers=_ACL_HEADERS, params=params
            )
        if response.status_code >= 400:
            raise GeoServerAclError(response.status_code, response.text)

    def acl_layer_post(self, layer_name: str, access_type: AclAccessType, roles: list[str]) -> None:
        """Insert a new layer ACL rule in GeoServer.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type (READ or WRITE).
            roles: List of roles to grant, e.g. ["ROLE_IMPORT"].

        Raises:
            GeoServerAclError: 409 if the rule already exists.
        """
        rule_key = f"{layer_name}.{access_type}"
        self._acl_write("POST", {rule_key: ",".join(roles)})

    def acl_layer_put(self, layer_name: str, access_type: AclAccessType, roles: list[str]) -> None:
        """Update an existing layer ACL rule in GeoServer.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type (READ or WRITE).
            roles: New list of roles, e.g. ["ROLE_ADMINISTRATOR", "ROLE_IMPORT"].

        Raises:
            GeoServerAclError: 422 if the rule does not exist.
        """
        rule_key = f"{layer_name}.{access_type}"
        self._acl_write("PUT", {rule_key: ",".join(roles)})

    def acl_layer_delete(self, layer_name: str, access_type: AclAccessType) -> None:
        """Delete a layer ACL rule from GeoServer.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type to delete (READ or WRITE).
        """
        rule_key = f"{layer_name}.{access_type}"
        rest_client = self.geoserver.rest_service.rest_client  # type: ignore[attr-defined]
        response = rest_client.delete(f"/rest/security/acl/layers/{rule_key}", headers=_ACL_HEADERS)
        if response.status_code >= 400:
            raise GeoServerAclError(response.status_code, response.text)

    def acl_layer_set_rule(
        self, layer_name: str, access_type: AclAccessType, roles: list[str]
    ) -> None:
        """Set (replace) a layer ACL rule in GeoServer, overwriting any existing roles.

        Tries to insert the rule with POST. If GeoServer returns 409 (rule already exists),
        replaces it entirely with PUT — without merging with existing roles.
        Use this when DataKern is the source of truth and external rules should not be preserved.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type (READ or WRITE).
            roles: List of roles to set.
        """
        try:
            self.acl_layer_post(layer_name, access_type, roles)
        except GeoServerAclError as e:
            if e.status_code == 409:
                self.acl_layer_put(layer_name, access_type, roles)
            else:
                raise

    def acl_layer_remove_rule(
        self, layer_name: str, access_type: AclAccessType, roles: list[str]
    ) -> None:
        """Remove specific roles from an existing layer ACL rule in GeoServer.

        Fetches the current roles with GET, removes the given roles, then updates
        with PUT. If no roles remain after removal, deletes the rule entirely.

        Args:
            layer_name: The layer name in "workspace.layer" format, e.g. "geor.public_layer".
            access_type: The access type (READ or WRITE).
            roles: List of roles to remove.
        """
        existing = self.acl_layer_get(layer_name, access_type) or []
        remaining = [r for r in existing if r not in roles]
        if remaining:
            self.acl_layer_put(layer_name, access_type, remaining)
        else:
            self.acl_layer_delete(layer_name, access_type)
