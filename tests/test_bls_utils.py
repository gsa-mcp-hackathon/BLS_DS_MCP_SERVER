"""Unit tests for BLS API client functions in utils.py and models.py.

All tests use mocked HTTP responses — no real network calls are made.
Follows the _FakeClient pattern established in test_http_security.py.

Coverage:
  - Version selection (v1 / v2) based on BLS_API_KEY
  - fetch_bls: URL routing, key injection, error sanitization, size limit
  - unwrap_bls_response: envelope validation, data integrity guarantees
  - validate_series_request: v1/v2 limit enforcement, actionable messages
  - BLSSeriesRequest: Pydantic field and cross-field validators
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from example_server import utils
from example_server.config import BLS_V1_BASE_URL, BLS_V2_BASE_URL
from example_server.models import BLSSeriesRequest
from example_server.utils import (
    BLSAPIError,
    UpstreamServiceError,
    fetch_bls,
    unwrap_bls_response,
    validate_series_request,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_success_envelope(series_id: str = "CUUR0000SA0") -> dict[str, Any]:
    """Build a minimal BLS REQUEST_SUCCEEDED envelope with one observation."""
    return {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 123,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": series_id,
                    "data": [
                        {
                            "year": "2025",
                            "period": "M01",
                            "periodName": "January",
                            "value": "274.310",
                            "footnotes": [{}],
                        }
                    ],
                }
            ]
        },
    }


class _FakeBLSPost:
    """Mock httpx.AsyncClient: captures POST payload, returns controlled responses."""

    last_endpoint: str = ""
    last_json: dict[str, Any] = {}
    response_body: bytes = b"{}"
    status_code: int = 200

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> _FakeBLSPost:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    class _Stream:
        def __init__(self, body: bytes, status_code: int) -> None:
            self._body = body
            self.status_code = status_code
            self.request = httpx.Request("POST", "https://api.bls.gov/")

        async def __aenter__(self) -> _FakeBLSPost._Stream:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "error",
                    request=self.request,
                    response=httpx.Response(self.status_code),
                )

        async def aiter_bytes(self):
            yield self._body

    def stream(
        self, method: str, url: str, *, json: dict | None = None, **kwargs: Any
    ) -> _FakeBLSPost._Stream:
        type(self).last_endpoint = url
        type(self).last_json = json or {}
        return self._Stream(type(self).response_body, type(self).status_code)


# ── Version selection ──────────────────────────────────────────────────────────


def test_version_selection_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_bls_api_version() returns 'v1' when no key is configured."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    assert cfg.get_bls_api_version() == "v1"


def test_version_selection_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_bls_api_version() returns 'v2' when a key is configured."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("abc123"))
    assert cfg.get_bls_api_version() == "v2"


# ── fetch_bls: URL routing ─────────────────────────────────────────────────────


async def test_fetch_bls_v1_posts_to_v1_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """v1 POST uses BLS_V1_BASE_URL."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    _FakeBLSPost.response_body = json.dumps(_make_success_envelope()).encode()
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    await fetch_bls({"seriesid": ["CUUR0000SA0"]})
    assert _FakeBLSPost.last_endpoint == f"{BLS_V1_BASE_URL}timeseries/data/"


async def test_fetch_bls_v2_posts_to_v2_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """v2 POST uses BLS_V2_BASE_URL."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("testkey123"))
    _FakeBLSPost.response_body = json.dumps(_make_success_envelope()).encode()
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    await fetch_bls({"seriesid": ["CUUR0000SA0"]})
    assert _FakeBLSPost.last_endpoint == f"{BLS_V2_BASE_URL}timeseries/data/"


# ── fetch_bls: key injection ───────────────────────────────────────────────────


async def test_fetch_bls_v1_no_registration_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """v1 POST does not include registrationKey in the sent payload."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    _FakeBLSPost.response_body = json.dumps(_make_success_envelope()).encode()
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    await fetch_bls({"seriesid": ["CUUR0000SA0"]})
    assert "registrationKey" not in _FakeBLSPost.last_json


