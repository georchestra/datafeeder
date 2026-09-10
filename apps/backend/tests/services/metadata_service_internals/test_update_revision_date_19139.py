from datetime import datetime, timezone

from lxml import etree

from src.services.metadata_service import NS_19139, MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19139_NO_REVISION,
    SAMPLE_19139_WITH_REVISION,
    SAMPLE_19139_WITH_REVISION_DATETIME,
)

CITATION_REVISION_XPATH_19139 = (
    "gmd:identificationInfo/gmd:MD_DataIdentification"
    "/gmd:citation/gmd:CI_Citation"
    "/gmd:date/gmd:CI_Date[gmd:dateType/gmd:CI_DateTypeCode"
    "/@codeListValue='revision']/gmd:date/gco:DateTime"
)


class TestUpdateRevisionDate19139:
    """Tests for _update_revision_date_19139."""

    def test_insert_when_absent(self) -> None:
        root = etree.fromstring(SAMPLE_19139_NO_REVISION)
        rev_date = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-03-15T14:30:00Z"

    def test_replace_gco_date_with_datetime(self) -> None:
        """Existing gco:Date revision is replaced with gco:DateTime."""
        root = etree.fromstring(SAMPLE_19139_WITH_REVISION)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59Z"

    def test_replace_existing_datetime(self) -> None:
        """Existing gco:DateTime revision is updated in place."""
        root = etree.fromstring(SAMPLE_19139_WITH_REVISION_DATETIME)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59Z"
