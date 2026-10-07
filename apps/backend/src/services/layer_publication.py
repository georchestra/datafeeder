"""GeoServer publication of a dataset's final table."""

from dataclasses import dataclass, field

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.utils import compute_bbox_from_postgis_stextent_string
from geoservercloud.models.common import MetadataLink
from sqlalchemy import MetaData, Table, func, select

from src.core.config import get_settings
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.geoserver import GeoServerService

logger = get_logger()


class DatastoreSchemaMismatchError(Exception):
    """The workspace datastore reads another schema than the table's."""

    def __init__(self, workspace: str, datastore_schema: str, table_schema: str) -> None:
        super().__init__(
            f"Datastore {workspace}_ds reads schema '{datastore_schema}', not '{table_schema}'"
        )
        self.datastore_schema = datastore_schema


@dataclass
class TableExtent:
    """Geometry information needed to publish a final table."""

    is_geographic: bool = False
    epsg: int | None = None
    bbox: dict[str, float] = field(
        default_factory=lambda: {"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0}
    )


def read_table_extent(table_name: str, schema: str) -> TableExtent:
    """SRID and extent of a final table (placeholder bbox if not geographic)."""
    table = Table(table_name, MetaData(schema=schema), autoload_with=data_engine)
    extent = TableExtent(is_geographic=DEFAULT_GEOMETRY_COLUMN in table.c)
    if extent.is_geographic:
        with data_engine.connect() as conn:
            geom = table.c[DEFAULT_GEOMETRY_COLUMN]
            extent.epsg = conn.execute(select(func.ST_SRID(geom)).limit(1)).scalar_one_or_none()
            bbox_result = conn.execute(select(func.ST_Extent(geom))).scalar_one_or_none()
            if bbox_result:
                extent.bbox = compute_bbox_from_postgis_stextent_string(bbox_result)
    return extent


async def publish_final_table(
    geoserver_service: GeoServerService,
    integrity_link: IntegrityLink,
    final_table_name: str,
    target_schema: str,
    extent: TableExtent,
) -> None:
    """Publish a final table in the organization workspace, creating it if missing, and set
    data_id. An existing datastore is never repointed: all the workspace layers rely on it.

    Raises:
        DatastoreSchemaMismatchError: If the datastore reads another schema than target_schema
    """
    settings = get_settings()
    workspace_name = integrity_link.integrity_organization.lower()
    datastore_name = f"{workspace_name}_ds"

    datastore_schema = geoserver_service.get_datastore_schema(workspace_name, datastore_name)
    if datastore_schema is None:
        await geoserver_service.create_workspace(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            pg_schema=target_schema,
        )
        logger.info(
            f"Created GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
            f"workspace={workspace_name}, datastore={datastore_name}, schema={target_schema}"
        )
    elif datastore_schema != target_schema:
        raise DatastoreSchemaMismatchError(workspace_name, datastore_schema, target_schema)

    metadata_links: list[MetadataLink] | None = None
    if integrity_link.metadata_id:
        metadata_links = [
            MetadataLink(
                url=settings.GEONETWORK_XML_RECORD_URL.format(
                    metadata_id=integrity_link.metadata_id
                ),
                metadata_type="ISO19115:2003",
                mime_type="text/xml",
            ),
            MetadataLink(
                url=settings.DATAHUB_PUBLIC_URL.format(metadata_id=integrity_link.metadata_id),
                metadata_type="ISO19115:2003",
                mime_type="text/html",
            ),
        ]

    await geoserver_service.create_layer(
        workspace_name=workspace_name,
        datastore_name=datastore_name,
        table_name=final_table_name,
        title=integrity_link.integrity_title or final_table_name,
        abstract=integrity_link.integrity_title or final_table_name,
        epsg=extent.epsg or 4326,
        is_geographic=extent.is_geographic,
        bbox=extent.bbox,
        metadata_links=metadata_links,
    )
    integrity_link.data_id = workspace_name + ":" + final_table_name
    logger.info(
        f"Created GeoServer layer for IntegrityLink {integrity_link.id}: "
        f"{integrity_link.data_id}, geographic={extent.is_geographic}, bbox={extent.bbox}"
    )
