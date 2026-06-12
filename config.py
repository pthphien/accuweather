"""Shared project constants."""

from pathlib import Path

ACCUWEATHER_URL = "https://www.accuweather.com"
DEFAULT_LOCATION = "Ho Chi Minh City"
DEFAULT_INTERVAL_MINUTES = 60
PLANNED_EXECUTION_RUNS_PER_DAY = 24
DATA_RETENTION_DAYS = 3
# All execution timestamps use UTC so local runs and GitHub Actions match.
TIMESTAMP_TIMEZONE = "UTC"

AUTOMATION_NAME = "AccuWeather Forecast Automation"
TEST_OBJECTIVE = "Collect and analysis forecasts weather in 10-day section"
EXECUTION_FREQUENCY_LABEL = "Every 60 minutes in at least a day"
MIN_FORECAST_DAYS = 10

STANDARD_PERIODS = ("Morning", "Afternoon", "Evening", "Overnight")
VALID_PERIOD_VALUES = set(STANDARD_PERIODS) | {"All day", "Night"}
EXTREME_HEAT_THRESHOLD_F = 100
HIGH_HUMIDITY_THRESHOLD = 80

ERROR_LABELS = {
    "element_not_found": "Element Not Found",
    "timeout": "Timeout",
    "network_error": "Network Error",
    "page_load_failure": "Page Load Failure",
    "unexpected_error": "Unexpected Error",
}

QA_SECTION_2_DETAIL_TITLE = "2. Execution and Data Quality detail"

DATA_DIR = Path("data")
FORECAST_CSV_PATH = DATA_DIR / "daily_forecast.csv"
WEATHER_REPORT_PATH = DATA_DIR / "weather_summary_report.html"
QA_REPORT_PATH = DATA_DIR / "automation_qa_report.html"
EXECUTION_LOG_PATH = DATA_DIR / "execution_log.json"

CSV_FIELDNAMES = {
    "date": "Date",
    "period": "Period",
    "weather": "Weather",
    "high_temp": "High Temp (F)",
    "low_temp": "Low Temp (F)",
    "real_feel": "Real Feel (F)",
    "humidity": "Humidity (%)",
    "executed_at": "Executed At",
}

# Forecast columns from CSV_FIELDNAMES (excludes collection timestamp).
FORECAST_FIELDNAMES = {
    key: label for key, label in CSV_FIELDNAMES.items() if key != "executed_at"
}
