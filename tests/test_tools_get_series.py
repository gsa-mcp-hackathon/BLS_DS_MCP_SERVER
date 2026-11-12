"""Tests for get_series_metadata and get_series_data tools."""

from __future__ import annotations

import json

import example_server.utils as utils_module

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _capture(module) -> object:
    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    module.register(FakeMCP())
    return captured["fn"]


# ---------------------------------------------------------------------------
# get_series_metadata
# ---------------------------------------------------------------------------


def test_get_series_metadata_flagship_has_notes() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    # CUUR0000SA0 is in the flagship table
    result = fn(series_id="CUUR0000SA0")
    assert "notes" in result
    assert result["notes"]  # non-empty


def test_get_series_metadata_non_flagship_no_notes() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    # A valid SM series that is NOT in the flagship table
    result = fn(series_id="SMU01000000000000001")
    assert "notes" not in result


def test_get_series_metadata_valid_ce_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CES0000000001")
    assert result["valid"] is True
    assert result["prefix"] == "CE"
    assert "segments" in result
    assert len(result["segments"]) > 0


def test_get_series_metadata_invalid_length() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="SMUXX")  # too short
    assert result["valid"] is False
    assert any("length" in i.lower() for i in result["issues"])


def test_get_series_metadata_unknown_prefix() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="ZZUNKNOWN")
    assert result["valid"] is False
    assert result["survey"] is None


def test_get_series_metadata_la_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="LAUST060000000000003")
    assert result["prefix"] == "LA"


def test_get_series_metadata_ln_series_recognized() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    # LNS11300000 = Labor Force Participation Rate SA (11 chars — canonical monthly)
    result = fn(series_id="LNS11300000")
    assert result["prefix"] == "LN"
    # Length matches the canonical monthly schema so should be valid
    assert result["valid"] is True
    assert len(result["segments"]) == 2
    seasonal_seg = result["segments"][0]
    assert seasonal_seg["name"] == "seasonal"
    assert seasonal_seg["value"] == "S"
    assert seasonal_seg["label"] == "Seasonally Adjusted"


def test_get_series_metadata_ln_flagship_enrichment() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="LNS11300000")
    # Flagship entry should enrich the result with concept/measure_type/unit
    assert result.get("concept") == "labor_force_participation_rate"
    assert result.get("measure_type") == "rate"
    assert result.get("unit") == "percent"


def test_get_series_metadata_ln_unknown_prefix_gone() -> None:
    """LN prefix must no longer return an 'unrecognised prefix' error."""
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="LNS14000000")
    assert result["valid"] is True
    assert result["survey"] is not None


# ---------------------------------------------------------------------------
# Mock helpers for get_series_data
# ---------------------------------------------------------------------------


def _make_bls_envelope(
    series_id: str = "CUUR0000SA0", values: list | None = None
) -> dict:
    """Build a minimal BLS API success envelope."""
    if values is None:
        values = [
            {
                "year": "2024",
                "period": "M12",
                "periodName": "December",
                "value": "314.175",
                "footnotes": [{}],
            }
        ]
    return {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 1,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": series_id,
                    "data": values,
                }
            ]
        },
    }


class _FakeBLSClient:
    """Intercepts httpx.AsyncClient to return a controlled BLS response."""

    def __init__(
        self, *, status_code: int = 200, body: dict | None = None, raise_exc=None
    ):
        self.status_code = status_code
        self.body = body or _make_bls_envelope()
        self.raise_exc = raise_exc
        self.sent_json: dict | None = None

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def stream(self, method, url, json=None, **kwargs):
        self.sent_json = json
        return _FakeStream(
            status_code=self.status_code,
            body=self.body,
            raise_exc=self.raise_exc,
        )


class _FakeStream:
    def __init__(self, *, status_code: int, body: dict, raise_exc):
        self.status_code = status_code
        self._body = body
        self._raise_exc = raise_exc

    async def __aenter__(self):
        if self._raise_exc:
            raise self._raise_exc
        import httpx

        if self.status_code >= 400:
            import httpx

            req = httpx.Request("POST", "https://api.bls.gov/")
            resp = httpx.Response(self.status_code, request=req)
            raise httpx.HTTPStatusError("error", request=req, response=resp)
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def aiter_bytes(self):
        yield json.dumps(self._body).encode()


