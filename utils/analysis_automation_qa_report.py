"""Generate automation execution and QA data quality HTML reports."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from config import (
    AUTOMATION_NAME,
    DEFAULT_LOCATION,
    ERROR_LABELS,
    EXECUTION_FREQUENCY_LABEL,
    PLANNED_EXECUTION_RUNS_PER_DAY,
    QA_REPORT_PATH,
    FORECAST_FIELDNAMES,
    QA_SECTION_2_DETAIL_TITLE,
    TEST_OBJECTIVE,
    VALID_PERIOD_VALUES,
)
from utils.analysis_forecast_data import prepare_forecast_rows
from utils.execution_log import ERROR_TYPES, get_execution_runs
from utils.helpers import is_valid_temperature, parse_forecast_date
from utils.html_report import (
    automation_qa_styles,
    escape_html,
    html_document,
    html_report_header,
    html_section,
    html_section_group,
    html_summary_box,
    html_table,
    percentage,
    split_values,
)

# --- Shared helpers -----------------------------------------------------------

def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    return f"{seconds:.1f}s"


def _status_badge(status: str) -> str:
    tone = {
        "passed": "success",
        "failed": "danger",
        "skipped": "warning",
    }.get(status, "info")
    return f'<span class="status-badge {tone}">{escape_html(status.title())}</span>'


def _validation_status(passed: bool) -> str:
    return "Pass" if passed else "Fail"


def _detail_section(section_id: str, title: str, purpose: str, content: str) -> str:
    """Render a subsection inside section 2."""
    return html_section(section_id, title, purpose, content, heading_level=3)


def _html_overview_lines(items: list[tuple[str, str]]) -> str:
    lines = "".join(
        f'<div class="overview-line">'
        f'<span class="overview-label">{escape_html(label)}</span>'
        f'<span class="overview-value">{escape_html(value)}</span>'
        f"</div>"
        for label, value in items
    )
    return f'<div class="overview-lines">{lines}</div>'


# --- Analysis -----------------------------------------------------------------

def analyze_execution_summary(
    runs: list[dict],
    execution_frequency: str = EXECUTION_FREQUENCY_LABEL,
    planned_execution_runs: int = PLANNED_EXECUTION_RUNS_PER_DAY,
) -> dict:
    """Compute automation execution metrics."""
    successful = sum(1 for run in runs if run.get("status") == "passed")
    failed = sum(1 for run in runs if run.get("status") == "failed")
    skipped = sum(1 for run in runs if run.get("status") == "skipped")

    durations = [
        float(run["duration_seconds"])
        for run in runs
        if run.get("duration_seconds") is not None
    ]
    response_times = [
        float(run["duration_seconds"]) / max(int(run.get("records_collected", 0)), 1)
        for run in runs
        if run.get("duration_seconds") is not None and int(run.get("records_collected", 0)) > 0
    ]

    error_totals = Counter()
    for run in runs:
        for error_type, count in (run.get("errors") or {}).items():
            error_totals[error_type] += int(count)

    return {
        "automation_name": AUTOMATION_NAME,
        "test_objective": TEST_OBJECTIVE,
        "execution_frequency": execution_frequency,
        "planned_execution_runs": planned_execution_runs,
        "successful_runs": successful,
        "failed_runs": failed,
        "skipped_runs": skipped,
        "success_rate": percentage(successful, planned_execution_runs),
        "average_execution_time": mean(durations) if durations else None,
        "fastest_execution": min(durations) if durations else None,
        "slowest_execution": max(durations) if durations else None,
        "average_response_time": mean(response_times) if response_times else None,
        "error_totals": error_totals,
        "timeline": runs,
    }


def analyze_data_completeness(rows: list[dict]) -> dict:
    """Count missing values per required field."""
    missing_counts = {field_key: 0 for field_key in FORECAST_FIELDNAMES}
    valid_records = 0

    for row in rows:
        row_valid = True
        for field_key in FORECAST_FIELDNAMES:
            if _is_missing(row.get(field_key)):
                missing_counts[field_key] += 1
                row_valid = False
        if row_valid:
            valid_records += 1

    total_records = len(rows)
    return {
        "missing_counts": missing_counts,
        "valid_counts": {
            field_key: total_records - missing_counts[field_key]
            for field_key in FORECAST_FIELDNAMES
        },
        "valid_records": valid_records,
        "total_records": total_records,
        "completeness": percentage(valid_records, total_records) if total_records else 0.0,
    }


def _row_has_valid_date(row: dict) -> bool:
    try:
        parse_forecast_date(str(row["date"]))
        return True
    except ValueError:
        return False


def _row_has_valid_period(row: dict) -> bool:
    periods = split_values(str(row.get("period", ""))) or [str(row.get("period", ""))]
    return bool(periods) and all(period in VALID_PERIOD_VALUES for period in periods if period)


def _row_passes_validity(row: dict) -> bool:
    try:
        if _is_missing(row.get("date")) or _is_missing(row.get("weather")) or _is_missing(row.get("period")):
            return False

        parse_forecast_date(str(row["date"]))

        high_temp = float(row["high_temp"])
        low_temp = float(row["low_temp"])
        real_feel = float(row["real_feel"])
        humidity = float(row["humidity"])

        if not all(is_valid_temperature(temp, "F") for temp in (high_temp, low_temp, real_feel)):
            return False
        if not 0 <= humidity <= 100:
            return False
        return True
    except (ValueError, TypeError):
        return False


def analyze_data_validity(rows: list[dict]) -> dict:
    """Validate forecast records against QA rules."""
    total = len(rows)
    if total == 0:
        return {
            "rules": {
                "temperature_numeric": False,
                "humidity_range": False,
                "date_format_valid": False,
                "weather_exists": False,
                "period_valid": False,
            },
            "valid_records": 0,
            "validity_score": 0.0,
        }

    rules = {
        "temperature_numeric": all(
            not _is_missing(row.get("high_temp"))
            and not _is_missing(row.get("low_temp"))
            and not _is_missing(row.get("real_feel"))
            for row in rows
        ),
        "humidity_range": all(0 <= float(row["humidity"]) <= 100 for row in rows),
        "date_format_valid": all(not _is_missing(row.get("date")) for row in rows)
        and all(_row_has_valid_date(row) for row in rows),
        "weather_exists": all(not _is_missing(row.get("weather")) for row in rows),
        "period_valid": all(_row_has_valid_period(row) for row in rows),
    }
    valid_records = sum(1 for row in rows if _row_passes_validity(row))

    return {
        "rules": rules,
        "valid_records": valid_records,
        "validity_score": percentage(valid_records, total),
    }


def analyze_data_consistency(rows: list[dict]) -> dict:
    """Check temperature and period consistency."""
    high_gte_low_count = sum(
        1 for row in rows if float(row["high_temp"]) >= float(row["low_temp"])
    )
    valid_period_count = sum(1 for row in rows if _row_has_valid_period(row))

    total = len(rows)
    return {
        "high_gte_low_count": high_gte_low_count,
        "high_gte_low_passed": high_gte_low_count == total,
        "rule1_difference": total - high_gte_low_count,
        "rule2_difference": total - valid_period_count,
        "consistency_score": percentage(high_gte_low_count, total) if total else 0.0,
    }


def analyze_duplicates(rows: list[dict]) -> dict:
    """Detect duplicate forecast records."""
    seen: set[tuple] = set()
    duplicate_records = 0

    for row in rows:
        key = (
            row.get("date"),
            row.get("period"),
            row.get("weather"),
            row.get("high_temp"),
            row.get("low_temp"),
            row.get("real_feel"),
            row.get("humidity"),
            row.get("executed_at"),
        )
        if key in seen:
            duplicate_records += 1
        else:
            seen.add(key)

    total_records = len(rows)
    return {
        "total_records": total_records,
        "duplicate_records": duplicate_records,
        "unique_records": total_records - duplicate_records,
    }


def analyze_overall_quality(
    completeness: dict,
    validity: dict,
    consistency: dict,
) -> dict:
    """Compute category scores and overall QA status."""
    scores = {
        "completeness": completeness["completeness"],
        "validity": validity["validity_score"],
        "consistency": consistency["consistency_score"],
    }
    overall = round(mean(scores.values()), 1) if scores else 0.0

    if overall >= 90:
        status, tone = "Excellent", "success"
    elif overall >= 75:
        status, tone = "Good", "info"
    elif overall >= 60:
        status, tone = "Needs improvement", "warning"
    else:
        status, tone = "Critical", "danger"

    critical_issues = []
    if completeness["completeness"] < 100:
        critical_issues.append("Incomplete required fields detected")
    if not validity["rules"]["humidity_range"]:
        critical_issues.append("Humidity values outside 0-100 range")
    if not consistency["high_gte_low_passed"]:
        critical_issues.append("High temperature lower than low temperature in some records")

    return {
        "scores": scores,
        "overall_score": overall,
        "status": status,
        "tone": tone,
        "critical_issues": critical_issues or ["None"],
    }


# --- HTML sections ------------------------------------------------------------

def _section_1_1_execution_overview(execution: dict) -> str:
    content = _html_overview_lines(
        [
            ("Automation name", execution["automation_name"]),
            ("Test objective", execution["test_objective"]),
            ("Execution Frequency", execution["execution_frequency"]),
            ("Planned Execution Runs", str(execution["planned_execution_runs"])),
            ("Successful Runs", str(execution["successful_runs"])),
            ("Skipped Runs", str(execution["skipped_runs"])),
            ("Success Rate", f"{execution['success_rate']}%"),
        ]
    )
    return html_section(
        "execution-overview",
        "1.1 Test Execution Overview",
        "Show automation framework execution status and reliability.",
        content,
    )


def _section_1_2_overall_quality(quality: dict) -> str:
    scores = quality["scores"]
    content = (
        html_table(
            ["Category", "Score"],
            [
                ["Completeness", f"{scores['completeness']}%"],
                ["Validity", f"{scores['validity']}%"],
                ["Consistency", f"{scores['consistency']}%"],
            ],
        )
        + '<div class="score-card"><div>Overall Data Quality Score</div>'
        + f'<div class="score-value">{quality["overall_score"]}%</div></div>'
        + html_summary_box(
            [
                f"Data quality status: {quality['status']}",
                f"Critical Issues: {', '.join(quality['critical_issues'])}",
            ],
            tone=quality["tone"],
        )
    )
    return html_section(
        "overall-quality",
        "1.2 Overall Data Quality Score",
        "Combined QA score and final summary.",
        content,
    )


def _build_timeline_table(execution: dict) -> str:
    rows = []
    for run in reversed(execution["timeline"][-20:]):
        status = str(run.get("status", "unknown"))
        row_class = "timeline-passed" if status == "passed" else "timeline-failed"
        rows.append(
            f"<tr class='{row_class}'>"
            f"<td>{escape_html(run.get('execution_time', 'N/A'))}</td>"
            f"<td>{_status_badge(status)}</td>"
            f"<td>{escape_html(str(run.get('records_collected', 0)))}</td>"
            f"<td>{escape_html(_format_duration(run.get('duration_seconds')))}</td>"
            f"</tr>"
        )

    body = "".join(rows) or "<tr><td colspan='4'>No execution history</td></tr>"
    return (
        '<table class="data-table"><thead><tr>'
        "<th>Execution Time</th><th>Status</th><th>Records Collected</th><th>Duration</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def _section_2_1_execution_timeline(execution: dict) -> str:
    return _detail_section(
        "execution-timeline",
        "2.1 Execution Timeline",
        "Recent automation execution history.",
        _build_timeline_table(execution),
    )


def _section_2_2_automation_performance(execution: dict) -> str:
    content = html_table(
        ["Metric", "Value"],
        [
            ["Average Execution Time", _format_duration(execution["average_execution_time"])],
            ["Fastest Execution", _format_duration(execution["fastest_execution"])],
            ["Slowest Execution", _format_duration(execution["slowest_execution"])],
            ["Average Response Time", _format_duration(execution["average_response_time"])],
        ],
    )
    return _detail_section(
        "automation-performance",
        "2.2 Automation Performance",
        "Execution timing and responsiveness metrics.",
        content,
    )


def _section_2_3_error_summary(execution: dict) -> str:
    rows = [
        [ERROR_LABELS[error_type], str(execution["error_totals"].get(error_type, 0))]
        for error_type in ERROR_TYPES
    ]
    return _detail_section(
        "error-summary",
        "2.3 Error Summary",
        "Aggregated automation error counts.",
        html_table(["Error Type", "Count"], rows),
    )


def _section_2_4_data_completeness(completeness: dict) -> str:
    total_records = completeness["total_records"]
    field_rows = [
        [label, f"{completeness['valid_counts'][field_key]}/{total_records}"]
        for field_key, label in FORECAST_FIELDNAMES.items()
    ]
    content = (
        html_table(["Required Field", "Valid Count"], field_rows)
        + html_summary_box(
            [f"Completeness Score: {completeness['completeness']}%"],
            tone="success" if completeness["completeness"] == 100 else "warning",
        )
    )
    return _detail_section(
        "data-completeness",
        "2.4 Data Completeness",
        "Measure presence of required forecast fields.",
        content,
    )


def _section_2_5_data_validity(validity: dict) -> str:
    rules = validity["rules"]
    rows = [
        ["Temperature is numeric", _validation_status(rules["temperature_numeric"])],
        ["Humidity between 0-100", _validation_status(rules["humidity_range"])],
        ["Date format valid", _validation_status(rules["date_format_valid"])],
        ["Weather value exists", _validation_status(rules["weather_exists"])],
        ["Period value valid", _validation_status(rules["period_valid"])],
    ]
    tone = "success" if validity["validity_score"] >= 95 else "warning"
    content = (
        html_table(["Validation Rule", "Status"], rows)
        + html_summary_box([f"Validity Score: {validity['validity_score']}%"], tone=tone)
    )
    return _detail_section(
        "data-validity",
        "2.5 Data Validity",
        "Validate forecast values against QA rules.",
        content,
    )


def _section_2_6_data_consistency(consistency: dict) -> str:
    content = (
        html_table(
            ["Rule", "Difference"],
            [
                ["Rule 1: High Temperature >= Low Temperature", str(consistency["rule1_difference"])],
                ["Rule 2: Valid Period Values", str(consistency["rule2_difference"])],
            ],
        )
        + html_summary_box(
            [f"Consistency Score: {consistency['consistency_score']}%"],
            tone="success" if consistency["consistency_score"] >= 95 else "warning",
        )
    )
    return _detail_section(
        "data-consistency",
        "2.6 Data Consistency",
        "Check logical consistency across forecast records.",
        content,
    )


def _section_2_7_duplicate_check(duplicates: dict) -> str:
    content = html_table(
        ["Metric", "Value"],
        [
            ["Total Records", str(duplicates["total_records"])],
            ["Duplicate Records", str(duplicates["duplicate_records"])],
            ["Unique Records", str(duplicates["unique_records"])],
        ],
    )
    return _detail_section(
        "duplicate-check",
        "2.7 Duplicate Data Check",
        "Identify repeated forecast records.",
        content,
    )


def _build_detail_sections(metrics: dict) -> list[str]:
    """Render section 2 subsections in display order."""
    execution = metrics["execution"]
    return [
        _section_2_1_execution_timeline(execution),
        _section_2_2_automation_performance(execution),
        _section_2_3_error_summary(execution),
        _section_2_4_data_completeness(metrics["completeness"]),
        _section_2_5_data_validity(metrics["validity"]),
        _section_2_6_data_consistency(metrics["consistency"]),
        _section_2_7_duplicate_check(metrics["duplicates"]),
    ]


def _build_report_sections(metrics: dict) -> list[str]:
    """Render top-level report sections in display order."""
    return [
        _section_1_1_execution_overview(metrics["execution"]),
        _section_1_2_overall_quality(metrics["quality"]),
        html_section_group(
            "execution-data-quality-detail",
            QA_SECTION_2_DETAIL_TITLE,
            "".join(_build_detail_sections(metrics)),
        ),
    ]


# --- Report assembly ----------------------------------------------------------

def generate_automation_qa_html(
    rows: list[dict],
    execution_runs: list[dict] | None = None,
    execution_frequency: str = EXECUTION_FREQUENCY_LABEL,
    location: str = DEFAULT_LOCATION,
) -> str:
    """Generate the automation execution and QA HTML report."""
    rows = prepare_forecast_rows(rows)
    runs = execution_runs if execution_runs is not None else get_execution_runs(rows)

    completeness = analyze_data_completeness(rows)
    validity = analyze_data_validity(rows)
    consistency = analyze_data_consistency(rows)
    metrics = {
        "execution": analyze_execution_summary(runs, execution_frequency=execution_frequency),
        "completeness": completeness,
        "validity": validity,
        "consistency": consistency,
        "duplicates": analyze_duplicates(rows),
        "quality": analyze_overall_quality(completeness, validity, consistency),
    }

    return html_document(
        title=f"AccuWeather Automation & QA Report - {location}",
        header=html_report_header(
            "AccuWeather Automation & QA Report",
            theme="automation",
        ),
        sections_html="".join(_build_report_sections(metrics)),
        extra_styles=automation_qa_styles(),
    )


def save_automation_qa_html(
    rows: list[dict],
    output_path: str | Path = QA_REPORT_PATH,
    execution_runs: list[dict] | None = None,
    location: str = DEFAULT_LOCATION,
) -> Path:
    """Generate and save the automation and QA HTML report."""
    report = generate_automation_qa_html(
        rows,
        execution_runs=execution_runs,
        location=location,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path
