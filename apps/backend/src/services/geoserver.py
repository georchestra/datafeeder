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
            is_geographic=is_geographic,
            bbox=bbox,
        )

        # Build service URLs
        layer_qualified_name = f"{workspace_name}:{table_name}"

        wms = None
        if is_geographic:
            # WMS GetCapabilities URL for the workspace
            wms_capabilities_url = f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetCapabilities"

            # WMS GetMap URL for the specific layer
            wms_getmap_url = f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetMap&layers={layer_qualified_name}"

            # WMS GetLegendGraphic URL for the layer
            wms_legend_url = f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetLegendGraphic&layer={layer_qualified_name}&format=image/png"

            wms = WMSUrls(
                capabilities=wms_capabilities_url,
                getmap=wms_getmap_url,
                legend=wms_legend_url,
            )

        # WFS GetCapabilities URL for the workspace
        wfs_capabilities_url = f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetCapabilities"

        # WFS GetFeature URL for the specific layer
        wfs_getfeature_url = f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames={layer_qualified_name}"

        # OGC Features URL for the layer
        ogcfeatures_url = (
            f"{self.public_url}/ogc/features/v1/collections/{layer_qualified_name}?f=json"
        )

        return LayerCreationResult(
            workspace=workspace_name,
            datastore=datastore_name,
            layer=table_name,
            layer_qualified_name=layer_qualified_name,
            table=table_name,
            wms=wms,
            wfs=WFSUrls(
                capabilities=wfs_capabilities_url,
                getfeature=wfs_getfeature_url,
            ),
            ogcfeatures=ogcfeatures_url,
        )

    def build_layer_urls(
        self,
        workspace_name: str,
        table_name: str,
        is_geographic: bool = True,
    ) -> dict[str, Any]:
        """Build layer service URLs without making any GeoServer API call.

        Returns only the keys consumed by MetadataService.create_and_publish_metadata().
        """
        layer_qualified_name = f"{workspace_name}:{table_name}"
        result: dict[str, Any] = {
            "layer_qualified_name": layer_qualified_name,
            "ogcfeatures": f"{self.public_url}/ogc/features/v1/collections/{layer_qualified_name}?f=json",
            "wfs": {
                "capabilities": f"{self.public_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetCapabilities",
            },
        }
        if is_geographic:
            result["wms"] = {
                "capabilities": f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetCapabilities",
                "getmap": f"{self.public_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetMap&layers={layer_qualified_name}",
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
