"""Analyze forecast data and generate weather analytics HTML reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from config import (
    DEFAULT_LOCATION,
    EXTREME_HEAT_THRESHOLD_F,
    HIGH_HUMIDITY_THRESHOLD,
    STANDARD_PERIODS,
    WEATHER_REPORT_PATH,
)
from utils.helpers import parse_forecast_date
from utils.html_report import (
    escape_html,
    html_document,
    html_report_header,
    html_section,
    html_stat_cards,
    html_summary_box,
    html_table,
    parse_executed_at,
    percentage,
    split_values,
)

WEATHER_COLORS = {
    "Rain": "#3b82f6",
    "Heavy Rain": "#1e3a8a",
    "Cloudy": "#6b7280",
    "Sunny": "#f59e0b",
    "Thunderstorm": "#7c3aed",
    "Fog": "#9ca3af",
    "Snow": "#e0f2fe",
    "Ice": "#bae6fd",
}


def prepare_forecast_rows(rows: list[dict]) -> list[dict]:
    """Normalize in-memory forecast rows for analysis."""
    return [_normalize_row(row) for row in rows]


def _normalize_row(row: dict) -> dict:
    return {
        "date": str(row.get("date", "")).strip(),
        "period": str(row.get("period", "")).strip(),
        "weather": str(row.get("weather", "")).strip(),
        "high_temp": _to_float(row.get("high_temp")),
        "low_temp": _to_float(row.get("low_temp")),
        "real_feel": _to_float(row.get("real_feel")),
        "humidity": _to_float(row.get("humidity", row.get("precip_icon"))),
        "executed_at": str(row.get("executed_at", "")).strip(),
    }


def _to_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    return float(str(value).replace("°", "").replace("%", "").strip())


def _weather_color(weather: str) -> str:
    return WEATHER_COLORS.get(weather, "#64748b")


def _html_weather_table(headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{escape_html(header)}</th>" for header in headers)
    body_rows = []
    for condition, count, percentage in rows:
        color = _weather_color(condition)
        bar_width = percentage.rstrip("%")
        body_rows.append(
            "<tr>"
            f'<td><span class="weather-badge" style="background:{color}">{escape_html(condition)}</span></td>'
            f"<td>{escape_html(count)}</td>"
            f'<td><div class="bar-cell"><div class="bar" style="width:{bar_width}%;background:{color}"></div>'
            f'<span>{escape_html(percentage)}</span></div></td>'
            "</tr>"
        )
    return (
        '<table class="data-table weather-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def _html_alert_table(rows: list[list[str]]) -> str:
    header_html = "<th>Alert Type</th><th>Count</th>"
    body_rows = []
    for alert_type, count in rows:
        count_value = int(count)
        alert_class = "alert-active" if count_value > 0 else "alert-clear"
        body_rows.append(
            f'<tr class="{alert_class}">'
            f"<td>{escape_html(alert_type)}</td>"
            f"<td><strong>{escape_html(count)}</strong></td>"
            "</tr>"
        )
    return (
        '<table class="data-table alert-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def _weather_condition_counts(rows: list[dict]) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        conditions = split_values(row["weather"]) or [row["weather"]]
        for condition in conditions:
            counter[condition] += 1
    return counter


def _rows_for_period(rows: list[dict], period: str) -> list[dict]:
    matched_rows = []
    for row in rows:
        periods = split_values(row["period"]) or [row["period"]]
        if period in periods:
            matched_rows.append(row)
    return matched_rows


def _daily_temperature_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        date = row["date"]
        if date not in grouped:
            grouped[date] = {
                "date": date,
                "high_temp": row["high_temp"],
                "low_temp": row["low_temp"],
            }
            continue

        grouped[date]["high_temp"] = max(grouped[date]["high_temp"], row["high_temp"])
        grouped[date]["low_temp"] = min(grouped[date]["low_temp"], row["low_temp"])

    daily_rows = []
    for item in grouped.values():
        item["difference"] = round(item["high_temp"] - item["low_temp"], 1)
        daily_rows.append(item)

    daily_rows.sort(key=lambda item: parse_forecast_date(item["date"]))
    return daily_rows


def _forecast_snapshot(row: dict) -> tuple[str, str]:
    return (row["period"], row["weather"])


def _format_forecast_change(period: str, weather: str) -> str:
    return f"Period: {period} | Weather: {weather}"


def analyze_forecast_weather_changes(rows: list[dict]) -> list[dict]:
    """Track unique period and weather forecast snapshots per day in collection order."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["date"]:
            grouped[row["date"]].append(row)

    changes = []
    for date, day_rows in grouped.items():
        day_rows.sort(
            key=lambda row: (
                parse_executed_at(row["executed_at"]) or datetime.min,
                row["period"],
            )
        )

        unique_snapshots: list[tuple[str, str]] = []
        for row in day_rows:
            snapshot = _forecast_snapshot(row)
            if (snapshot[0] or snapshot[1]) and snapshot not in unique_snapshots:
                unique_snapshots.append(snapshot)

        if not unique_snapshots:
            continue

        initial_period, initial_weather = unique_snapshots[0]
        changed_snapshots = [
            {"period": period, "weather": weather}
            for period, weather in unique_snapshots[1:]
        ]
        changes.append(
            {
                "date": date,
                "initial_period": initial_period,
                "initial_weather": initial_weather,
                "changed_forecasts": changed_snapshots,
            }
        )

    changes.sort(key=lambda item: parse_forecast_date(item["date"]))
    return changes


