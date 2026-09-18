from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

logger = get_logger()


class MetadataSchema:
    """Base class/interface for schema-specific ISO metadata operations.

    Wraps the parsed record (``root``) an instance operates on. Provides
    no-op defaults; concrete schemas override what they support.
    """

    def __init__(self, root: _Element) -> None:
        self.root = root

    def update_revision_date(self, revision_date: datetime) -> bool:
        return False

    def get_title(self) -> str | None:
        return None

    def update_online_resources_when_title_changed(self, title: str) -> bool:
        return False

    def add_online_resources_from_layer_urls_19115_3(self, layer_urls: dict[str, Any]) -> bool:
        return False


class NoopSchema(MetadataSchema):
    """Fallback handler for unrecognized/unsupported metadata schemas."""

    def update_revision_date(self, revision_date: datetime) -> bool:
        logger.warning("Unsupported schema for revision date update (root tag: %s)", self.root.tag)
        return False

    def get_title(self) -> str | None:
        logger.warning("Unsupported schema for title extraction (root tag: %s)", self.root.tag)
        return None
