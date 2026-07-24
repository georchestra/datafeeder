import os

from dotenv import load_dotenv
from playwright.sync_api import Page, expect

from common import login

load_dotenv()

FTP_HOST = os.environ["FTP_HOST"]
FTP_USER = os.environ["FTP_USER"]
FTP_PASSWORD = os.environ["FTP_PASSWORD"]
FTP_PATH = os.environ["FTP_PATH"]

BASIC_AUTH_URL = os.environ["BASIC_AUTH_URL"]
BASIC_AUTH_USER = os.environ["BASIC_AUTH_USER"]
BASIC_AUTH_PASSWORD = os.environ["BASIC_AUTH_PASSWORD"]


class TestDatafeederCredentials:

    def test_import_ftp(self, page: Page):
        expected_title = os.path.splitext(os.path.basename(FTP_PATH))[0]
        login(page)
        page.goto("/dataset/import")
        page.get_by_text("From an FTP").click()
        page.get_by_role("textbox").first.click()
        page.get_by_role("textbox").first.fill(FTP_HOST)
        page.locator("app-data-source-ftp form div").filter(has_text="Username* Password*").locator("input[type=\"text\"]").click()
        page.locator("app-data-source-ftp form div").filter(has_text="Username* Password*").locator("input[type=\"text\"]").fill(FTP_USER)
        page.locator("input[type=\"password\"]").click()
        page.locator("input[type=\"password\"]").fill(FTP_PASSWORD)
        page.get_by_label("/path/to/dataset.example").click()
        page.get_by_label("/path/to/dataset.example").fill(FTP_PATH)
        page.get_by_role("button", name="Configure the dataset").click()
        expect(page.get_by_placeholder("Enter a title for your dataset")).to_have_value(expected_title, timeout=15000)
        page.get_by_role("button", name="Validate the dataset").click()
        expect(page.locator("[data-test=\"recordTitleInput\"]")).to_have_value(expected_title, timeout=15000)
        self.remove_first_dataset(page)

    def test_import_url_with_basic_auth(self, page: Page):
        login(page)
        page.goto("/dataset/import")
        page.get_by_placeholder("https://").click()
        page.get_by_placeholder("https://").fill(BASIC_AUTH_URL)
        page.get_by_title("The URL I'm using has").locator("div").click()
        page.locator("input[type=\"text\"]").click()
        page.locator("input[type=\"text\"]").fill(BASIC_AUTH_USER)
        page.locator("input[type=\"password\"]").click()
        page.locator("input[type=\"password\"]").fill(BASIC_AUTH_PASSWORD)
        page.locator("gn-ui-url-input").get_by_role("button").click()
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
