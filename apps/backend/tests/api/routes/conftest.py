from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def staging_metadata_deps() -> Generator[SimpleNamespace, None, None]:
    """Patch every dependency get_staging_metadata needs besides the IntegrityLink
    and staging table content, which each test configures itself via .load and
    .table."""
    with (
        patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging"),
        patch("src.api.routes.ingestion.staging.select"),
        patch("src.api.routes.ingestion.staging.Table") as mock_table,
        patch("src.api.routes.ingestion.staging._resolve_columns") as mock_resolve_cols,
        patch("src.api.routes.ingestion.staging._detect_original_projection") as mock_detect_proj,
        patch("src.api.routes.ingestion.staging.load_authorized_integrity_link") as mock_load,
    ):
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None
        yield SimpleNamespace(load=mock_load, table=mock_table)