async def test_fetch_bls_v2_injects_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """v2 POST includes registrationKey in the payload sent to the API."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("myfakekey99"))
    _FakeBLSPost.response_body = json.dumps(_make_success_envelope()).encode()
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    await fetch_bls({"seriesid": ["CUUR0000SA0"]})
    assert "registrationKey" in _FakeBLSPost.last_json
    # Key value is present but we do NOT assert its value here to keep the test
    # independent of the actual key content.


async def test_fetch_bls_v2_does_not_mutate_caller_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch_bls must not mutate the caller's payload dict."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("myfakekey99"))
    _FakeBLSPost.response_body = json.dumps(_make_success_envelope()).encode()
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    caller_payload: dict[str, Any] = {"seriesid": ["CUUR0000SA0"]}
    await fetch_bls(caller_payload)
    assert "registrationKey" not in caller_payload


# ── fetch_bls: error handling ─────────────────────────────────────────────────


async def test_fetch_bls_key_not_in_error_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 401 on v2 raises BLSAPIError without exposing the key value."""
    import example_server.config as cfg

    secret_key = "a8923107b1304aa9be1bec8eca762c71"
    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(secret_key))
    _FakeBLSPost.response_body = b"Unauthorized"
    _FakeBLSPost.status_code = 401
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    with pytest.raises(BLSAPIError) as exc_info:
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})

    message = str(exc_info.value)
    assert secret_key not in message
    assert "registration key" in message.lower()


async def test_fetch_bls_403_raises_bls_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 403 on v2 raises BLSAPIError (not UpstreamServiceError)."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("somekey"))
    _FakeBLSPost.response_body = b"Forbidden"
    _FakeBLSPost.status_code = 403
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    with pytest.raises(BLSAPIError):
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})


async def test_fetch_bls_http_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-auth HTTP errors raise UpstreamServiceError with the status code."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    _FakeBLSPost.response_body = b"Internal Server Error - SSN 123-45-6789"
    _FakeBLSPost.status_code = 500
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    with pytest.raises(UpstreamServiceError) as exc_info:
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})

    message = str(exc_info.value)
    assert "500" in message
    assert "SSN" not in message  # upstream body must not leak


async def test_fetch_bls_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network-level failure raises UpstreamServiceError."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))

    class _FailingClient:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _FailingClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        def stream(self, *args: Any, **kwargs: Any) -> Any:
            raise httpx.RequestError("connection refused")

    monkeypatch.setattr(utils.httpx, "AsyncClient", _FailingClient)

    with pytest.raises(UpstreamServiceError, match="request failed"):
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})


async def test_fetch_bls_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed JSON response raises UpstreamServiceError."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    _FakeBLSPost.response_body = b"not-json SSN 123-45-6789"
    _FakeBLSPost.status_code = 200
    monkeypatch.setattr(utils.httpx, "AsyncClient", _FakeBLSPost)

    with pytest.raises(UpstreamServiceError) as exc_info:
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})

    assert "invalid JSON" in str(exc_info.value)
    assert "SSN" not in str(exc_info.value)


async def test_fetch_bls_response_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Response exceeding 5 MB raises UpstreamServiceError."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))

    big_body = b"x" * (utils.MAX_RESPONSE_BYTES + 1)

    class _FakeStreamContext:
        """Async context manager returned by client.stream()."""

        status_code = 200
        request = httpx.Request("POST", "https://api.bls.gov/")

        async def __aenter__(self) -> _FakeStreamContext:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        def raise_for_status(self) -> None:
            pass

        async def aiter_bytes(self):
            yield big_body

    class _BigClient:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> _BigClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        def stream(self, *args: Any, **kwargs: Any) -> _FakeStreamContext:
            return _FakeStreamContext()

    monkeypatch.setattr(utils.httpx, "AsyncClient", _BigClient)

    with pytest.raises(UpstreamServiceError, match="size limit"):
        await fetch_bls({"seriesid": ["CUUR0000SA0"]})


# ── unwrap_bls_response ────────────────────────────────────────────────────────


def test_unwrap_success() -> None:
    """REQUEST_SUCCEEDED with valid Results.series returns the series list."""
    envelope = _make_success_envelope()
    result = unwrap_bls_response(envelope)
    assert isinstance(result, list)
    assert result[0]["seriesID"] == "CUUR0000SA0"


def test_unwrap_failure_status() -> None:
    """Non-SUCCESS status raises BLSAPIError containing the BLS message."""
    envelope = {
        "status": "REQUEST_NOT_PROCESSED",
        "message": ["Series does not exist."],
        "Results": {},
    }
    with pytest.raises(BLSAPIError, match="Series does not exist"):
        unwrap_bls_response(envelope)


