"""Forecast parsing, validation, and list utilities."""

from __future__ import annotations

import re
from datetime import datetime

from config import DATA_RETENTION_DAYS
from utils.time_helper import now, today

_PERIOD_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("late night", "Late Night"),
    ("early morning", "Early Morning"),
    ("overnight", "Overnight"),
    ("afternoon", "Afternoon"),
    ("morning", "Morning"),
    ("evening", "Evening"),
    ("midday", "Midday"),
    ("mid day", "Midday"),
    ("noon", "Midday"),
    ("night", "Night"),
)

# Strongest / most specific weather phrases first.
_WEATHER_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("thunderstorm", "Thunderstorm"),
    ("storm", "Thunderstorm"),
    ("lightning", "Thunderstorm"),
    ("snow", "Snow"),
    ("flurr", "Snow"),
    ("sleet", "Sleet"),
    ("ice", "Ice"),
    ("heavy rain", "Heavy Rain"),
    ("rain most", "Heavy Rain"),
    ("periods of rain", "Rain"),
    ("showers", "Rain"),
    ("shower", "Rain"),
    ("rain", "Rain"),
    ("drizzle", "Drizzle"),
    ("mostly cloudy", "Cloudy"),
    ("considerable cloudiness", "Cloudy"),
    ("cloudy", "Cloudy"),
    ("overcast", "Cloudy"),
    ("cloud", "Cloudy"),
    ("mostly sunny", "Sunny"),
    ("partly sunny", "Partly Sunny"),
    ("sunny", "Sunny"),
    ("sun", "Sun"),
    ("windy", "Windy"),
    ("breezy", "Breezy"),
    ("fog", "Fog"),
    ("mist", "Fog"),
)


