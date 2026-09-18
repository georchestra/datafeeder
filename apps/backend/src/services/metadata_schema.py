from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.core.logging import get_logger

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

logger = get_logger()


class MetadataSchema:
    @staticmethod
    def update_revision_date(root: _Element, revision_date: datetime) -> bool:
        return False

    @staticmethod
    def get_title(root: _Element) -> str | None:
        return None

    @staticmethod
    def update_online_resources_when_title_changed(root: _Element, title: str) -> _Element:
        return root

    @staticmethod
    def add_online_resources_from_layer_urls_19115_3(
        root: _Element, layer_urls: dict[str, Any]
    ) -> bool:
        return False


class NoopSchema(MetadataSchema):
    """Fallback handler for unrecognized/unsupported metadata schemas."""

    @staticmethod
    def update_revision_date(root: _Element, revision_date: datetime) -> bool:
        logger.warning("Unsupported schema for revision date update (root tag: %s)", root.tag)
        return False

    @staticmethod
    def get_title(root: _Element) -> str | None:
        logger.warning("Unsupported schema for title extraction (root tag: %s)", root.tag)
        return None


NOOP_SCHEMA = NoopSchema()
