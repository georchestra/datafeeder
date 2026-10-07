import csv
from pathlib import Path
from typing import Any

import pytest
from common import (
    get_features_geojson,
    login,
    remove_first_dataset,
    validate_and_assert_feature_count,
)
from playwright.sync_api import Locator, Page, expect

FILES_DIR = Path(__file__).parent.parent / "files"

IMPORT_CASES = [
    {
        "id": "csv-no-geom",
        "file": "subventions_aux_associations.csv",
        "map": False,
        "timeout-seconds": 60,
        "expected_number_of_features": 6721,
    },
    {
        "id": "geojson-point",
        "file": "mel_mairie.json",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 127,
    },
    {
        "id": "geojson-line",
        "file": "travaux_7j_30k_troncon.json",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 264,
    },
    {
        "id": "geojson-polygon",
        "file": "bruit_zones_calmes.json",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 315,
    },
    {
        "id": "gpkg-single-layer",
        "file": "mel_mairie.gpkg",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 127,
    },
    {
        # Latin-1 .dbf with its codepage in a misnamed .cst instead of a .cpg
        "id": "shp-zip-wrong-encoding",
        "file": "mel_mairie.zip",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 127,
        "expected_values": ["Armentières", "Chéreng"],
    },
    {
        # "œ" only exists in Latin-9, not in Latin-1
        "id": "shp-zip-latin9-qgis",
        "file": "mel_mairie_latin9_qgis.zip",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 127,
        "expected_values": ["Armentières", "Annœullin", "Marcq-en-Barœul"],
    },
    {
        "id": "parquet",
        "file": "donnees-2023-reg02.parquet",
        "map": False,
        "timeout-seconds": 600,
        "expected_number_of_features": 2441268,
    },
    {
        "id": "geoparquet",
        "file": "a-epci2025.parquet",
        "map": True,
        "timeout-seconds": 60,
        "expected_number_of_features": 1269,
    },
]

ERROR_CASES = [
    {
        "id": "gpkg-multi-layer",
        "file": "bruit_travaux.gpkg",
        "timeout-seconds": 60,
    },
]

MEL_MAIRIE_FEATURES = 127


class TestDatafeederLocalFile:
    @pytest.mark.parametrize("case", IMPORT_CASES, ids=[c["id"] for c in IMPORT_CASES])
    def test_import_local_file(self, page: Page, case: dict[str, Any]):
        self.upload_and_configure(page, case["file"], case["id"], case["timeout-seconds"])
        if case["map"]:
            page.get_by_role("radio", name="Map").click()
            expect(page.locator("canvas")).to_be_visible()
        data_id = validate_and_assert_feature_count(
            page, case["expected_number_of_features"], case["timeout-seconds"]
        )
        if "expected_values" in case:
            values = {
                value
                for feature in get_features_geojson(page, data_id)["features"]
                for value in feature["properties"].values()
            }
            for expected_value in case["expected_values"]:
                assert expected_value in values
        remove_first_dataset(page)

    @pytest.mark.parametrize("case", ERROR_CASES, ids=[c["id"] for c in ERROR_CASES])
    def test_import_local_file_error(self, page: Page, case: dict[str, Any]):
        login(page)
        page.goto("/dataset/import")
        page.locator("gn-ui-file-input input[type='file']").set_input_files(
            FILES_DIR / case["file"]
        )
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_text("The data upload or analysis failed")).to_be_visible(
            timeout=case["timeout-seconds"] * 1000
        )
        expect(page.get_by_role("heading", name="Add a dataset")).to_be_visible()

    def test_import_csv_lat_lon_2154(self, page: Page):
        self.upload_and_configure(page, "mel_mairie_export_qgis.csv", "csv-lat-lon-2154", 30)
        configuration = page.locator("app-dataset-configuration")
        dropdowns = configuration.locator("gn-ui-dropdown-selector")
        self.select_choice(page, dropdowns.nth(1), "x")
        self.select_choice(page, dropdowns.nth(2), "y")
        dropdowns.nth(0).get_by_role("button").click()
        if page.locator("[role='listbox'] [data-cy-value='EPSG:2154']").count() == 0:
            page.keyboard.press("Escape")
            remove_first_dataset(page)
            pytest.skip("EPSG:2154 is not offered, add it to the PROJECTIONS setting")
        page.locator("[role='listbox'] [data-cy-value='EPSG:2154']").click()
        expect(page.locator('[data-test="config-saving-indicator"]')).to_be_hidden(timeout=15000)

        page.get_by_role("radio", name="Map").click()
        expect(page.locator("canvas")).to_be_visible()
        data_id = validate_and_assert_feature_count(page, MEL_MAIRIE_FEATURES, 30)
        self.assert_mel_mairie_coordinates(page, data_id, "mel_mairie_export_qgis.csv")
        remove_first_dataset(page)

    @pytest.mark.xfail(reason="WKT/WKB geometries in CSV are planned for V2.x", strict=False)
    def test_import_csv_wkt_2154(self, page: Page):
        self.upload_and_configure(page, "mel_mairie.csv", "csv-wkt-2154", 30)
        page.get_by_role("radio", name="Map").click()
        expect(page.locator("canvas")).to_be_visible()
        data_id = validate_and_assert_feature_count(page, MEL_MAIRIE_FEATURES, 30)
        self.assert_mel_mairie_coordinates(page, data_id, "mel_mairie_export_qgis.csv")
        remove_first_dataset(page)

    def upload_and_configure(self, page: Page, file_name: str, title: str, timeout: int):
        login(page)
        page.goto("/dataset/import")
        page.locator("gn-ui-file-input input[type='file']").set_input_files(FILES_DIR / file_name)
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(
            timeout=timeout * 1000
        )
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        page.get_by_placeholder("Enter a title for your dataset").fill(title)

    def select_choice(self, page: Page, dropdown: Locator, value: str):
        dropdown.get_by_role("button").click()
        page.locator(f"[role='listbox'] [data-cy-value='{value}']").click()
        expect(page.locator('[data-test="config-saving-indicator"]')).to_be_hidden(timeout=15000)

    def assert_mel_mairie_coordinates(self, page: Page, data_id: str, reference_csv: str):
        """Check every published point matches an X/Y of the reference CSV (EPSG:2154)."""
        with open(FILES_DIR / reference_csv, newline="", encoding="utf-8") as f:
            expected = {
                (round(float(row["X"])), round(float(row["Y"]))) for row in csv.DictReader(f)
            }
        features = get_features_geojson(page, data_id, srs_name="EPSG:2154")["features"]
        assert len(features) == MEL_MAIRIE_FEATURES
        for feature in features:
            assert feature["geometry"] is not None
            coordinates = feature["geometry"]["coordinates"]
            if feature["geometry"]["type"] == "MultiPoint":
                coordinates = coordinates[0]
            assert (round(coordinates[0]), round(coordinates[1])) in expected
