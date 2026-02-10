"""GeoServer layer creation utilities."""

from geoservercloud import GeoServerCloud  # type: ignore[import-untyped]
from geoservercloud.models.datastore import PostGisDataStore
from geoservercloud.models.featuretype import FeatureType
from geoservercloud.services import RestService
from pydantic import BaseModel  # type: ignore[import-untyped]

from data_manipulation.utils import compute_bbox_from_postgis_stextent_string, sanitize_name


class WorkspaceCreationResult(BaseModel):  # type: ignore[misc]
    """Result of workspace creation."""

    workspace: str
    datastore: str
    pg_schema: str


def create_workspace(
    geoserver: GeoServerCloud,  # type: ignore[reportUnknownParameterType]
    workspace_name: str,
    datastore_name: str,
    jndi_reference: str,
    pg_schema: str | None,
    description: str | None = None,
) -> WorkspaceCreationResult:
    """
    Create a workspace and JNDI datastore in GeoServer.

    Args:
        geoserver: GeoServerCloud instance
        workspace_name: Name of the workspace to create
        datastore_name: Name for the datastore
        jndi_reference: JNDI reference for database connection
        pg_schema: PostgreSQL schema name (defaults to workspace_name if None)
        description: Description for the datastore

    Returns:
        WorkspaceCreationResult: Result with workspace, datastore, and schema names

    Raises:
        Exception: If workspace or datastore creation fails
    """
    # Sanitize workspace name
    workspace_name = sanitize_name(workspace_name)

    # Default schema to workspace name if not provided
    if pg_schema is None:
        pg_schema = workspace_name

    # Create workspace
    geoserver.create_workspace(workspace_name)  # type: ignore[reportUnknownMemberType]

    # Retrieve namespace URI for the workspace because ite must match datastore one
    # So if the workspace already exists, we get the correct namespace URI instead of assuming it follows a pattern
    namespace = geoserver.rest_service.rest_client.get(f"/rest/namespaces/{workspace_name}").json()[
        "namespace"
    ]["uri"]
    # Create JNDI datastore
    datastore = PostGisDataStore(
        workspace_name,
        datastore_name,
        connection_parameters={
            "dbtype": "postgis",
            "jndiReferenceName": jndi_reference,
            "schema": pg_schema,
            "namespace": namespace,
            "Expose primary keys": "true",
        },
        type="PostGIS (JNDI)",
        description=description,
    )
    geoserver.rest_service.create_jndi_datastore(workspace_name=workspace_name, datastore=datastore)

    return WorkspaceCreationResult(
        workspace=workspace_name,
        datastore=datastore_name,
        pg_schema=pg_schema,
    )


def create_layer(
    geoserver: GeoServerCloud,  # type: ignore[reportUnknownVariableType]
    workspace_name: str,
    datastore_name: str | None,
    table_name: str,
    title: str | None = None,
    abstract: str | None = None,
    epsg: int = 4326,
    is_geographic: bool = True,
    bbox: str = "",
) -> None:
    """
    Create a feature type (layer) in GeoServer from a database table.

    Args:
        geoserver: GeoServerCloud instance
        workspace_name: Name of the workspace
        datastore_name: Name of the datastore (defaults to workspace_name_ds if None)
        table_name: Database table name
        title: Layer title (defaults to table_name if None)
        abstract: Layer description/abstract (defaults to table_name if None)
        epsg: EPSG code for the coordinate reference system (defaults to 4326)
        is_geographic: Whether the data has valid geometry (defaults to True)
                       If False, fake bounds will be set

    Raises:
        Exception: If the table doesn't exist in the database or GeoServer fails to create the layer
    """
    # Sanitize names
    workspace_name = sanitize_name(workspace_name)
    table_name = sanitize_name(table_name)

    # Default datastore_name to workspace_name_ds if not provided
    if datastore_name is None:
        datastore_name = f"{workspace_name}_ds"

    # Default title and abstract to table_name if not provided
    if title is None:
        title = table_name
    if abstract is None:
        abstract = table_name

    try:
        native_bounding_box = {
            "minx": -1.0,
            "miny": -1.0,
            "maxx": 0.0,
            "maxy": 0.0,
            "crs": {"$": f"EPSG:{epsg}", "@class": "projected"},
        }
        lat_lon_bounding_box = {
            "minx": -1.0,
            "miny": -1.0,
            "maxx": 0.0,
            "maxy": 0.0,
            "crs": f"EPSG:{epsg}",
        }
        if is_geographic:
            parsed_bbox = compute_bbox_from_postgis_stextent_string(bbox)
            native_bounding_box["minx"] = lat_lon_bounding_box["minx"] = parsed_bbox["minx"]
            native_bounding_box["miny"] = lat_lon_bounding_box["miny"] = parsed_bbox["miny"]
            native_bounding_box["maxx"] = lat_lon_bounding_box["maxx"] = parsed_bbox["maxx"]
            native_bounding_box["maxy"] = lat_lon_bounding_box["maxy"] = parsed_bbox["maxy"]

        feature_type = FeatureType(
            name=table_name,
            native_name=table_name,
            workspace_name=workspace_name,
            store_name=datastore_name,
            title=title,
            abstract=abstract,
            srs=f"EPSG:{epsg}",
            epsg_code=epsg,
            native_bounding_box=native_bounding_box,
            lat_lon_bounding_box=lat_lon_bounding_box,
        )

        rest_service = RestService(
            url=geoserver.url,  # type: ignore[reportUnknownMemberType]
            auth=geoserver.auth,  # type: ignore[reportUnknownMemberType]
        )
        rest_service.create_feature_type(feature_type)

    except Exception as e:
        error_msg = str(e)
        try:
            # Verify if the layer was actually created despite the error
            # (the error may not be critical)
            geoserver.get_feature_type(  # type: ignore[reportUnknownMemberType]
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                feature_type_name=table_name,
            )
            return
        except Exception:
            raise Exception(
                f"Failed to create layer '{table_name}' in GeoServer. Error: {error_msg}"
            ) from e