def generate_weather_summary_html(
    rows: list[dict],
    location: str = DEFAULT_LOCATION,
) -> str:
    """Generate a styled HTML weather summary report from in-memory forecast data."""
    rows = prepare_forecast_rows(rows)

    if not rows:
        return html_document(
            title="Weather Summary Report",
            header="",
            sections_html="<p>No forecast data available.</p>",
        )

    sections = [
        html_section_1_1_coverage(rows, location),
        html_section_1_6_alerts(rows),
        html_section_1_2_weather_conditions(rows),
        html_section_1_3_temperature(rows),
        html_section_1_4_weather_by_period(rows),
        html_section_1_5_humidity(rows),
        html_section_1_6_forecast_weather_changes(rows),
    ]

    return html_document(
        title=f"Weather Summary Report - {location}",
        header=html_report_header("Weather Summary Report", "Weather Analytics"),
        sections_html="".join(sections),
    )


def html_section_1_1_coverage(rows: list[dict], location: str) -> str:
    unique_dates = sorted({row["date"] for row in rows if row["date"]}, key=parse_forecast_date)
    collected_periods = sorted(
        {
            period
            for row in rows
            for period in (split_values(row["period"]) or [row["period"]])
            if period
        }
    )
    executed_times = [
        parsed
        for row in rows
        if (parsed := parse_executed_at(row["executed_at"])) is not None
    ]
    start_time = min(executed_times).strftime("%Y-%m-%d %H:%M:%S") if executed_times else "N/A"
    end_time = max(executed_times).strftime("%Y-%m-%d %H:%M:%S") if executed_times else "N/A"
    period_pills = "".join(f'<span class="period-pill">{escape_html(p)}</span>' for p in collected_periods)

    content = (
        html_stat_cards(
            [
                ("Location", location),
                ("Forecast Period", f"{len(unique_dates)} days"),
                ("Total Forecast Days", str(len(unique_dates))),
                ("Total Forecast Records", str(len(rows))),
            ]
        )
        + "<h3>Time Periods Collected</h3>"
        + f"<div>{period_pills or 'N/A'}</div>"
        + "<h3>Data Collection Time Range</h3>"
        + html_table(
            ["Start Time", "End Time"],
            [[start_time, end_time]],
        )
    )
    return html_section(
        "coverage",
        "1.0 Forecast Coverage Summary",
        "Analyze collected weather forecast coverage.",
        content,
    )


def html_section_1_2_weather_conditions(rows: list[dict]) -> str:
    counts = _weather_condition_counts(rows)
    total = sum(counts.values())
    table_rows = [
        [condition, str(count), f"{percentage(count, total)}%"]
        for condition, count in counts.most_common()
    ]
    most_frequent = counts.most_common(1)[0][0] if counts else "N/A"
    thunderstorm_count = counts.get("Thunderstorm", 0)
    heavy_rain_count = counts.get("Heavy Rain", 0)
    other_alerts = [
        f"{name}: {count}"
        for name, count in counts.items()
        if name in {"Ice", "Sleet", "Snow", "Fog"}
    ]

    content = (
        _html_weather_table(["Weather Condition", "Count", "Percentage"], table_rows)
        + html_summary_box(
            [
                f"Most frequent weather condition: {most_frequent}",
                f"Thunderstorm count: {thunderstorm_count}",
                f"Heavy Rain count: {heavy_rain_count}",
                f"Other alerts: {', '.join(other_alerts) if other_alerts else 'None'}",
            ],
            tone="warning" if thunderstorm_count or heavy_rain_count else "info",
        )
    )
    return html_section(
        "weather-conditions",
        "1.2 Weather Condition Analysis",
        "Analyze weather distribution grouped by weather condition.",
        content,
    )


