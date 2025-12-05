from geoservercloud import GeoServerCloud  # type: ignore[import-untyped]


class GeoServerService:
    """Service to interact with GeoServer API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080/geoserver",
        username: str = "admin",
        password: str = "admin",
    ):
        self.geoserver = GeoServerCloud(
            url=base_url,
            user=username,
            password=password,
        )

    async def create_workspace(
        self,
        workspace_name: str,
        datastore_name: str | None = None,
        jndi_reference: str = "jdbc/datakern",
        pg_schema: str | None = None,
    ) -> dict[str, str]:
        """
        Create a workspace and optionally a JNDI datastore in GeoServer.

        Args:
            workspace_name: Name of the workspace to create
            datastore_name: Optional name for the datastore (defaults to {workspace_name}_ds)
            jndi_reference: JNDI reference for database connection
            pg_schema: PostgreSQL schema name (defaults to workspace_name)

        Returns:
            dict: Response with workspace and datastore information
        """
        # Set defaults
        if datastore_name is None:
            datastore_name = f"{workspace_name}_ds"
        if pg_schema is None:
            pg_schema = workspace_name

        # Create workspace
        self.geoserver.create_workspace(workspace_name)

        # Create JNDI datastore
        self.geoserver.create_jndi_datastore(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
            description=f"DataKern datasets for {workspace_name}",
        )

        return {
            "workspace": workspace_name,
            "datastore": datastore_name,
            "schema": pg_schema,
        }

    async def create_layer(
        self,
        workspace_name: str,
        datastore_name: str,
        layer_name: str,
        table_name: str | None = None,
        title: str | None = None,
        abstract: str | None = None,
        enable_wms: bool = True,
        enable_wfs: bool = True,
    ) -> dict[str, str | dict[str, str | None] | None]:
        """
        Create a WFS and WMS layer from a database table.

        Args:
            workspace_name: Name of the workspace
            datastore_name: Name of the datastore
            layer_name: Name for the layer
            table_name: Database table name (defaults to layer_name)
            title: Layer title (defaults to layer_name)
            abstract: Layer description/abstract
            enable_wms: Enable WMS service for this layer
            enable_wfs: Enable WFS service for this layer

        Returns:
            dict: Response with layer information including WMS and WFS URLs

        Raises:
            Exception: If the table doesn't exist in the database or GeoServer fails to create the layer
        """
        # Set defaults
        if table_name is None:
            table_name = layer_name
        if title is None:
            title = layer_name

        try:
            # Create the feature type (layer) from the database table
            # Note: The layer_name is used as both the layer name and the native table name
            # GeoServer will look for the table in the schema configured in the datastore
            self.geoserver.create_feature_type(  # type: ignore[misc]
                layer_name=table_name,  # Use table_name as the layer name so it matches the DB table
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                title=title,
                abstract=abstract or layer_name,
            )
        except Exception as e:
            error_msg = str(e)
            # Check if it's a 500 error which might be the FreeMarker template bug
            if "500 Server Error" in error_msg:
                # Verify if the layer was actually created despite the error
                try:
                    # Try to get the layer - if it exists, the creation succeeded
                    self.geoserver.get_feature_type(
                        workspace_name=workspace_name,
                        datastore_name=datastore_name,
                        feature_type_name=table_name,
                    )
                    # Layer exists, the 500 was just the template error
                    pass
                except Exception:
                    # Layer doesn't exist, it's a real error
                    raise Exception(
                        f"Failed to create layer '{layer_name}' in GeoServer. "
                        f"The table '{table_name}' might not exist in schema '{workspace_name}', "
                        f"or the JNDI datastore is not properly configured. "
                        f"Error: {error_msg}"
                    ) from e
            else:
                raise Exception(
                    f"Failed to create layer '{layer_name}' in GeoServer. "
                    f"Make sure the table '{table_name}' exists in the database schema. "
                    f"Error: {error_msg}"
                ) from e

        # Build service URLs
        base_url = self.geoserver.url.rstrip("/")
        layer_qualified_name = f"{workspace_name}:{table_name}"

        # WMS GetCapabilities URL for the workspace
        wms_capabilities_url = (
            f"{base_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetCapabilities"
            if enable_wms
            else None
        )

        # WMS GetMap URL for the specific layer
        wms_getmap_url = (
            f"{base_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetMap&layers={layer_qualified_name}"
            if enable_wms
            else None
        )

        # WMS GetLegendGraphic URL for the layer
        wms_legend_url = (
            f"{base_url}/{workspace_name}/wms?service=WMS&version=1.3.0&request=GetLegendGraphic&layer={layer_qualified_name}&format=image/png"
            if enable_wms
            else None
        )

        # WFS GetCapabilities URL for the workspace
        wfs_capabilities_url = (
            f"{base_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetCapabilities"
            if enable_wfs
            else None
        )

        # WFS GetFeature URL for the specific layer
        wfs_getfeature_url = (
            f"{base_url}/{workspace_name}/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames={layer_qualified_name}"
            if enable_wfs
            else None
        )

        return {
            "workspace": workspace_name,
            "datastore": datastore_name,
            "layer": table_name,  # The actual layer name in GeoServer
            "layer_qualified_name": layer_qualified_name,
            "table": table_name,
            "wms": {
                "capabilities": wms_capabilities_url,
                "getmap": wms_getmap_url,
                "legend": wms_legend_url,
            }
            if enable_wms
            else None,
            "wfs": {
                "capabilities": wfs_capabilities_url,
                "getfeature": wfs_getfeature_url,
            }
            if enable_wfs
            else None,
        }
