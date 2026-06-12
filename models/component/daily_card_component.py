"""Component for a single daily forecast card on AccuWeather."""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class DailyForecastCardComponent:
    """Represents one daily forecast card."""

    DOW_DATE_SELECTOR = ".module-header.dow.date"
    SUB_DATE_SELECTOR = ".module-header.sub.date"
    HIGH_TEMP_SELECTOR = ".high"
    LOW_TEMP_SELECTOR = ".low"
    HUMIDITY_SELECTOR = ".precip"
    DAY_CARD_CONTENT_SELECTOR = ".half-day-card-content"
    DAILY_CARD_CONTENT_SELECTOR = ".phrase"
    PANEL_ITEM_REAL_FEEL = "RealFeel®"

    def __init__(self, card_element: WebElement):
        self._card = card_element

    def _text(self, selector: str) -> str:
        return self._card.find_element(By.CSS_SELECTOR, selector).text.strip()

    def _optional_text(self, selector: str) -> str:
        elements = self._card.find_elements(By.CSS_SELECTOR, selector)
        if not elements:
            return ""
        return (elements[0].get_attribute("innerText") or elements[0].text).strip()

    def _panel_item_value(self, label: str) -> str:
        items = self._card.find_elements(
            By.XPATH,
            f".//*[contains(@class, 'panel-item') and contains(., '{label}')]",
        )
        if not items:
            return ""
        return items[0].text.replace(label, "").strip()

    @property
    def dow_date(self) -> str:
        return self._text(self.DOW_DATE_SELECTOR)

    @property
    def sub_date(self) -> str:
        return self._text(self.SUB_DATE_SELECTOR)

    @property
    def high_temp(self) -> str:
        return self._text(self.HIGH_TEMP_SELECTOR)

    @property
    def low_temp(self) -> str:
        return self._text(self.LOW_TEMP_SELECTOR)

    @property
    def humidity(self) -> str:
        return self._optional_text(self.HUMIDITY_SELECTOR)

    @property
    def real_feel(self) -> str:
        return self._panel_item_value(self.PANEL_ITEM_REAL_FEEL)

    @property
    def daily_card_content(self) -> str:
        text = self._optional_text(self.DAILY_CARD_CONTENT_SELECTOR)
        if text:
            return text
        return self._optional_text(self.DAY_CARD_CONTENT_SELECTOR)

    def to_dict(self) -> dict[str, str]:
        """Return all card data as a dictionary."""
        return {
            "dow_date": self.dow_date,
            "sub_date": self.sub_date,
            "high_temp": self.high_temp,
            "low_temp": self.low_temp,
            "daily_card_content": self.daily_card_content,
            "real_feel": self.real_feel,
            "humidity": self.humidity,
        }