def html_section_1_6_forecast_weather_changes(rows: list[dict]) -> str:
    changes = analyze_forecast_weather_changes(rows)
    days_with_changes = [item for item in changes if item["changed_forecasts"]]

    table_headers = [
        "Forecast Date",
        "Initial Period",
        "Initial Weather",
        "Different Period & Weather",
    ]

    if days_with_changes:
        table_rows = [
            [
                item["date"],
                item["initial_period"],
                item["initial_weather"],
                "; ".join(
                    _format_forecast_change(
                        change["period"],
                        change["weather"],
                    )
                    for change in item["changed_forecasts"]
                ),
            ]
            for item in days_with_changes
        ]
        content = html_table(table_headers, table_rows)
        tone = "warning"
        summary = (
            f"Forecast period or weather changed on {len(days_with_changes)} of "
            f"{len(changes)} forecast day(s)."
        )
    else:
        content = html_table(
            table_headers,
            [["—", "—", "—", "No forecast period or weather changes detected"]],
        )
        tone = "success"
        summary = "No forecast period or weather changes detected across collected data."

    return html_section(
        "forecast-weather-changes",
        "1.6 Forecast Weather Changes",
        "Compare the first collected period and weather for each day with later differences.",
        content + html_summary_box([summary], tone=tone),
    )


def html_section_1_3_temperature(rows: list[dict]) -> str:
    high_temps = [row["high_temp"] for row in rows]
    low_temps = [row["low_temp"] for row in rows]
    real_feels = [row["real_feel"] for row in rows]
    daily_rows = _daily_temperature_rows(rows)
    max_high_row = max(daily_rows, key=lambda item: item["high_temp"])
    min_low_row = min(daily_rows, key=lambda item: item["low_temp"])

    stats_table = html_table(
        ["Metric", "Value"],
        [
            ["Maximum Temperature", f"{max(high_temps):.1f} F"],
            ["Minimum Temperature", f"{min(low_temps):.1f} F"],
            ["Average High Temp", f"{mean(high_temps):.1f} F"],
            ["Average Low Temp", f"{mean(low_temps):.1f} F"],
            ["Average Real Feel", f"{mean(real_feels):.1f} F"],
        ],
    )

    daily_table_rows = []
    for item in daily_rows:
        daily_table_rows.append(
            "<tr>"
            f"<td>{escape_html(item['date'])}</td>"
            f'<td class="temp-high">{item["high_temp"]:.1f}</td>'
            f'<td class="temp-low">{item["low_temp"]:.1f}</td>'
            f"<td>{item['difference']:.1f}</td>"
            "</tr>"
        )
    daily_table = (
        '<table class="data-table">'
        "<thead><tr><th>Date</th><th>High Temp</th><th>Low Temp</th><th>Difference</th></tr></thead>"
        f"<tbody>{''.join(daily_table_rows)}</tbody>"
        "</table>"
    )

    content = (
        "<h3>Temperature Statistics</h3>"
        + stats_table
        + '<div class="formula">Temperature Range = High Temperature - Low Temperature</div>'
        + "<h3>Daily Temperature Range</h3>"
        + daily_table
        + html_summary_box(
            [
                f"Highest temperature occurred on: {max_high_row['date']} ({max_high_row['high_temp']:.1f} F)",
                f"Lowest temperature occurred on: {min_low_row['date']} ({min_low_row['low_temp']:.1f} F)",
            ],
            tone="info",
        )
    )
    return html_section(
        "temperature",
        "1.3 Temperature Analysis",
        "Analyze temperature trends.",
        content,
    )


def html_section_1_4_weather_by_period(rows: list[dict]) -> str:
    period_rows = []
    period_stats = []

    for period in STANDARD_PERIODS:
        matched_rows = _rows_for_period(rows, period)
        if not matched_rows:
            continue

        avg_temp = mean((row["high_temp"] + row["low_temp"]) / 2 for row in matched_rows)
        avg_humidity = mean(row["humidity"] for row in matched_rows)
        common_weather = _weather_condition_counts(matched_rows).most_common(1)[0][0]
        color = _weather_color(common_weather)

        period_rows.append(
            "<tr>"
            f"<td><strong>{escape_html(period)}</strong></td>"
            f"<td>{avg_temp:.1f}</td>"
            f"<td>{avg_humidity:.1f}</td>"
            f'<td><span class="weather-badge" style="background:{color}">{escape_html(common_weather)}</span></td>'
            "</tr>"
        )
        period_stats.append(
            {
                "period": period,
                "avg_temp": avg_temp,
                "avg_humidity": avg_humidity,
                "common_weather": common_weather,
            }
        )

    empty_period_row = "<tr><td colspan='4'>N/A</td></tr>"
    period_table = (
        '<table class="data-table">'
        "<thead><tr><th>Period</th><th>Avg Temp</th><th>Avg Humidity</th><th>Common Weather</th></tr></thead>"
        f"<tbody>{''.join(period_rows) or empty_period_row}</tbody>"
        "</table>"
    )

    highest_temp_period = max(period_stats, key=lambda item: item["avg_temp"])["period"] if period_stats else "N/A"
    highest_humidity_period = (
        max(period_stats, key=lambda item: item["avg_humidity"])["period"] if period_stats else "N/A"
    )
    summary_items = [
        f"Highest temperature period: {highest_temp_period}",
        f"Highest humidity period: {highest_humidity_period}",
        *[
            f"{item['period']}: {item['common_weather']}"
            for item in period_stats
        ],
    ]

    content = (
        "<h3>Period Analysis</h3>"
        + period_table
        + html_summary_box(summary_items, tone="info")
    )
    return html_section(
        "by-period",
        "1.4 Weather By Time Period",
        "Analyze weather by daily periods.",
        content,
    )


