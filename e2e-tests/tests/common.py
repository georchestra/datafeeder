import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from playwright.sync_api import Page, expect

FILES_DIR = Path(__file__).parent.parent / "files"

# Host under which the ingestion reaches the e2e machine: the files server (see
# conftest.files_base_url) and the stack's GeoServer. "localhost" works with the local
# executor (host backend, host-networked GDAL container); Airflow workers need e.g.
# "host.docker.internal".
E2E_HOST = os.environ.get("E2E_HOST", "localhost")
FILES_PORT = int(os.environ.get("E2E_FILES_PORT", "8765"))
GEOSERVER_URL = f"http://{E2E_HOST}:8080/geoserver"


def login(page: Page, username: str = "testadmin", password: str = "testadmin"):
    page.goto("/datahub/")
    page.get_by_role("link", name="login").click()
    username_input = page.get_by_placeholder("Username")
    username_input.fill(username)
    username_input.press("Tab")
    password_input = page.get_by_placeholder("Password")
    password_input.fill(password)
    password_input.press("Enter")


def validate_dataset(page: Page, timeout: int) -> str:
    """Click "Validate the dataset" and return the published layer's ``workspace:layer``."""
    with page.expect_response(
        lambda r: "/ingestion/process/" in r.url and r.request.method == "POST",
        timeout=timeout * 1000,
    ) as process_response_info:
        page.get_by_role("button", name="Validate the dataset").click()
    expect(page.locator('[data-test="recordTitleInput"]')).to_be_visible(timeout=timeout * 1000)
    integrity_link_id = process_response_info.value.json()["integrity_link_id"]
    # data_id is only set once the processing DAG has published the layer,
    # which may still be running when the metadata form shows up.
    deadline = time.monotonic() + timeout
    while True:
        integrity_link = page.request.get(
            f"/datafeeder-backend/ingestion/integrity-link/{integrity_link_id}"
        )
        expect(integrity_link).to_be_ok()
        data_id = integrity_link.json()["data_id"]
        if data_id:
            return data_id
        assert time.monotonic() < deadline, f"data_id not set on integrity link {integrity_link_id}"
        page.wait_for_timeout(1000)


def get_feature_count(page: Page, data_id: str) -> int:
    workspace, _ = data_id.split(":", 1)
    hits = page.request.get(
        f"/geoserver/{workspace}/wfs",
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": data_id,
            "resultType": "hits",
        },
    )
    expect(hits).to_be_ok()
    return int(ET.fromstring(hits.text()).attrib["numberMatched"])


def get_features_geojson(page: Page, data_id: str, srs_name: str | None = None) -> dict:
    workspace, _ = data_id.split(":", 1)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": data_id,
        "outputFormat": "application/json",
    }
    if srs_name:
        params["srsName"] = srs_name
    features = page.request.get(f"/geoserver/{workspace}/wfs", params=params)
    expect(features).to_be_ok()
    return features.json()


def validate_and_assert_feature_count(
    page: Page, expected_number_of_features: int | None, timeout: int
) -> str:
    data_id = validate_dataset(page, timeout)
    if expected_number_of_features is not None:
        number_matched = get_feature_count(page, data_id)
        print(f"hits: {number_matched} expected: {expected_number_of_features} for {data_id}")
        assert number_matched == expected_number_of_features
    return data_id
