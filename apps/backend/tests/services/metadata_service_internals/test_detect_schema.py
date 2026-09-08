from lxml import etree

from src.services.metadata_service import MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_NO_REVISION,
    SAMPLE_19139_NO_REVISION,
)


class TestDetectSchema:
    def test_detects_19115_3(self) -> None:
        root = etree.fromstring(SAMPLE_19115_3_NO_REVISION)
        assert MetadataService._detect_schema(root) == "19115-3"  # pyright: ignore[reportPrivateUsage]

    def test_detects_19139(self) -> None:
        root = etree.fromstring(SAMPLE_19139_NO_REVISION)
        assert MetadataService._detect_schema(root) == "19139"  # pyright: ignore[reportPrivateUsage]

    def test_returns_none_for_unsupported(self) -> None:
        root = etree.fromstring(b"<root/>")
        assert MetadataService._detect_schema(root) is None  # pyright: ignore[reportPrivateUsage]
