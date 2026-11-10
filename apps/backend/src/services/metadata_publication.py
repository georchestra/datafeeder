"""GeoNetwork record creation for a new dataset."""

from typing import Any

from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.console_service import ConsoleService
from src.services.georchestra import GeorchestraContext
from src.services.metadata_service import MetadataService

logger = get_logger()


def publish_new_record(
    metadata_service: MetadataService,
    console_service: ConsoleService,
    integrity_link: IntegrityLink,
    author: GeorchestraContext,
    layer_urls: dict[str, Any] | None = None,
) -> None:
    """Create and publish the metadata record of a dataset, set its metadata_id, then give the
    record to the dataset owner (soft failure).

    The record contact is the dataset organization, as found in the console, else the author.

    Args:
        layer_urls: GeoServer service URLs (GeoServerService.build_layer_urls_for_metadata),
            None for a record without online resources

    Raises:
        Exception: If the record cannot be created
    """
    organization = console_service.get_organization(integrity_link.integrity_organization)
    org_name = organization.get("name") if organization else None
    contact_email = (organization.get("mail") if organization else None) or author.email

    metadata_service.create_and_publish_metadata(
        integrity_link,
        user_email=contact_email,
        user_first_name=org_name or author.firstname,
        user_last_name="" if org_name else author.lastname,
        organization_name=org_name or "",
        layer_urls=layer_urls,
    )
    integrity_link.metadata_id = str(integrity_link.id)
    logger.info("Metadata published for IntegrityLink %s", integrity_link.id)

    try:
        metadata_service.set_record_ownership(integrity_link)
    except Exception as e:
        logger.warning(
            "Failed to set metadata ownership for IntegrityLink %s: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
