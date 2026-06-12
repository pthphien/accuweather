"""Pytest fixtures for AccuWeather automation tests."""

import pytest

from utils.driver_helper import managed_driver


def pytest_addoption(parser):
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser tests with a visible Chrome window",
    )


@pytest.fixture
def driver(request):
    """Provide a Chrome WebDriver instance for each test."""
    headless = not request.config.getoption("--headed")
    with managed_driver(headless=headless) as browser:
        yield browser
