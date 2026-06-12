"""WebDriver setup helpers."""

from __future__ import annotations

import sys
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

_LINUX_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_MAC_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and return a configured Chrome WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    user_agent = _LINUX_USER_AGENT if sys.platform == "linux" else _MAC_USER_AGENT
    options.add_argument(f"user-agent={user_agent}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


@contextmanager
def managed_driver(headless: bool = True):
    """Context manager that creates and quits a WebDriver."""
    driver = create_driver(headless=headless)
    driver.implicitly_wait(0)
    try:
        yield driver
    finally:
        driver.quit()
