"""GeoServer publication of a dataset's final table."""

from data_manipulation.database import TableExtent
from geoservercloud.models.common import MetadataLink

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.geoserver import GeoServerService

logger = get_logger()

# JNDI resource of the data database, declared in GeoServer's jetty-env.xml
DATA_JNDI_REFERENCE = "jdbc/datafeeder"


class DatastoreSchemaMismatchError(Exception):
    """The datastore reads another schema than the table's."""

    def __init__(
        self, workspace: str, datastore: str, datastore_schema: str, table_schema: str
    ) -> None:
        super().__init__(
            f"Datastore {workspace}/{datastore} reads schema '{datastore_schema}', "
            f"not '{table_schema}'"
        )
        self.datastore_schema = datastore_schema


def build_metadata_links(integrity_link: IntegrityLink) -> list[MetadataLink] | None:
    """Links from a GeoServer layer to the metadata record of its dataset, if it has one."""
    if not integrity_link.metadata_id:
        return None
    settings = get_settings()
    return [
        MetadataLink(
            url=settings.GEONETWORK_XML_RECORD_URL.format(metadata_id=integrity_link.metadata_id),
            metadata_type="ISO19115:2003",
            mime_type="text/xml",
        ),
        MetadataLink(
            url=settings.DATAHUB_PUBLIC_URL.format(metadata_id=integrity_link.metadata_id),
            metadata_type="ISO19115:2003",
            mime_type="text/html",
        ),
    ]


async def publish_table(
    geoserver_service: GeoServerService,
    integrity_link: IntegrityLink,
    table_name: str,
    extent: TableExtent,
    *,
    datastore_name: str,
    pg_schema: str,
    jndi_reference: str,
) -> None:
    """Publish a table in the organization workspace, through a JNDI datastore reading pg_schema
    that is created with the workspace if missing, and set data_id. An existing datastore is never
    repointed: all its layers rely on it.

    Raises:
        DatastoreSchemaMismatchError: If the datastore reads another schema than pg_schema
    """
    workspace_name = integrity_link.integrity_organization.lower()

    datastore_schema = geoserver_service.get_datastore_schema(workspace_name, datastore_name)
    if datastore_schema is None:
        await geoserver_service.create_workspace(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            jndi_reference=jndi_reference,
            pg_schema=pg_schema,
        )
        logger.info(
            f"Created GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
            f"workspace={workspace_name}, datastore={datastore_name}, schema={pg_schema}, "
            f"jndi={jndi_reference}"
        )
    elif datastore_schema != pg_schema:
        raise DatastoreSchemaMismatchError(
            workspace_name, datastore_name, datastore_schema, pg_schema
        )

    await geoserver_service.create_layer(
        workspace_name=workspace_name,
        datastore_name=datastore_name,
        table_name=table_name,
        title=integrity_link.integrity_title or table_name,
        abstract=integrity_link.integrity_title or table_name,
        epsg=extent.epsg or 4326,
        is_geographic=extent.is_geographic,
        bbox=extent.bbox,
        metadata_links=build_metadata_links(integrity_link),
    )
    integrity_link.data_id = workspace_name + ":" + table_name
    logger.info(
        f"Created GeoServer layer for IntegrityLink {integrity_link.id}: "
        f"{integrity_link.data_id}, geographic={extent.is_geographic}, bbox={extent.bbox}"
    )


async def publish_final_table(
    geoserver_service: GeoServerService,
    integrity_link: IntegrityLink,
    final_table_name: str,
    target_schema: str,
    extent: TableExtent,
) -> None:
    """Publish a final table of the data database in the {workspace}_ds datastore, and set data_id.

    Raises:
        DatastoreSchemaMismatchError: If the datastore reads another schema than target_schema
    """
    workspace_name = integrity_link.integrity_organization.lower()
    await publish_table(
        geoserver_service,
        integrity_link,
        final_table_name,
        extent,
        datastore_name=f"{workspace_name}_ds",
        pg_schema=target_schema,
        jndi_reference=DATA_JNDI_REFERENCE,
    )
