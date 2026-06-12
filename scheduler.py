"""Run the AccuWeather forecast flow on a fixed interval."""

import argparse
import time
import traceback
from config import DEFAULT_INTERVAL_MINUTES, DEFAULT_LOCATION
from flows.accuweather_flow import run_accuweather_forecast_flow
from utils.driver_helper import managed_driver
from utils.execution_log import classify_error, record_execution_run
from utils.time_helper import format_timestamp


def run_flow_once(headless: bool = True) -> None:
    """Run the forecast flow once."""
    started_at = time.perf_counter()
    execution_time = format_timestamp()

    try:
        with managed_driver(headless=headless) as driver:
            result = run_accuweather_forecast_flow(driver, location=DEFAULT_LOCATION)
            print(
                f"Collected {result.records_collected} records "
                f"in {result.duration_seconds}s"
            )
    except Exception as exc:
        record_execution_run(
            {
                "execution_time": execution_time,
                "status": "failed",
                "records_collected": 0,
                "duration_seconds": round(time.perf_counter() - started_at, 2),
                "errors": classify_error(exc),
            }
        )
        raise


def run_scheduler(interval_minutes: int, headless: bool = True) -> None:
    """Run the flow repeatedly every interval_minutes."""
    print(f"Scheduler started: running every {interval_minutes} minute(s)")
    print("Press Ctrl+C to stop\n")

    while True:
        started_at = format_timestamp()
        print(f"=== Run started at {started_at} ===")

        try:
            run_flow_once(headless=headless)
        except Exception:
            print("Run failed:")
            traceback.print_exc()

        finished_at = format_timestamp()
        print(f"=== Run finished at {finished_at} ===")
        print(f"Next run in {interval_minutes} minute(s)...\n")
        time.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AccuWeather flow on a schedule")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_MINUTES,
        help=f"Interval in minutes (default: {DEFAULT_INTERVAL_MINUTES})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no schedule loop)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window",
    )
    args = parser.parse_args()

    headless = not args.headed

    if args.once:
        run_flow_once(headless=headless)
    else:
        run_scheduler(interval_minutes=args.interval, headless=headless)


if __name__ == "__main__":
    main()
