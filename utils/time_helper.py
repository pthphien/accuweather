"""UTC timestamps for execution logs and reports (consistent local + CI)."""

from __future__ import annotations

from datetime import datetime, timezone

_EXECUTED_AT_FORMAT = "%Y-%m-%d %H:%M:%S"


def now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc)


def today():
    """Return today's date in UTC."""
    return now().date()


def format_timestamp(when: datetime | None = None) -> str:
    """Format a datetime as a UTC timestamp string."""
    moment = when or now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return moment.strftime(_EXECUTED_AT_FORMAT)
