"""Page object for the AccuWeather daily forecast page."""

from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from models.component.daily_card_component import DailyForecastCardComponent
from utils.dialog_helper import accept_privacy_promise_if_present, run_with_privacy_dismissal, safe_click

_DAILY_FORECAST_URL_MARKERS = ("daily-weather-forecast", "10-day-weather-forecast")


class DailyForecastPage:
    """Represents the AccuWeather 10-day forecast page."""

    TEN_DAY_MENU = (
        By.CSS_SELECTOR,
        'a.subnav-item[data-qa="daily"][data-pageid="daily"]',
    )
    DAILY_FORECAST_CARDS = (
        By.CSS_SELECTOR,
        ".daily-wrapper",
    )

    def __init__(self, driver, timeout: int = 30):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    @staticmethod
    def _is_daily_forecast_url(url: str) -> bool:
        return any(marker in url for marker in _DAILY_FORECAST_URL_MARKERS)

    @staticmethod
    def _daily_forecast_url_from_current(url: str) -> str | None:
        """Build the daily forecast URL from a location weather-forecast page."""
        if "/weather-forecast/" not in url:
            return None
        return url.replace("/weather-forecast/", "/daily-weather-forecast/", 1)

    def _wait_for_daily_forecast_page(self) -> None:
        """Wait until the daily forecast page and cards are loaded."""
        self.wait.until(lambda driver: self._is_daily_forecast_url(driver.current_url))
        self.wait.until(EC.presence_of_element_located(self.DAILY_FORECAST_CARDS))

    def _open_daily_forecast_via_url(self) -> bool:
        """Navigate directly to the daily forecast page when possible."""
        accept_privacy_promise_if_present(self.driver)
        current_url = self.driver.current_url

        if self._is_daily_forecast_url(current_url):
            self._wait_for_daily_forecast_page()
            return True

        daily_url = self._daily_forecast_url_from_current(current_url)
        if not daily_url:
            return False

        self.driver.get(daily_url)
        accept_privacy_promise_if_present(self.driver)
        try:
            self._wait_for_daily_forecast_page()
        except TimeoutException:
            return False
        return True

    def _open_daily_forecast_via_menu(self) -> None:
        """Open the daily forecast page by clicking the Daily subnav item."""
        ten_day_link = self.wait.until(EC.element_to_be_clickable(self.TEN_DAY_MENU))
        safe_click(self.driver, ten_day_link)
        accept_privacy_promise_if_present(self.driver)
        self._wait_for_daily_forecast_page()

    def select_ten_day_forecast(self) -> None:
        """Open the 10-day daily forecast page."""
        def open_ten_day_forecast() -> None:
            if self._open_daily_forecast_via_url():
                return
            self._open_daily_forecast_via_menu()

        run_with_privacy_dismissal(self.driver, open_ten_day_forecast)

    def get_daily_forecast_cards(self) -> list[DailyForecastCardComponent]:
        """Return the list of daily forecast cards."""
        card_elements = self.wait.until(
            EC.presence_of_all_elements_located(self.DAILY_FORECAST_CARDS)
        )
        return [DailyForecastCardComponent(card) for card in card_elements]

    @staticmethod
    def build_daily_forecast_data(
        cards: list[DailyForecastCardComponent],
    ) -> list[dict[str, str | int]]:
        """Return structured data for each daily forecast card."""
        return [{"day": index, **card.to_dict()} for index, card in enumerate(cards, start=1)]
