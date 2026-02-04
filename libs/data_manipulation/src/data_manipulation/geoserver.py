"""GeoServer layer creation utilities."""

import re

from geoservercloud import GeoServerCloud  # type: ignore[import-untyped]
from geoservercloud.models.featuretype import FeatureType
from geoservercloud.services import RestService
from pydantic import BaseModel  # type: ignore[import-untyped]

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

    # Create JNDI datastore
    geoserver.create_jndi_datastore(  # type: ignore[reportUnknownMemberType]
        workspace_name=workspace_name,
        datastore_name=datastore_name,
        jndi_reference=jndi_reference,
        pg_schema=pg_schema,
        description=description,
    )

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
        if is_geographic:
            m = re.match(
                r"BOX\(\s*([-\d\.eE]+)\s+([-\d\.\.eE]+)\s*,\s*([-\d\.eE]+)\s+([-\d\.eE]+)\s*\)",
                bbox,
            )
            if not m:
                raise ValueError("Invalid BOX WKT")

            minx, miny, maxx, maxy = map(float, m.groups())
            native_bounding_box = {
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "crs": {"$": f"EPSG:{epsg}", "@class": "projected"},
            }

            lat_lon_bounding_box = {
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "crs": f"EPSG:{epsg}",
            }
        else:
            # For non-geographic data, manually set fake bounds
            native_bounding_box = {
                "minx": 0,
                "miny": 0,
                "maxx": -1,
                "maxy": -1,
                "crs": {"$": f"EPSG:{epsg}", "@class": "projected"},
            }

            lat_lon_bounding_box = {
                "minx": -1,
                "miny": -1,
                "maxx": 0,
                "maxy": 0,
                "crs": f"EPSG:{epsg}",
            }

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
