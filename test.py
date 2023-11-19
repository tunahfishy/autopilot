from playwright.sync_api import Playwright, sync_playwright

from nav_tools import *


def run(playwright: Playwright):
    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = chromium.launch(headless=False) # Set headless to False to visualize the actions
    page = browser.new_page()
    page.set_viewport_size({"width": page.viewport_size["width"], "height": page.viewport_size["height"]})
    page.goto("https://www.amazon.com/")
    page.wait_for_timeout(2000)
    click_element(page, "#nav-holiday")
    page.wait_for_timeout(2000)
    type_and_submit(page, "#twotabsearchtextbox", "clothes")
    page.wait_for_timeout(2000)

    # page.screenshot(path="screenshot.png", full_page=True)
    scroll_down(page)
    page.wait_for_timeout(2000)
    scroll_up(page)
    page.wait_for_timeout(2000) 
    browser.close()

with sync_playwright() as playwright:
    run(playwright)

