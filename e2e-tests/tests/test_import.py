from playwright.sync_api import Page, expect

from common import login
import pytest

# Liste des liens à importer. Ajouter une entrée ici crée automatiquement un test.
IMPORT_CASES = [
    {
        "id": "parquet",
        "url": "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/formulaire-de-contact-de-la-ville-de-paris-messages-sur-13-mois-glissants/exports/parquet?lang=fr&timezone=Europe%2FBerlin",
        "map": False,
        "timeout-seconds": 120,
    },
    {
        "id": "geojson",
        "url": "https://www.data.gouv.fr/api/1/datasets/r/6b54f76f-f143-4e74-aecc-0af2a032428b",
        "map": True,
        "timeout-seconds": 30,
    },
    {
        "id": "csv",
        "url": "https://www.data.gouv.fr/api/1/datasets/r/47ac11c2-8a00-46a7-9fa8-9b802643f975",
        "map": False,
        "timeout-seconds": 30,
    },
    {
        "id": "gpkg",
        "url": "https://www.data.gouv.fr/api/1/datasets/r/12d32a68-e245-4e19-9215-7d07c699b6c0",
        "map": True,
        "timeout-seconds": 60,
    },
    {
        "id": "gpkg-big",
        "url": "https://www.data.gouv.fr/api/1/datasets/r/c83ba91e-2cd1-40f7-a632-eb0a76d83c49",
        "map": True,
        "timeout-seconds": 600,
    },
]
SERVICE_IMPORT_CASES = [
    {
        "id": "wfs-mel-tram",
        "type": "WFS",
        "url": "https://data.lillemetropole.fr/geoserver/ows",
        "layer": "Arrêts de tramway (mel_mobilite_et_transport:tramway_arrets)",
        "map": True,
        "timeout-seconds": 120,
        "expected_number_of_features":66
    },
    {
        "id": "wfs-dev-geo-irve",
        "type": "WFS",
        "url": "https://dev.geo2france.fr/geoserver/ows",
        "layer": "irve_geojson",
        "map": True,
        "timeout-seconds": 120,
        "expected_number_of_features": 18060
    },
    {
        "id": "wfs-dev-geo-limites",
        "type": "WFS",
        "url": "https://dev.geo2france.fr/geoserver/ows",
        "layer": "limites_communes_loi_littoral",
        "map": True,
        "timeout-seconds": 120,
        "expected_number_of_features": 57
    },
    {
        "id": "ogc-features",
        "type": "Service & OGC API",
        "url": "https://data.lillemetropole.fr/geoserver/ogc/features/v1/collections/mel:equipementsculturelsvilleneuvedascq/items?f=application%2Fgeo%2Bjson&limit=50",
        "layer": "mel:equipementsculturelsvilleneuvedascq",
        "map": True,
        "timeout-seconds": 30,
    }
]

class TestDatafeeder:

    @pytest.mark.parametrize("case", IMPORT_CASES, ids=[c["id"] for c in IMPORT_CASES])
    def test_import_url(self, page: Page, case):
        login(page)
        page.goto("/dataset/import")
        page.get_by_placeholder("https://").click()
        page.get_by_placeholder("https://").fill(case["url"])
        page.locator("gn-ui-url-input").get_by_role("button").click()
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(timeout=case["timeout-seconds"] * 1000)
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        if case["map"]:
            page.get_by_role("radio", name="Map").click()
            expect(page.locator("canvas")).to_be_visible()
        page.get_by_role("button", name="Validate the dataset").click()
        expect(page.locator("[data-test=\"recordTitleInput\"]")).to_be_visible(timeout=case["timeout-seconds"] * 1000)
        self.remove_first_dataset(page)


    @pytest.mark.parametrize("case", SERVICE_IMPORT_CASES, ids=[c["id"] for c in SERVICE_IMPORT_CASES])
    def test_import_service(self, page: Page, case):
        login(page)
        page.goto("/dataset/import")
        page.get_by_text("Service & OGC API").click()
        page.get_by_label(case["type"]).check()
        page.get_by_placeholder("https://").click()
        page.get_by_placeholder("https://").fill(case["url"])
        page.locator("gn-ui-url-input").get_by_role("button").click()
        expect(page.get_by_placeholder("Select a layer")).to_be_visible(timeout=case["timeout-seconds"] * 1000)
        page.get_by_role("option", name=case["layer"]).click()
        page.get_by_role("heading", name="Add a dataset").click()
        page.get_by_role("button", name="Link the service").click()
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(timeout=case["timeout-seconds"] * 1000)
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        page.get_by_role("radio", name="Map").click()
        expect(page.locator("canvas")).to_be_visible()
        page.get_by_role("button", name="Validate the dataset").click()
        expect(page.locator("[data-test=\"recordTitleInput\"]")).to_be_visible(timeout=case["timeout-seconds"] * 1000)
        # if case["expected_number_of_features"]:
        #     re

        self.remove_first_dataset(page)



    def test_import_database(self, page: Page):
        login(page)
        page.goto("/dataset/import")
        page.get_by_label("From a database").check()
        page.get_by_role("textbox").first.click()
        page.get_by_role("textbox").first.fill("staging")
        page.get_by_role("textbox").nth(1).click()
        page.get_by_role("textbox").nth(1).fill("layer_070ec496_1ef0_4775_8758_80de47584841")
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_role("heading", name="Configure the dataset")).to_be_visible(timeout=15000)
        expect(page.get_by_role("heading", name="Preview of the result")).to_be_visible()
        page.get_by_role("radio", name="Map").click()
        expect(page.locator("canvas")).to_be_visible()
        page.get_by_role("button", name="Validate the dataset").click()
        expect(page.locator("[data-test=\"recordTitleInput\"]")).to_be_visible(timeout=15000)
        self.remove_first_dataset(page)


    def remove_first_dataset(self, page: Page):
        page.goto("/dataset/")
        # page.get_by_label("Delete dataset").first.click()
        # page.get_by_role("button", name="Delete").click()






