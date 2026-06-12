"""AccuWeather forecast collection flow."""

from __future__ import annotations

import time
from dataclasses import dataclass
from utils.time_helper import format_timestamp

from config import (
    CSV_FIELDNAMES,
    DATA_RETENTION_DAYS,
    DEFAULT_LOCATION,
    FORECAST_CSV_PATH,
    QA_REPORT_PATH,
    WEATHER_REPORT_PATH,
)
from pages.daily_forecast_page import DailyForecastPage
from pages.home_page import HomePage
from utils.analysis_automation_qa_report import save_automation_qa_html
from utils.analysis_forecast_data import save_weather_summary_html
from utils.execution_log import get_execution_runs, record_execution_run
from utils.file_helper import read_csv_rows, write_csv
from utils.helpers import (
    combine_and_sort_dicts,
    formulize_daily_forecast_data,
    remove_old_rows,
)


@dataclass
class FlowResult:
    """Result of a completed forecast collection run."""

    combined_data: list[dict]
    records_collected: int
    executed_at: str
    duration_seconds: float
    weather_report_path: str
    qa_report_path: str


def run_accuweather_forecast_flow(
    driver,
    location: str = DEFAULT_LOCATION,
) -> FlowResult:
    """Scrape forecast data, persist to CSV, and generate HTML reports."""
    start_time = time.perf_counter()
    # Step 1: Open the home page: https://www.accuweather.com/ and search for the location such as "Ho Chi Minh City"
    home_page = HomePage(driver)
    home_page.open()
    home_page.search_location(location)

    # Step 2: Open the 10-day forecast page
    forecast_page = DailyForecastPage(driver)
    forecast_page.select_ten_day_forecast()

    # Step 3: Get the daily forecast cards
    cards = forecast_page.get_daily_forecast_cards()
    daily_data = DailyForecastPage.build_daily_forecast_data(cards)
    daily_forecast_data = formulize_daily_forecast_data(daily_data)

    # Step 4: Save the daily forecast data to the CSV file
    executed_at = format_timestamp()
    for row in daily_forecast_data:
        row["executed_at"] = executed_at

    existing_data = []
    if FORECAST_CSV_PATH.exists():
        existing_data = read_csv_rows(FORECAST_CSV_PATH, CSV_FIELDNAMES)
        existing_data = remove_old_rows(existing_data, "date", DATA_RETENTION_DAYS)

    combined_data = combine_and_sort_dicts(
        existing_data,
        daily_forecast_data,
        ("date", "executed_at"),
    )
    write_csv(FORECAST_CSV_PATH, combined_data, CSV_FIELDNAMES)

    # Step 5: Generate the weather summary report
    duration_seconds = round(time.perf_counter() - start_time, 2)
    records_collected = len(daily_forecast_data)

    record_execution_run(
        {
            "execution_time": executed_at,
            "status": "passed",
            "records_collected": records_collected,
            "duration_seconds": duration_seconds,
            "errors": {},
        }
    )

    weather_report_path = save_weather_summary_html(
        combined_data,
        output_path=WEATHER_REPORT_PATH,
        location=location,
    )
    qa_report_path = save_automation_qa_html(
        combined_data,
        output_path=QA_REPORT_PATH,
        execution_runs=get_execution_runs(combined_data),
        location=location,
    )

    return FlowResult(
        combined_data=combined_data,
        records_collected=records_collected,
        executed_at=executed_at,
        duration_seconds=duration_seconds,
        weather_report_path=str(weather_report_path),
        qa_report_path=str(qa_report_path),
    )
