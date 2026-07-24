from playwright.sync_api import Page


def login(page: Page, username: str = 'testadmin', password: str = 'testadmin'):
    page.goto("/datahub/")
    page.get_by_role("link", name="login").click()
    username_input = page.get_by_placeholder("Username")
    username_input.fill(username)
    username_input.press("Tab")
    password_input = page.get_by_placeholder("Password")
    password_input.fill(password)
    password_input.press("Enter")