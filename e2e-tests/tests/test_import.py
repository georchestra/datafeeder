from typing import Any

import pytest
from common import (
    GEOSERVER_URL,
    login,
    validate_and_assert_feature_count,
)
from playwright.sync_api import Page, expect

# Served by the files_base_url fixture: no dependency on a third-party host
IMPORT_CASES = [
    {
        "id": "parquet",
        "file": "a-epci2025.parquet",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 1269,
    },
    {
        "id": "geojson",
        "file": "mel_mairie.json",
        "map": True,
        "timeout-seconds": 30,
        "expected_number_of_features": 127,
    },
    {
        "id": "csv",
        "file": "subventions_aux_associations.csv",
        "map": False,
        "timeout-seconds": 30,
        "expected_number_of_features": 6721,
    },
    {
        "id": "gpkg",
        "file": "mel_mairie.gpkg",
        "map": True,
        "timeout-seconds": 30,
        "expected_number_of_features": 127,
    },
    {
        "id": "shp-zip",
        "file": "mel_mairie.zip",
        "map": True,
        "timeout-seconds": 30,
        "expected_number_of_features": 127,
    },
]
# geor:public_layer ships with the geOrchestra GeoServer of the stack
SERVICE_IMPORT_CASES = [
    {
        "id": "wfs",
        "type": "WFS",
        "url": f"{GEOSERVER_URL}/ows",
        "layer": "public_layer (geor:public_layer)",
        "map": True,
        "timeout-seconds": 30,
        "expected_number_of_features": 33,
    },
    {
        "id": "ogc-features",
        "type": "Service & OGC API",
        "url": f"{GEOSERVER_URL}/ogc/features/v1/collections/geor:public_layer/items?f=application%2Fgeo%2Bjson&limit=50",
        "layer": "geor:public_layer",
        "map": True,
        "timeout-seconds": 30,
        "expected_number_of_features": 33,
    },
]


class TestDatafeeder:
    @pytest.mark.parametrize("case", IMPORT_CASES, ids=[c["id"] for c in IMPORT_CASES])
    def test_import_url(self, page: Page, files_base_url: str, case: dict[str, Any]):
        login(page)
        page.goto("/dataset/import")
        page.get_by_placeholder("https://").click()
        page.get_by_placeholder("https://").fill(f"{files_base_url}/{case['file']}")
        page.locator("gn-ui-url-input").get_by_role("button").click()
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(
            timeout=case["timeout-seconds"] * 1000
        )
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        page.get_by_placeholder("Enter a title for your dataset").fill(case["id"])
        if case["map"]:
            page.get_by_role("radio", name="Map").click()
            expect(page.locator("canvas")).to_be_visible()
        validate_and_assert_feature_count(
            page, case.get("expected_number_of_features"), case["timeout-seconds"]
        )

    @pytest.mark.parametrize(
        "case", SERVICE_IMPORT_CASES, ids=[c["id"] for c in SERVICE_IMPORT_CASES]
    )
    @pytest.mark.usefixtures("advertised_public_layer")
    def test_import_service(self, page: Page, case: dict[str, Any]):
        login(page)
        page.goto("/dataset/import")
        page.get_by_text("Service & OGC API").click()
        page.get_by_label(case["type"]).check()
        page.get_by_placeholder("https://").click()
        page.get_by_placeholder("https://").fill(case["url"])
        page.locator("gn-ui-url-input").get_by_role("button").click()
        expect(page.get_by_placeholder("Select a layer")).to_be_visible(
            timeout=case["timeout-seconds"] * 1000
        )
        page.get_by_role("option", name=case["layer"]).click()
        page.get_by_role("heading", name="Add a dataset").click()
        page.get_by_role("button", name="Link to the service").click()
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(
            timeout=case["timeout-seconds"] * 1000
        )
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        page.get_by_placeholder("Enter a title for your dataset").fill(case["id"])
        page.get_by_role("radio", name="Map").click()
        expect(page.locator("canvas")).to_be_visible()

        validate_and_assert_feature_count(
            page, case.get("expected_number_of_features"), case["timeout-seconds"]
        )

    def test_import_database(self, page: Page, files_base_url: str):
        login(page)
        page.goto("/dataset/import")
        page.get_by_role("textbox", name="https://").click()
        page.get_by_role("textbox", name="https://").fill(
            f"{files_base_url}/subventions_aux_associations.csv"
        )
        page.locator("gn-ui-url-input").get_by_role("button").click()
        page.get_by_role("button", name="Configure the dataset").click()
        page.get_by_role("textbox", name="Enter a title for your dataset").click()
        page.get_by_role("textbox", name="Enter a title for your dataset").press("ControlOrMeta+a")
        page.get_by_role("textbox", name="Enter a title for your dataset").fill("mon dataset")
        validate_and_assert_feature_count(page, 6721, 15)
        page.goto("/dataset/import")
        page.get_by_label("From a database").check()
        page.get_by_role("textbox").first.click()
        page.get_by_role("textbox").first.fill("data")
        page.get_by_role("textbox").nth(1).click()
        page.get_by_role("textbox").nth(1).fill("mon_dataset")
        page.get_by_role("button", name="Configure the dataset").click()
        page.get_by_role("textbox", name="Enter a title for your dataset").click()
        page.get_by_role("textbox", name="Enter a title for your dataset").press("ControlOrMeta+a")
        page.get_by_role("textbox", name="Enter a title for your dataset").fill("mon dataset2")
        page.get_by_role("columnheader", name="nomattribuant").get_by_role("button").click()
        page.get_by_role("button", name="Filter column").click()
        page.get_by_placeholder("Values contain...").fill("Transports")
        page.locator(".absolute").click()
        page.locator("th.mat-column-id_datafeeder [data-action-button]").click()
        page.get_by_role("button", name="Remove column").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(
            timeout=15000
        )
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        validate_and_assert_feature_count(page, 49, 15)