def test_unwrap_missing_results_key() -> None:
    """Missing 'Results' key on a SUCCESS response raises BLSAPIError."""
    envelope = {"status": "REQUEST_SUCCEEDED", "message": []}
    with pytest.raises(BLSAPIError, match="'Results' is missing"):
        unwrap_bls_response(envelope)


def test_unwrap_missing_series_key() -> None:
    """Missing 'series' inside Results raises BLSAPIError."""
    envelope = {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {}}
    with pytest.raises(BLSAPIError, match="'Results.series' is missing"):
        unwrap_bls_response(envelope)


def test_unwrap_empty_series_list() -> None:
    """An empty series list returns [] without raising."""
    envelope = {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": {"series": []},
    }
    assert unwrap_bls_response(envelope) == []


# ── Data integrity ─────────────────────────────────────────────────────────────


def test_unwrap_preserves_value_string() -> None:
    """Value strings must be returned exactly as BLS published them — no float cast."""
    envelope = _make_success_envelope()
    envelope["Results"]["series"][0]["data"][0]["value"] = "274.310"
    series = unwrap_bls_response(envelope)
    assert series[0]["data"][0]["value"] == "274.310"
    # Confirm it is still a string, not a float
    assert isinstance(series[0]["data"][0]["value"], str)


def test_unwrap_preserves_missing_observation_dash() -> None:
    """A '-' observation value must pass through unchanged, not become 0."""
    envelope = _make_success_envelope()
    envelope["Results"]["series"][0]["data"][0]["value"] = "-"
    series = unwrap_bls_response(envelope)
    assert series[0]["data"][0]["value"] == "-"


def test_unwrap_preserves_missing_observation_dot() -> None:
    """A '.' observation value must pass through unchanged, not become 0."""
    envelope = _make_success_envelope()
    envelope["Results"]["series"][0]["data"][0]["value"] = "."
    series = unwrap_bls_response(envelope)
    assert series[0]["data"][0]["value"] == "."


def test_unwrap_preserves_footnotes() -> None:
    """Footnotes list must be returned verbatim."""
    envelope = _make_success_envelope()
    footnotes = [{"code": "P", "text": "Preliminary"}]
    envelope["Results"]["series"][0]["data"][0]["footnotes"] = footnotes
    series = unwrap_bls_response(envelope)
    assert series[0]["data"][0]["footnotes"] == footnotes


def test_unwrap_preserves_period_fields() -> None:
    """period and periodName must be returned exactly as BLS provides them."""
    envelope = _make_success_envelope()
    series = unwrap_bls_response(envelope)
    obs = series[0]["data"][0]
    assert obs["period"] == "M01"
    assert obs["periodName"] == "January"


def test_unwrap_api_key_stripped_from_error_messages() -> None:
    """A 32-char hex string in BLS error messages must not appear in BLSAPIError."""
    fake_key = "a8923107b1304aa9be1bec8eca762c71"
    envelope = {
        "status": "REQUEST_NOT_PROCESSED",
        "message": [f"Invalid key: {fake_key}"],
        "Results": {},
    }
    with pytest.raises(BLSAPIError) as exc_info:
        unwrap_bls_response(envelope)
    assert fake_key not in str(exc_info.value)


# ── validate_series_request ────────────────────────────────────────────────────


def test_validate_request_ok_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid v1 request passes without error."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2022, end_year=2024)
    validate_series_request(req)  # must not raise


def test_validate_request_ok_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid v2 request with calculations passes without error."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("somekey"))
    req = BLSSeriesRequest(
        series_ids=["CUUR0000SA0"],
        start_year=2005,
        end_year=2024,
        calculations=True,
    )
    validate_series_request(req)  # must not raise


def test_validate_request_v1_series_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """26 series on v1 raises BLSAPIError with a v2 hint."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    req = BLSSeriesRequest(series_ids=[f"CUUR000{i:04d}" for i in range(26)])
    with pytest.raises(BLSAPIError) as exc_info:
        validate_series_request(req)
    assert "v2" in str(exc_info.value)
    assert "25" in str(exc_info.value)


def test_validate_request_v2_series_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """51 series on v2 raises BLSAPIError."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("somekey"))
    req = BLSSeriesRequest(series_ids=[f"CUUR000{i:04d}" for i in range(51)])
    with pytest.raises(BLSAPIError) as exc_info:
        validate_series_request(req)
    assert "50" in str(exc_info.value)


