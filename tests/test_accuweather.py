"""Tests for AccuWeather automation."""

import pytest

from config import DEFAULT_LOCATION, MIN_FORECAST_DAYS
from flows.accuweather_flow import run_accuweather_forecast_flow


class TestAccuWeatherFlow:
    """End-to-end AccuWeather navigation and forecast verification."""

    @pytest.mark.smoke
    def test_accuweather_10_day_forecast_flow(self, driver):
        result = run_accuweather_forecast_flow(driver, location=DEFAULT_LOCATION)

        assert result.records_collected >= MIN_FORECAST_DAYS
        assert result.combined_data
        assert result.combined_data[0]["date"].strip() != ""
        assert "accuweather.com" in driver.current_url

        print(f"Passed: collected {result.records_collected} records at {result.executed_at}")
        print(f"Saved weather report to {result.weather_report_path}")
        print(f"Saved automation & QA report to {result.qa_report_path}")
