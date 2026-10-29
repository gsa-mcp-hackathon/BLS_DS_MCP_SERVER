"""pytest configuration: skip 'live' tests unless --run-live is passed."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live integration tests that make real network calls.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if config.getoption("--run-live"):
        return  # run everything including live tests
    skip_live = pytest.mark.skip(
        reason="Live network test — run with: pytest -m live --run-live"
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
