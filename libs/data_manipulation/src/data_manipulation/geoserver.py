"""GeoServer layer creation utilities."""

from geoservercloud import GeoServerCloud  # type: ignore[import-untyped]
from geoservercloud.models.datastore import DataStore
from geoservercloud.models.featuretype import FeatureType
from geoservercloud.services import RestService
from pydantic import BaseModel  # type: ignore[import-untyped]
from pyproj import Transformer  # type: ignore[import-untyped]

from data_manipulation.utils import sanitize_name


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

    # Retrieve namespace URI for the workspace because it must match datastore one
    # So if the workspace already exists before calling geoserver.create_workspace,
    #   we get the correct namespace URI instead of assuming it follows a pattern
    namespace = geoserver.rest_service.rest_client.get(f"/rest/namespaces/{workspace_name}").json()[
        "namespace"
    ]["uri"]
    # Create JNDI datastore
    datastore = DataStore(
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
    geoserver.rest_service.create_datastore(workspace_name=workspace_name, datastore=datastore)

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
    bbox: dict[str, float] = {"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0},
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
            **bbox,
            "crs": {"$": f"EPSG:{epsg}", "@class": "projected"},
        }
        lat_lon_bounding_box = {
            **bbox,
            "crs": "EPSG:4326",
        }
        if is_geographic:
            native_bounding_box = _get_native_bbox_from_bbox_string(bbox, epsg)
            lat_lon_bounding_box = _get_ll_bbox_from_native_bbox(bbox, epsg)

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


def update_layer_bbox(
    geoserver: GeoServerCloud,  # type: ignore[reportUnknownVariableType]
    workspace_name: str,
    datastore_name: str,
    table_name: str,
    bbox: dict[str, float],
    native_epsg: int = 4326,
) -> None:
    """
    Update the bounding box of an existing GeoServer layer after data has been loaded.

    Args:
        geoserver: GeoServerCloud instance
        workspace_name: Name of the workspace
        datastore_name: Name of the datastore
        table_name: Database table name (feature type name)
        bbox: PostGIS ST_Extent string, e.g. "BOX(minx miny, maxx maxy)"
        native_epsg: Native CRS EPSG code (defaults to 4326)

    Raises:
        ValueError: If bbox string is invalid
        Exception: If GeoServer update fails
    """
    workspace_name = sanitize_name(workspace_name)
    table_name = sanitize_name(table_name)

    feature_type = FeatureType(
        name=table_name,
        native_name=table_name,
        workspace_name=workspace_name,
        store_name=datastore_name,
        srs=f"EPSG:{native_epsg}",
        epsg_code=native_epsg,
        native_bounding_box=_get_native_bbox_from_bbox_string(bbox, native_epsg),
        lat_lon_bounding_box=_get_ll_bbox_from_native_bbox(bbox, native_epsg),
    )

    rest_service = RestService(
        url=geoserver.url,  # type: ignore[reportUnknownMemberType]
        auth=geoserver.auth,  # type: ignore[reportUnknownMemberType]
    )
    rest_service.create_feature_type(feature_type)


def _get_native_bbox_from_bbox_string(
    parsed_bbox: dict[str, float], native_epsg: int
) -> dict[str, object]:
    return {
        **parsed_bbox,
        "crs": {"$": f"EPSG:{native_epsg}", "@class": "projected"},
    }


def _get_ll_bbox_from_native_bbox(
    native_bbox: dict[str, float], native_epsg: int
) -> dict[str, object]:
    if native_epsg != 4326:
        transformer = Transformer.from_crs(f"EPSG:{native_epsg}", "EPSG:4326", always_xy=True)
        minx_ll, miny_ll = transformer.transform(native_bbox["minx"], native_bbox["miny"])
        maxx_ll, maxy_ll = transformer.transform(native_bbox["maxx"], native_bbox["maxy"])
        return {
            "minx": minx_ll,
            "miny": miny_ll,
            "maxx": maxx_ll,
            "maxy": maxy_ll,
            "crs": "EPSG:4326",
        }
    else:
        return {
            **native_bbox,
            "crs": "EPSG:4326",
        }
