"""Persist automation execution run history."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config import DATA_RETENTION_DAYS, ERROR_LABELS, EXECUTION_LOG_PATH
from utils.helpers import remove_old_rows
from utils.time_helper import format_timestamp

ERROR_TYPES = tuple(ERROR_LABELS.keys())


def _empty_errors() -> dict[str, int]:
    return dict.fromkeys(ERROR_TYPES, 0)


def classify_error(exc: BaseException) -> dict[str, int]:
    """Map an exception to error type counts."""
    errors = _empty_errors()
    message = f"{type(exc).__name__} {exc}".lower()

    if "nosuchelement" in message or "element not found" in message or "unable to locate" in message:
        errors["element_not_found"] = 1
    elif "timeout" in message or "timed out" in message:
        errors["timeout"] = 1
    elif "net::" in message or "network" in message or "connection" in message:
        errors["network_error"] = 1
    elif "page load" in message or ("document" in message and "ready" in message):
        errors["page_load_failure"] = 1
    else:
        errors["unexpected_error"] = 1

    return errors


def _load_runs(log_path: Path) -> list[dict]:
    """Load execution runs from the log file."""
    if not log_path.exists():
        return []

    with open(log_path, encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, list) else []


def _save_runs(log_path: Path, runs: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as file:
        json.dump(runs, file, indent=2)


def _normalize_run(run: dict) -> dict:
    return {
        "execution_time": run.get("execution_time", format_timestamp()),
        "status": run.get("status", "passed"),
        "records_collected": int(run.get("records_collected", 0)),
        "duration_seconds": run.get("duration_seconds"),
        "errors": {**_empty_errors(), **(run.get("errors") or {})},
    }


def _bootstrap_runs_from_forecast(rows: list[dict]) -> list[dict]:
    """Build execution timeline entries from forecast executed_at timestamps."""
    grouped: dict[str, int] = defaultdict(int)
    for row in rows:
        executed_at = str(row.get("executed_at", "")).strip()
        if executed_at:
            grouped[executed_at] += 1

    return [
        {
            "execution_time": execution_time,
            "status": "passed",
            "records_collected": records,
            "duration_seconds": None,
            "errors": _empty_errors(),
        }
        for execution_time, records in sorted(grouped.items())
    ]


def record_execution_run(
    run: dict,
    log_path: str | Path = EXECUTION_LOG_PATH,
) -> None:
    """Append an execution run to the log file."""
    log_path = Path(log_path)
    runs = remove_old_rows(
        _load_runs(log_path),
        "execution_time",
        DATA_RETENTION_DAYS,
    )
    runs.append(_normalize_run(run))
    _save_runs(log_path, runs)


def get_execution_runs(
    forecast_rows: list[dict] | None = None,
    log_path: str | Path = EXECUTION_LOG_PATH,
) -> list[dict]:
    """Return logged runs, or bootstrap from forecast data when the log is empty."""
    runs = _load_runs(Path(log_path))
    if runs:
        return runs

    if forecast_rows:
        return _bootstrap_runs_from_forecast(forecast_rows)
    return []
