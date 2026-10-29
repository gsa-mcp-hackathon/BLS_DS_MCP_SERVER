"""Live connectivity tests against the real BLS Public Data API.

These tests make actual HTTP requests to https://api.bls.gov/ and are
excluded from the normal test suite by the ``live`` marker. Run them
explicitly when you want to verify real API connectivity:

    uv run pytest tests/test_bls_live.py -v -m live

Requirements:
  - Network access to api.bls.gov
  - For the v2 test: BLS_API_KEY must be set in .env or the environment.
    Register at https://data.bls.gov/registrationEngine/

The v2 test is automatically skipped when BLS_API_KEY is not configured.
"""

from __future__ import annotations

import pytest

from example_server.config import get_bls_api_version, settings
from example_server.models import BLSSeriesRequest
from example_server.utils import (
    fetch_bls,
    unwrap_bls_response,
    validate_series_request,
)

# Series used for all live tests: CPI-U All Items, U.S. City Average.
_TEST_SERIES = "CUUR0000SA0"
_TEST_YEAR = 2025

pytestmark = pytest.mark.live


@pytest.fixture()
def _force_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force v1 by clearing the API key for the duration of the test."""
    from pydantic import SecretStr

    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))


async def test_live_v1_retrieval(_force_v1: None) -> None:
    """v1 unauthenticated: retrieve CPI series for the test year.

    Verifies:
    - API version selected is v1
    - HTTP call succeeds (no exception)
    - BLS envelope status is REQUEST_SUCCEEDED
    - At least one observation is returned
    - The returned series ID matches the requested series
    - Observation values are strings (no float conversion)
    """
    assert get_bls_api_version() == "v1", "Fixture did not clear the key"

    req = BLSSeriesRequest(
        series_ids=[_TEST_SERIES],
        start_year=_TEST_YEAR,
        end_year=_TEST_YEAR,
    )
    validate_series_request(req)

    payload = {
        "seriesid": req.series_ids,
        "startyear": str(req.start_year),
        "endyear": str(req.end_year),
    }
    raw = await fetch_bls(payload)

    # Envelope status
    assert raw.get("status") == "REQUEST_SUCCEEDED", (
        f"BLS returned status '{raw.get('status')}'. "
        f"Messages: {raw.get('message', [])}"
    )

    series_list = unwrap_bls_response(raw)
    assert len(series_list) >= 1, "No series in response"

    series = series_list[0]
    assert series["seriesID"] == _TEST_SERIES
    assert len(series["data"]) >= 1, "No observations returned"

    # Data integrity: values must be strings
    for obs in series["data"]:
        assert isinstance(obs["value"], str), (
            f"value field must be a string, got {type(obs['value'])}"
        )

    _report("v1", raw, series)


async def test_live_v2_retrieval() -> None:
    """v2 authenticated: retrieve CPI series for the test year using BLS_API_KEY.

    Automatically skipped when BLS_API_KEY is not configured.

    Verifies:
    - API version selected is v2
    - HTTP call succeeds (no exception)
    - BLS envelope status is REQUEST_SUCCEEDED
    - At least one observation is returned
    - The returned series ID matches the requested series
    - Observation values are strings (no float conversion)
    - The API key is never printed or exposed
    """
    key_configured = bool(settings.bls_api_key.get_secret_value())
    if not key_configured:
        pytest.skip("BLS_API_KEY not configured — skipping v2 live test")

    assert get_bls_api_version() == "v2", "Key is set but version is not v2"

    req = BLSSeriesRequest(
        series_ids=[_TEST_SERIES],
        start_year=_TEST_YEAR,
        end_year=_TEST_YEAR,
    )
    validate_series_request(req)

    payload = {
        "seriesid": req.series_ids,
        "startyear": str(req.start_year),
        "endyear": str(req.end_year),
    }
    raw = await fetch_bls(payload)

    # Envelope status
    assert raw.get("status") == "REQUEST_SUCCEEDED", (
        f"BLS returned status '{raw.get('status')}'. "
        f"Messages: {raw.get('message', [])}"
    )

    series_list = unwrap_bls_response(raw)
    assert len(series_list) >= 1, "No series in response"

    series = series_list[0]
    assert series["seriesID"] == _TEST_SERIES
    assert len(series["data"]) >= 1, "No observations returned"

    # Data integrity: values must be strings
    for obs in series["data"]:
        assert isinstance(obs["value"], str), (
            f"value field must be a string, got {type(obs['value'])}"
        )

    # Key must not appear anywhere in the raw response dict
    raw_text = str(raw)
    key_value = settings.bls_api_key.get_secret_value()
    assert key_value not in raw_text, "API key leaked into response body"

    _report("v2", raw, series)


# ── Reporting helper ───────────────────────────────────────────────────────────

def _report(version: str, raw: dict, series: dict) -> None:
    """Print a structured connectivity report to stdout (visible with -s)."""
    data = series.get("data", [])
    first = data[0] if data else {}
    messages = raw.get("message") or "none"

    print(f"\n{'='*56}")
    print(f"  BLS Live Connectivity Report — {version.upper()}")
    print(f"{'='*56}")
    print(f"  API version used    : {version}")
    print(f"  BLS status          : {raw.get('status')}")
    print(f"  Series ID returned  : {series.get('seriesID')}")
    print(f"  Observations count  : {len(data)}")
    if first:
        print(
            f"  First observation   : "
            f"year={first.get('year')} "
            f"period={first.get('period')} "
            f"value={first.get('value')!r}"
        )
    print(f"  BLS messages        : {messages}")
    if version == "v2":
        print("  Key displayed       : [REDACTED]")
    print(f"{'='*56}")
