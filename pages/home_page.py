"""Page object for the AccuWeather home page."""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import ACCUWEATHER_URL
from utils.dialog_helper import accept_privacy_promise_if_present, safe_click


class HomePage:
    """Represents the AccuWeather home page."""

    SEARCH_BAR = (By.CSS_SELECTOR, ".featured-search-bar")
    SEARCH_INPUT = (By.CSS_SELECTOR, ".featured-search-bar input.search-input")
    SEARCH_RESULT = (
        By.CSS_SELECTOR,
        ".featured-search-bar .search-bar-result, .featured-search-bar .search-result",
    )

    def __init__(self, driver, timeout: int = 30):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def open(self, url: str = ACCUWEATHER_URL) -> None:
        """Navigate to the AccuWeather home page."""
        self.driver.get(url)
        accept_privacy_promise_if_present(self.driver)
        self.wait.until(EC.presence_of_element_located(self.SEARCH_BAR))

    def search_location(self, location: str) -> None:
        """Search for a location on the home page."""
        accept_privacy_promise_if_present(self.driver)
        search_bar = self.wait.until(EC.presence_of_element_located(self.SEARCH_INPUT))
        safe_click(self.driver, search_bar)
        search_bar.clear()
        search_bar.send_keys(location)

        location_option = self._find_location_option(location)
        safe_click(self.driver, location_option)
        accept_privacy_promise_if_present(self.driver)
        self.wait_for_location_forecast_page(location)

    def _find_location_option(self, location: str):
        """Find the first matching location in the search dropdown."""
        location_xpath = f"//a[contains(normalize-space(.), '{location}')]"
        try:
            return self.wait.until(EC.element_to_be_clickable((By.XPATH, location_xpath)))
        except Exception:
            results = self.wait.until(
                EC.presence_of_all_elements_located(self.SEARCH_RESULT)
            )
            for result in results:
                if location.lower() in result.text.lower():
                    return result
            return results[0]

    def wait_for_location_forecast_page(self, location: str) -> None:
        """Wait until the location weather forecast page is loaded."""
        location_slug = location.lower().replace(" ", "-")
        accept_privacy_promise_if_present(self.driver)
        self.wait.until(
            lambda d: "weather-forecast" in d.current_url
            and location_slug in d.current_url
        )
