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


class WMSUrls(BaseModel):
    """WMS service URLs."""

    capabilities: str
    getmap: str
    legend: str


class WFSUrls(BaseModel):
    """WFS service URLs."""

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
    wfs: WFSUrls
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
        jndi_reference: str = "jdbc/datakern",
        pg_schema: str | None = None,
    ) -> WorkspaceCreationResult:
        """
        Create a workspace and optionally a JNDI datastore in GeoServer.

        Args:
            workspace_name: Name of the workspace to create
            datastore_name: Name for the datastore
            jndi_reference: JNDI reference for database connection (defaults to "jdbc/datakern")
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
            description=f"DataKern datasets for {workspace_name}",
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
        bbox: str = "",
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

        # Build WMS from URLs
        wms = None
        if is_geographic and "wms" in urls:
            wms = WMSUrls(
                capabilities=urls["wms"]["capabilities"],
                getmap=urls["wms"]["getmap"],
                legend=urls["wms"]["legend"],
            )

        return LayerCreationResult(
            workspace=workspace_name,
            datastore=datastore_name,
            layer=table_name,
            layer_qualified_name=layer_qualified_name,
            table=table_name,
            wms=wms,
            wfs=WFSUrls(
                capabilities=urls["wfs"]["capabilities"],
                getfeature=urls["wfs"]["getfeature"],
            ),
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
            "wfs": {
                "capabilities": f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetCapabilities",
                "getfeature": f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames={layer_qualified_name}",
            },
        }
        if is_geographic:
            result["wms"] = {
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
            "wfs": {
                "capabilities": all_urls["wfs"]["capabilities"],
            },
        }
        if is_geographic and "wms" in all_urls:
            result["wms"] = {
                "capabilities": all_urls["wms"]["capabilities"],
                "getmap": all_urls["wms"]["getmap"],
            }
        return result

    async def update_layer_bbox(
        self,
        workspace_name: str,
        datastore_name: str,
        table_name: str,
        bbox: str,
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