def _contains_keyword(text: str, keyword: str) -> bool:
    """Match whole words/phrases only (e.g. 'noon' won't match inside 'afternoon')."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text) is not None


def _match_keywords(text: str, keywords: tuple[tuple[str, str], ...]) -> str:
    """Return comma-separated labels for keywords found in text, in priority order."""
    matched: list[str] = []
    seen: set[str] = set()

    for keyword, label in keywords:
        if _contains_keyword(text, keyword) and label not in seen:
            matched.append(label)
            seen.add(label)

    return ", ".join(matched)


# Temperature helpers

def parse_temperature(value: str) -> float:
    """Parse a temperature string (e.g. '72°', '/72°') into a numeric value."""
    return float(value.replace("°", "").replace("/", "").strip())

def parse_real_feel(value: str) -> float:
    """Parse a real feel string (e.g. 'Feels like 72°', '101°') into a numeric value."""
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace("°", ""))
    if not match:
        raise ValueError(f"Could not parse real feel value: {value!r}")
    return float(match.group())

def is_valid_temperature(temp: float, unit: str = "F") -> bool:
    """Check if a temperature value is within a reasonable range."""
    if unit == "F":
        return -130 <= temp <= 140
    if unit == "C":
        return -90 <= temp <= 60
    raise ValueError(f"Invalid unit: {unit}")

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round((celsius * 9 / 5) + 32, 1)


def to_fahrenheit(value: float) -> float:
    """Normalize a scraped temperature to Fahrenheit (handles °C or °F input)."""
    from_celsius = celsius_to_fahrenheit(value)
    as_fahrenheit = round(value, 1)

    celsius_interpretation_valid = is_valid_temperature(from_celsius, "F")
    fahrenheit_interpretation_valid = is_valid_temperature(as_fahrenheit, "F")

    if celsius_interpretation_valid and not fahrenheit_interpretation_valid:
        return from_celsius
    if fahrenheit_interpretation_valid and not celsius_interpretation_valid:
        return as_fahrenheit
    if celsius_interpretation_valid and fahrenheit_interpretation_valid:
        # Ambiguous (e.g. 35 → 35°F or 95°F). Values ≤ 60 are treated as °C.
        if value <= 60:
            return from_celsius
        return as_fahrenheit

    raise ValueError(f"Invalid temperature: {value}")


def parse_humidity(value: str) -> float:
    """Parse a humidity string (e.g. '70%') into a numeric value."""
    return float(value.replace("%", "").strip())

# Forecast normalization

def format_forecast_date(sub_date: str, year: int | None = None) -> str:
    """Format a month/day string into 'Wednesday, June 10 2026'."""
    month, day = map(int, sub_date.split("/"))
    if year is None:
        year = now().year

    date = datetime(year, month, day)
    return f"{date.strftime('%A')}, {date.strftime('%B')} {day} {year}"


def parse_weather_description(text: str) -> dict[str, str]:
    """Extract period and weather labels from a forecast phrase."""
    normalized = text.lower()
    period = _match_keywords(normalized, _PERIOD_KEYWORDS)

    return {
        "period": period or "All day",
        "weather": _match_keywords(normalized, _WEATHER_KEYWORDS),
    }


def formulize_daily_forecast_data(
    daily_data: list[dict[str, str | int]],
) -> list[dict[str, str | int | float]]:
    """Build formatted daily forecast data from scraped card data."""
    daily_forecast_data = []

    for data in daily_data:
        parsed = parse_weather_description(str(data["daily_card_content"]))

        high_temp = parse_temperature(str(data["high_temp"]))
        high_temp_fahrenheit = to_fahrenheit(high_temp)

        low_temp = parse_temperature(str(data["low_temp"]))
        low_temp_fahrenheit = to_fahrenheit(low_temp)

        real_feel = parse_real_feel(str(data["real_feel"]))
        real_feel_fahrenheit = to_fahrenheit(real_feel)

        if not is_valid_temperature(high_temp_fahrenheit, "F"):
            raise ValueError(f"Invalid high temperature: {data['high_temp']!r} → {high_temp_fahrenheit}°F")
        if not is_valid_temperature(low_temp_fahrenheit, "F"):
            raise ValueError(f"Invalid low temperature: {data['low_temp']!r} → {low_temp_fahrenheit}°F")
        if not is_valid_temperature(real_feel_fahrenheit, "F"):
            raise ValueError(f"Invalid real feel: {data['real_feel']!r} → {real_feel_fahrenheit}°F")

        daily_forecast_data.append({
            "date": format_forecast_date(str(data["sub_date"])),
            "period": parsed["period"],
            "weather": parsed["weather"],
            "high_temp": high_temp_fahrenheit,
            "low_temp": low_temp_fahrenheit,
            "real_feel": real_feel_fahrenheit,
            "humidity": parse_humidity(str(data["humidity"])),
        })

    return daily_forecast_data


def parse_forecast_date(date_text: str) -> datetime:
    """Parse a forecast date string such as 'Friday, June 12 2026'."""
    return datetime.strptime(date_text.strip(), "%A, %B %d %Y")


def _sort_value(value: object) -> datetime | float | str:
    """Convert a field value into a type that sorts correctly."""
    if value is None or value == "":
        return ""

    text = str(value).strip()
    date_formats = (
        "%A, %B %d %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    )

    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return float(text)
    except ValueError:
        return text.lower()


def combine_and_sort_dicts(
    first: list[dict],
    second: list[dict],
    sort_by: tuple[str, str],
    reverse: bool = False,
) -> list[dict]:
    """Combine two lists of dicts and sort by two fields."""
    combined_list = [*first, *second]
    return sorted(
        combined_list,
        key=lambda row: tuple(_sort_value(row.get(field, "")) for field in sort_by),
        reverse=reverse,
    )


def _parse_row_date(value: object) -> datetime | None:
    """Parse a row date value into a datetime, or return None if unsupported."""
    sort_value = _sort_value(value)
    if isinstance(sort_value, datetime):
        return sort_value
    return None


def remove_old_rows(
    data: list[dict],
    date_field: str = "date",
    max_retention_days: int = DATA_RETENTION_DAYS,
) -> list[dict]:
    """Remove rows where the date field is older than max_retention_days from today."""
    today_date = today()
    filtered_rows = []

    for row in data:
        row_date = _parse_row_date(row.get(date_field, ""))
        if row_date is None:
            continue

        if (today_date - row_date.date()).days <= max_retention_days:
            filtered_rows.append(row)

    return filtered_rows
