from datetime import datetime, timezone

from lxml import etree

from src.services.metadata_service import NS_19115_3, MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_NO_REVISION,
    SAMPLE_19115_3_WITH_REVISION,
    SAMPLE_19115_3_WITH_REVISION_DATETIME,
)

CITATION_REVISION_XPATH_191153 = (
    "mdb:identificationInfo/mri:MD_DataIdentification"
    "/mri:citation/cit:CI_Citation"
    "/cit:date/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
    "/@codeListValue='revision']/cit:date/gco:DateTime"
)


class TestUpdateRevisionDate191153:
    """Tests for _update_revision_date_19115_3."""

    def test_insert_when_absent(self) -> None:
        root = etree.fromstring(SAMPLE_19115_3_NO_REVISION)
        rev_date = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        # citation-level data revision date is inserted as gco:DateTime
        dt_nodes = root.xpath(CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-03-15T14:30:00Z"

        # metadata-level mdb:dateInfo is NOT modified
        assert (
            len(
                root.xpath(
                    "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
                    "/@codeListValue='revision']",
                    namespaces=NS_19115_3,
                )
            )
            == 0
        )

    def test_replace_gco_date_with_datetime(self) -> None:
        """Existing gco:Date revision is replaced with gco:DateTime."""
        root = etree.fromstring(SAMPLE_19115_3_WITH_REVISION)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59Z"

        # metadata-level mdb:dateInfo[revision] is NOT modified
        mdb_nodes = root.xpath(
            "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
            "/@codeListValue='revision']/cit:date/gco:DateTime",
            namespaces=NS_19115_3,
        )
        assert len(mdb_nodes) == 1
        assert mdb_nodes[0].text == "2024-06-01T10:00:00"

    def test_replace_existing_datetime(self) -> None:
        """Existing gco:DateTime revision is updated in place."""
        root = etree.fromstring(SAMPLE_19115_3_WITH_REVISION_DATETIME)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59Z"
