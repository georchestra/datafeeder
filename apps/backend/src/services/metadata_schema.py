from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Self

from lxml import etree

from src.core.logging import get_logger

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

logger = get_logger()


class MetadataSchema:
    """Base class/interface for schema-specific ISO metadata operations.

    Wraps the parsed record (``root``) an instance operates on, and the
    GeoNetwork API client used to upload it back. Provides no-op defaults;
    concrete schemas override what they support.
    """

    def __init__(self, root: _Element, gn_api: Any) -> None:
        self.root = root
        self.gn_api = gn_api
        self.updated = False

    def update_revision_date(self, revision_date: datetime) -> Self:
        return self

    def read_title(self) -> str | None:
        return None

    def update_online_resources_when_title_changed(self, title: str) -> Self:
        return self

    def add_online_resources_from_layer_urls_19115_3(self, layer_urls: dict[str, Any]) -> Self:
        return self

    def force_updated(self) -> Self:
        self.updated = True
        return self

    def upload_to_gn(self) -> None:
        """Serialize ``root`` and upload it to GeoNetwork, if it was updated.

        Uses the GeoNetwork upload endpoint (POST /records with
        ``uuidprocessing="OVERWRITE"``) — GeoNetwork does not expose a raw-PUT
        record update endpoint. OVERWRITE on an existing record updates the
        XML without altering its publication privileges.
        """
        if not self.updated:
            return
        xml_bytes = etree.tostring(self.root, xml_declaration=True, encoding="UTF-8")
        self.gn_api.upload_metadata(xml_bytes, uuidprocessing="OVERWRITE")


class NoopSchema(MetadataSchema):
    """Fallback handler for unrecognized/unsupported metadata schemas."""

    def update_revision_date(self, revision_date: datetime) -> Self:
        logger.warning("Unsupported schema for revision date update (root tag: %s)", self.root.tag)
        return self

    def read_title(self) -> str | None:
        logger.warning("Unsupported schema for title extraction (root tag: %s)", self.root.tag)
        return None
