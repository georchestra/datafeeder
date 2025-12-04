from geoservercloud import GeoServerCloud


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
    ) -> dict:
        """
        Create a workspace and optionally a JNDI datastore in GeoServer.

        Args:
            workspace_name: Name of the workspace to create
            datastore_name: Optional name for the datastore (defaults to datafeeder_{workspace_name})
            jndi_reference: JNDI reference for database connection
            pg_schema: PostgreSQL schema name (defaults to workspace_name)

        Returns:
            dict: Response with workspace and datastore information
        """
        # Set defaults
        if datastore_name is None:
            datastore_name = f"datafeeder_{workspace_name}"
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
            description=f"Datafeeder uploaded datasets for {workspace_name}",
        )

        return {
            "workspace": workspace_name,
            "datastore": datastore_name,
            "schema": pg_schema,
        }