# ---------------------------------------------------------------------------
# get_series_data
# ---------------------------------------------------------------------------


async def _call_get_series_data(fn, monkeypatch, fake_client, **kwargs) -> dict:
    monkeypatch.setattr(utils_module.httpx, "AsyncClient", fake_client)
    return await fn(**kwargs)


async def test_get_series_data_success(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn,
        monkeypatch,
        client,
        series_ids=["CUUR0000SA0"],
    )
    assert "series" in result
    assert len(result["series"]) == 1
    assert result["series"][0]["series_id"] == "CUUR0000SA0"


async def test_get_series_data_has_api_version(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    assert "api_version" in result
    assert result["api_version"] in ("v1", "v2")


async def test_get_series_data_observations_are_strings(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    obs = result["series"][0]["observations"]
    assert len(obs) >= 1
    assert obs[0]["value"] == "314.175"  # must be string, not float


async def test_get_series_data_has_notes_field(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    assert "notes" in result


async def test_get_series_data_bls_api_error_returns_error_dict(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    # Envelope with failure status
    bad_envelope = {
        "status": "REQUEST_NOT_PROCESSED",
        "message": ["Bad request"],
        "Results": {},
    }
    client = _FakeBLSClient(body=bad_envelope)
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    assert "error" in result
    assert "series_ids" in result


async def test_get_series_data_upstream_error_returns_error_dict(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    import httpx

    client = _FakeBLSClient(raise_exc=httpx.RequestError("timeout"))
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    assert "error" in result
    assert "series_ids" in result


async def test_get_series_data_bad_series_id_format_returns_error() -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    # Pydantic validation: lowercase is invalid per BLSSeriesRequest
    result = await fn(series_ids=["lowercase"])
    assert "error" in result


async def test_get_series_data_flagship_series_has_notes(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "notes" in series_entry  # flagship series gets per-series notes


async def test_get_series_data_does_not_reraise(monkeypatch) -> None:
    """Tool must return an error dict, never re-raise an exception."""
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    import httpx

    client = _FakeBLSClient(raise_exc=httpx.RequestError("connection refused"))
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    # Should have returned an error dict, not raised
    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit in get_series_metadata
# ---------------------------------------------------------------------------


def test_get_series_metadata_flagship_has_concept() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "concept" in result
    assert result["concept"] == "cpi_all_items"


def test_get_series_metadata_flagship_has_measure_type() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "measure_type" in result
    assert result["measure_type"] == "index"


def test_get_series_metadata_flagship_has_unit() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "unit" in result
    assert result["unit"] == "index 1982-84=100"


def test_get_series_metadata_non_flagship_no_concept() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    # SMU01000000000000001 is a valid SM series not in the flagship table
    result = fn(series_id="SMU01000000000000001")
    assert "concept" not in result
    assert "measure_type" not in result
    assert "unit" not in result


def test_get_series_metadata_la_rate_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="LAUST000000000000003")
    assert result.get("concept") == "unemployment_rate"
    assert result.get("measure_type") == "rate"
    assert result.get("unit") == "percent"


def test_get_series_metadata_ce_earnings_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CES0500000003")
    assert result.get("measure_type") == "dollar_amount"
    assert result.get("unit") == "dollars per hour"


# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit in get_series_data
# ---------------------------------------------------------------------------


async def test_get_series_data_flagship_has_concept(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "concept" in series_entry
    assert series_entry["concept"] == "cpi_all_items"


async def test_get_series_data_flagship_has_measure_type(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "measure_type" in series_entry
    assert series_entry["measure_type"] == "index"


async def test_get_series_data_flagship_has_unit(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "unit" in series_entry
    assert series_entry["unit"] == "index 1982-84=100"


async def test_get_series_data_non_flagship_no_concept(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    # SMU01000000000000001 is a valid SM series not in the flagship table
    client = _FakeBLSClient(body=_make_bls_envelope(series_id="SMU01000000000000001"))
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["SMU01000000000000001"]
    )
    series_entry = result["series"][0]
    assert "concept" not in series_entry
    assert "measure_type" not in series_entry
    assert "unit" not in series_entry
