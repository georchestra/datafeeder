from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Self

from lxml import etree

from src.core.logging import get_logger

if TYPE_CHECKING:
    from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]

logger = get_logger()

# layer_urls key (GeoServerService.build_layer_urls_for_metadata) -> ISO protocol name
LAYER_URL_PROTOCOLS = (
    ("ogcfeatures", "OGC API Features"),
    ("wms", "OGC:WMS"),
    ("wfs", "OGC:WFS"),
)


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

    def replace_layer_online_resources(
        self, old_layer_name: str, layer_urls: dict[str, Any]
    ) -> Self:
        """Point the online resources of ``old_layer_name`` to the layer of ``layer_urls``."""
        return self

    def _replace_layer_links(
        self,
        resources: list[_Element],
        namespaces: dict[str, str],
        linkage_xpath: str,
        old_layer_name: str,
        layer_urls: dict[str, Any],
    ) -> Self:
        """Rewrite name and linkage of the CI_OnlineResource ``resources`` of ``old_layer_name``."""
        new_layer_name = layer_urls.get("layer_qualified_name", "")
        linkages = {
            protocol: urls["base"] if isinstance(urls, dict) else urls
            for key, protocol in LAYER_URL_PROTOCOLS
            if (urls := layer_urls.get(key))
        }
        for resource in resources:
            names = resource.xpath(
                "*[local-name()='name']/gco:CharacterString", namespaces=namespaces
            )
            if not names or names[0].text != old_layer_name:
                continue
            names[0].text = new_layer_name
            protocols = resource.xpath(
                "*[local-name()='protocol']/gco:CharacterString/text()", namespaces=namespaces
            )
            linkage_nodes = resource.xpath(linkage_xpath, namespaces=namespaces)
            if protocols and protocols[0] in linkages and linkage_nodes:
                linkage_nodes[0].text = linkages[protocols[0]]
            self.updated = True
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