def html_section_1_5_humidity(rows: list[dict]) -> str:
    humidity_values = [row["humidity"] for row in rows]
    high_humidity_count = sum(1 for value in humidity_values if value > HIGH_HUMIDITY_THRESHOLD)
    avg_humidity = mean(humidity_values)

    if avg_humidity > HIGH_HUMIDITY_THRESHOLD:
        humidity_condition = "High humidity overall"
        tone = "danger"
    elif avg_humidity >= 60:
        humidity_condition = "Moderate humidity overall"
        tone = "warning"
    else:
        humidity_condition = "Comfortable humidity overall"
        tone = "success"

    content = (
        html_stat_cards(
            [
                ("Maximum Humidity", f"{max(humidity_values):.1f}%"),
                ("Minimum Humidity", f"{min(humidity_values):.1f}%"),
                ("Average Humidity", f"{avg_humidity:.1f}%"),
            ]
        )
        + "<h3>Humidity Risk</h3>"
        + html_table(
            ["Metric", "Value"],
            [
                [f"High Humidity (>{HIGH_HUMIDITY_THRESHOLD}%) Records", str(high_humidity_count)],
                ["Percentage", f"{percentage(high_humidity_count, len(rows))}%"],
            ],
        )
        + html_summary_box([f"Humidity condition: {humidity_condition}"], tone=tone)
    )
    return html_section(
        "humidity",
        "1.5 Humidity Analysis",
        "Analyze humidity level.",
        content,
    )


def html_section_1_6_alerts(rows: list[dict]) -> str:
    weather_counts = _weather_condition_counts(rows)
    heavy_rain_count = sum(1 for row in rows if "Heavy Rain" in split_values(row["weather"]))
    thunderstorm_count = sum(1 for row in rows if "Thunderstorm" in split_values(row["weather"]))
    extreme_heat_count = sum(1 for row in rows if row["high_temp"] >= EXTREME_HEAT_THRESHOLD_F)
    high_humidity_count = sum(1 for row in rows if row["humidity"] > HIGH_HUMIDITY_THRESHOLD)

    risks = []
    if thunderstorm_count:
        risks.append("Thunderstorm")
    if heavy_rain_count:
        risks.append("Heavy Rain")
    if extreme_heat_count:
        risks.append("Extreme Heat")
    if high_humidity_count:
        risks.append("High Humidity")

    most_common_weather = weather_counts.most_common(1)[0][0] if weather_counts else "N/A"
    overall_condition = "Stable" if not risks else "Needs attention"
    tone = "success" if not risks else "danger"

    content = (
        _html_alert_table(
            [
                ["Heavy Rain", str(heavy_rain_count)],
                ["Thunderstorm", str(thunderstorm_count)],
                ["Extreme Heat", str(extreme_heat_count)],
                ["High Humidity", str(high_humidity_count)],
            ]
        )
        + html_summary_box(
            [
                f"Weather risks detected: {', '.join(risks) if risks else 'None'}",
                f"Overall weather condition: {overall_condition} (most common weather: {most_common_weather})",
            ],
            tone=tone,
        )
    )
    return html_section(
        "alerts",
        "1.1 Weather Alert Summary",
        "Identify abnormal weather conditions.",
        content,
    )


def save_weather_summary_html(
    rows: list[dict],
    output_path: str | Path = WEATHER_REPORT_PATH,
    location: str = DEFAULT_LOCATION,
) -> Path:
    """Generate and save the weather summary report to an HTML file."""
    report = generate_weather_summary_html(rows, location=location)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path
