from lxml import etree

from src.services.metadata_schema import NOOP_SCHEMA
from src.services.metadata_schema_19115_3 import ISO_19115_3_SCHEMA
from src.services.metadata_schema_19139 import ISO_19139_SCHEMA
from src.services.metadata_service import detect_schema
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_NO_REVISION,
    SAMPLE_19139_NO_REVISION,
)


class TestDetectSchema:
    def test_detects_19115_3(self) -> None:
        root = etree.fromstring(SAMPLE_19115_3_NO_REVISION)
        assert detect_schema(root) is ISO_19115_3_SCHEMA

    def test_detects_19139(self) -> None:
        root = etree.fromstring(SAMPLE_19139_NO_REVISION)
        assert detect_schema(root) is ISO_19139_SCHEMA

    def test_returns_noop_for_unsupported(self) -> None:
        root = etree.fromstring(b"<root/>")
        assert detect_schema(root) is NOOP_SCHEMA
