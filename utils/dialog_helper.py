"""Helpers for handling site dialogs during automation."""

from __future__ import annotations

from collections.abc import Callable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

CONSENT_BANNER_LOCATOR = (By.CSS_SELECTOR, "#ketch-consent-banner")
ACCEPT_BUTTON_LOCATOR = (By.CSS_SELECTOR, "#ketch-banner-button-primary")


def safe_click(driver: WebDriver, element: WebElement) -> None:
    """Scroll into view and click, using JavaScript if the click is intercepted."""
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        element,
    )
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _switch_to_default_content(driver: WebDriver) -> None:
    try:
        driver.switch_to.default_content()
    except Exception:
        pass


def _find_visible_accept_button(
    driver: WebDriver, timeout: float
) -> WebElement | None:
    """Return the Accept button only when the dialog is visible."""
    if timeout <= 0:
        for button in driver.find_elements(*ACCEPT_BUTTON_LOCATOR):
            if button.is_displayed():
                return button
        return None

    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(ACCEPT_BUTTON_LOCATOR)
        )
    except TimeoutException:
        return None


def _dismiss_dialog_in_current_context(
    driver: WebDriver, timeout: float
) -> bool:
    """Click Accept when the dialog is shown in the current document."""
    button = _find_visible_accept_button(driver, timeout)
    if button is None:
        return False

    safe_click(driver, button)

    try:
        WebDriverWait(driver, 2).until(
            EC.invisibility_of_element_located(CONSENT_BANNER_LOCATOR)
        )
    except TimeoutException:
        pass

    return True


def run_with_privacy_dismissal(
    driver: WebDriver, action: Callable[[], None]
) -> None:
    """Dismiss the privacy banner before and after an action if present."""
    accept_privacy_promise_if_present(driver)
    action()
    accept_privacy_promise_if_present(driver)


def accept_privacy_promise_if_present(driver: WebDriver, timeout: int = 2) -> bool:
    """
    Click Accept when the Privacy Promise dialog is visible.

    Returns True if the dialog was dismissed, False if no dialog was found (skipped).
    """
    _switch_to_default_content(driver)

    if _dismiss_dialog_in_current_context(driver, timeout):
        return True

    for iframe in driver.find_elements(By.CSS_SELECTOR, "iframe"):
        try:
            driver.switch_to.frame(iframe)
            if _dismiss_dialog_in_current_context(driver, timeout=0):
                return True
        except Exception:
            pass
        finally:
            _switch_to_default_content(driver)

    return False