def test_validate_request_v1_year_range_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """11-year range on v1 raises BLSAPIError with a v2 hint."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2010, end_year=2020)
    with pytest.raises(BLSAPIError) as exc_info:
        validate_series_request(req)
    assert "v2" in str(exc_info.value)
    assert "10" in str(exc_info.value)


def test_validate_request_v2_year_range_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """21-year span on v2 raises BLSAPIError (function-level check, bypasses model)."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr("somekey"))
    # Construct with exactly 20 years (model limit), then patch end_year to 21
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2000, end_year=2019)
    # Force a 21-year span past model validation to exercise the function-level check.
    object.__setattr__(req, "end_year", 2020)
    with pytest.raises(BLSAPIError) as exc_info:
        validate_series_request(req)
    assert "20" in str(exc_info.value)


def test_validate_request_v1_calculations_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculations=True on v1 raises BLSAPIError mentioning v2."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], calculations=True)
    with pytest.raises(BLSAPIError, match="v2"):
        validate_series_request(req)


def test_validate_request_v1_annual_average_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """annual_average=True on v1 raises BLSAPIError mentioning v2."""
    import example_server.config as cfg

    monkeypatch.setattr(cfg.settings, "bls_api_key", SecretStr(""))
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], annual_average=True)
    with pytest.raises(BLSAPIError, match="v2"):
        validate_series_request(req)


# ── BLSSeriesRequest model validators ─────────────────────────────────────────


def test_bls_series_request_valid() -> None:
    """A well-formed request constructs without error."""
    req = BLSSeriesRequest(
        series_ids=["CUUR0000SA0", "LNS14000000"],
        start_year=2020,
        end_year=2024,
    )
    assert req.series_ids == ["CUUR0000SA0", "LNS14000000"]
    assert req.start_year == 2020
    assert req.end_year == 2024


def test_bls_series_request_no_years() -> None:
    """Omitting years is valid — BLS returns its default range."""
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"])
    assert req.start_year is None
    assert req.end_year is None


def test_bls_series_request_empty_ids() -> None:
    """Empty series_ids list raises ValidationError."""
    with pytest.raises(ValidationError, match="at least one"):
        BLSSeriesRequest(series_ids=[])


def test_bls_series_request_bad_format_lowercase() -> None:
    """Lowercase series ID raises ValidationError."""
    with pytest.raises(ValidationError, match="uppercase alphanumeric"):
        BLSSeriesRequest(series_ids=["cuur0000sa0"])


def test_bls_series_request_bad_format_special_chars() -> None:
    """Series ID with special characters raises ValidationError."""
    with pytest.raises(ValidationError, match="uppercase alphanumeric"):
        BLSSeriesRequest(series_ids=["CUUR-0000"])


def test_bls_series_request_bad_year_too_short() -> None:
    """A 2-digit year raises ValidationError."""
    with pytest.raises(ValidationError, match="4-digit"):
        BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=25)


def test_bls_series_request_year_order_violated() -> None:
    """start_year > end_year raises ValidationError."""
    with pytest.raises(ValidationError, match="must be <="):
        BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2024, end_year=2020)


def test_bls_series_request_year_range_over_20() -> None:
    """Year range exceeding 20 years raises ValidationError at model level."""
    with pytest.raises(ValidationError, match="20 years"):
        BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2000, end_year=2021)


def test_bls_series_request_exactly_20_years_ok() -> None:
    """A 20-year range is exactly at the model-level limit and must succeed."""
    req = BLSSeriesRequest(series_ids=["CUUR0000SA0"], start_year=2000, end_year=2019)
    assert req.start_year == 2000
    assert req.end_year == 2019


def test_bls_series_request_21_char_jolts_id_accepted() -> None:
    """Extended JOLTS series IDs up to 28 chars must be accepted (not rejected by
    regex)."""
    sid = "JTS000000000000000JOL"  # 21 chars — real JOLTS extended format
    req = BLSSeriesRequest(series_ids=[sid])
    assert req.series_ids == [sid]


def test_bls_series_request_29_char_id_rejected() -> None:
    """Series IDs longer than 28 characters must be rejected."""
    with pytest.raises(ValidationError, match="uppercase alphanumeric"):
        BLSSeriesRequest(series_ids=["A" * 29])
