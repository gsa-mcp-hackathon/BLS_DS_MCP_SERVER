"""Tests for the answer_bls_question orchestrator tool.

All tests are fully mocked — no live BLS API calls are made.
Follows the _FakeBLSClient / _FakeStream pattern from test_tools_get_series.py.
asyncio_mode = "auto" is set in pyproject.toml, so no @pytest.mark.asyncio needed.
"""

from __future__ import annotations

import json

import example_server.utils as utils_module

# ---------------------------------------------------------------------------
# Shared mock infrastructure (mirrors test_tools_get_series.py)
# ---------------------------------------------------------------------------


def _make_bls_envelope(
    series_id: str = "LNS14000000", values: list | None = None
) -> dict:
    """Build a minimal BLS API success envelope."""
    if values is None:
        values = [
            {
                "year": "2024",
                "period": "M01",
                "periodName": "January",
                "value": "3.7",
                "footnotes": [{}],
            },
            {
                "year": "2023",
                "period": "M12",
                "periodName": "December",
                "value": "3.7",
                "footnotes": [{}],
            },
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
        self.called: bool = False  # True when stream() is called (BLS API hit)

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def stream(self, method, url, json=None, **kwargs):
        self.called = True
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
# Tool capture helper
# ---------------------------------------------------------------------------


def _capture(module) -> object:
    """Register a tool module against a fake MCP and return the inner function."""
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
# Helper: call answer_bls_question with a mocked HTTP client
# ---------------------------------------------------------------------------


async def _call(
    monkeypatch,
    fake_client,
    *,
    question: str = "What was the national unemployment rate in 2023?",
    series_id: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    import example_server.tools.answer_bls_question as mod

    fn = _capture(mod)
    monkeypatch.setattr(utils_module.httpx, "AsyncClient", fake_client)
    return await fn(
        question=question,
        series_id=series_id,
        start_year=start_year,
        end_year=end_year,
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


async def test_answer_returns_structured_response(monkeypatch) -> None:
    """Full pipeline should return the expected top-level keys."""
    result = await _call(monkeypatch, _FakeBLSClient())
    assert isinstance(result, dict)
    for key in ("question", "series_id", "series_label", "api_version", "observations"):
        assert key in result, f"Missing key: {key}"


async def test_answer_includes_notes_and_summary(monkeypatch) -> None:
    result = await _call(monkeypatch, _FakeBLSClient())
    assert "notes" in result
    assert "summary" in result
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


async def test_answer_api_version_is_v1_or_v2(monkeypatch) -> None:
    result = await _call(monkeypatch, _FakeBLSClient())
    assert result["api_version"] in ("v1", "v2")


async def test_answer_observations_preserve_string_values(monkeypatch) -> None:
    """Values must come back as strings, not floats."""
    result = await _call(monkeypatch, _FakeBLSClient())
    obs = result.get("observations", [])
    assert len(obs) >= 1
    assert isinstance(obs[0]["value"], str)


async def test_answer_suggestion_used_populated_when_no_series_id(monkeypatch) -> None:
    """When the caller doesn't supply a series_id, suggestion_used should be set."""
    result = await _call(monkeypatch, _FakeBLSClient())
    assert "suggestion_used" in result
    assert result["suggestion_used"] is not None
    assert "series_id" in result["suggestion_used"]


async def test_answer_suggestion_used_is_none_when_series_id_supplied(
    monkeypatch,
) -> None:
    """When the caller supplies a series_id directly, suggestion_used must be null."""
    result = await _call(
        monkeypatch,
        _FakeBLSClient(body=_make_bls_envelope("CUUR0000SA0")),
        question="CPI data",
        series_id="CUUR0000SA0",
    )
    assert result.get("suggestion_used") is None


# ---------------------------------------------------------------------------
# series_id override path
# ---------------------------------------------------------------------------


async def test_answer_accepts_series_id_override(monkeypatch) -> None:
    """Caller-supplied series_id should appear in the response."""
    result = await _call(
        monkeypatch,
        _FakeBLSClient(body=_make_bls_envelope("CUUR0000SA0")),
        question="What is CPI?",
        series_id="CUUR0000SA0",
    )
    assert "error" not in result
    assert result["series_id"] == "CUUR0000SA0"


async def test_answer_passes_year_range_to_fetch(monkeypatch) -> None:
    """start_year / end_year must be forwarded to the BLS POST payload."""
    client = _FakeBLSClient(body=_make_bls_envelope("CUUR0000SA0"))
    result = await _call(
        monkeypatch,
        client,
        question="CPI 2020 to 2022",
        series_id="CUUR0000SA0",
        start_year=2020,
        end_year=2022,
    )
    assert "error" not in result
    assert client.sent_json is not None
    assert client.sent_json.get("startyear") == "2020"
    assert client.sent_json.get("endyear") == "2022"


# ---------------------------------------------------------------------------
# Summary line tests
# ---------------------------------------------------------------------------


async def test_answer_summary_contains_value(monkeypatch) -> None:
    """Summary sentence should include the most recent observation value."""
    # Use a flagship LA series ID (recognised prefix)
    result = await _call(
        monkeypatch,
        _FakeBLSClient(body=_make_bls_envelope("LAUST000000000000003")),
        question="unemployment rate",
        series_id="LAUST000000000000003",
    )
    assert "3.7" in result["summary"]


async def test_answer_summary_handles_empty_observations(monkeypatch) -> None:
    """Empty data array should produce a safe fallback summary, not raise."""
    empty_envelope = {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 1,
        "message": [],
        "Results": {"series": [{"seriesID": "LNS14000000", "data": []}]},
    }
    result = await _call(
        monkeypatch,
        _FakeBLSClient(body=empty_envelope),
        question="unemployment",
        series_id="LNS14000000",
    )
    # Should not raise; summary should still be a string
    assert isinstance(result.get("summary", ""), str)


# ---------------------------------------------------------------------------
# Error / failure path tests
# ---------------------------------------------------------------------------


async def test_answer_no_flagship_match_returns_error_dict(monkeypatch) -> None:
    """A question that matches no flagship series should return an error dict."""
    import example_server.tools.answer_bls_question as mod
    import example_server.bls_flagship_series as flagship_mod

    fn = _capture(mod)
    # Monkeypatch search_flagship to return an empty list
    monkeypatch.setattr(flagship_mod, "search_flagship", lambda q, limit=10: [])
    monkeypatch.setattr(mod, "search_flagship", lambda q, limit=10: [])
    result = await fn(question="zzz no match for this question at all zzz")
    assert "error" in result
    assert "hint" in result
    assert "question" in result


async def test_answer_invalid_series_id_returns_error_dict(monkeypatch) -> None:
    """An invalid series_id supplied by the caller should return a validation error."""
    result = await _call(
        monkeypatch,
        _FakeBLSClient(),
        question="CPI",
        series_id="INVALID",
    )
    assert "error" in result
    assert "hint" in result


async def test_answer_bls_api_error_returns_error_dict(monkeypatch) -> None:
    """A BLS API failure should return an error dict, not raise."""
    bad_envelope = {
        "status": "REQUEST_NOT_PROCESSED",
        "message": ["Service unavailable"],
        "Results": {},
    }
    result = await _call(
        monkeypatch,
        _FakeBLSClient(body=bad_envelope),
        question="unemployment rate",
        series_id="LNS14000000",
    )
    assert "error" in result
    assert "hint" in result


async def test_answer_upstream_error_returns_error_dict(monkeypatch) -> None:
    """A network error should return an error dict, not raise."""
    import httpx

    result = await _call(
        monkeypatch,
        _FakeBLSClient(raise_exc=httpx.RequestError("connection refused")),
        question="unemployment",
        series_id="LNS14000000",
    )
    assert "error" in result
    assert "hint" in result


async def test_answer_does_not_reraise(monkeypatch) -> None:
    """Under any internal failure the tool must return a dict, never raise."""
    import httpx

    result = await _call(
        monkeypatch,
        _FakeBLSClient(raise_exc=httpx.RequestError("timeout")),
        question="unemployment rate",
        series_id="LNS14000000",
    )
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Registration smoke test
# ---------------------------------------------------------------------------


async def test_answer_bls_question_is_discoverable() -> None:
    """The tool must be registered and visible via the MCP server's tool list."""
    from example_server.app import mcp

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "answer_bls_question" in names


# ---------------------------------------------------------------------------
# Phase 4 — Ambiguity gate: tool-call safety tests
# ---------------------------------------------------------------------------


async def test_bls_api_not_called_when_measure_type_ambiguous(monkeypatch) -> None:
    """'Show me employment.' has level/rate/household ambiguity — must clarify."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, client, question="Show me employment.")
    assert result.get("clarification_required") is True, (
        f"Expected clarification_required=True, got: {result}"
    )
    # BLS API must not have been called
    assert not client.called


async def test_bls_api_not_called_when_stock_flow_ambiguous(monkeypatch) -> None:
    """'How many people lost jobs?' is stock/flow ambiguous — must clarify."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, client, question="How many people lost jobs?")
    assert result.get("clarification_required") is True, (
        f"Expected clarification_required=True, got: {result}"
    )
    assert not client.called


async def test_bls_api_not_called_when_cpi_vs_inflation_ambiguous(monkeypatch) -> None:
    """'What is the inflation rate?' — must clarify index vs. percent change."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, client, question="What is the inflation rate?")
    assert result.get("clarification_required") is True, (
        f"Expected clarification_required=True, got: {result}"
    )
    assert not client.called


async def test_bls_api_called_when_fully_resolved(monkeypatch) -> None:
    """'What is the unemployment rate?' is unambiguous — API should be called."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    result = await _call(
        monkeypatch, client, question="What is the unemployment rate?"
    )
    # Should NOT return clarification — should return data or error
    assert result.get("clarification_required") is not True
    assert client.called


async def test_clarification_response_shape(monkeypatch) -> None:
    """Clarification response must include required keys."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, client, question="Show me employment.")
    if result.get("clarification_required"):
        assert "clarification_question" in result
        assert isinstance(result["clarification_question"], str)
        assert len(result["clarification_question"]) > 0
        assert "hint" in result
        assert "question" in result


async def test_resolved_response_includes_defaults_applied(monkeypatch) -> None:
    """Successful response must include defaults_applied list."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    result = await _call(
        monkeypatch, client, question="What is the unemployment rate?"
    )
    if "series_id" in result:
        assert "defaults_applied" in result
        assert isinstance(result["defaults_applied"], list)


async def test_context_parameter_accepted(monkeypatch) -> None:
    """context parameter must be accepted without error."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    import example_server.tools.answer_bls_question as mod
    fn = _capture(mod)
    monkeypatch.setattr(utils_module.httpx, "AsyncClient", client)
    result = await fn(
        question="What is the unemployment rate?",
        context={"dataset": "LN", "seasonal_adjustment": "S"},
    )
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Phase 7 — Observability: log emission tests
# ---------------------------------------------------------------------------


async def test_log_records_clarification_decision(monkeypatch, caplog) -> None:
    """Logger must emit 'clarification_required=True' for ambiguous queries."""
    import logging
    client = _FakeBLSClient()
    with caplog.at_level(logging.DEBUG, logger="example_server.tools.answer_bls_question"):
        result = await _call(monkeypatch, client, question="Show me employment.")
    assert result.get("clarification_required") is True
    assert any("clarification_required=True" in r.message for r in caplog.records)


async def test_log_records_bls_api_called(monkeypatch, caplog) -> None:
    """Logger must emit 'bls_api_called=True' when API is invoked."""
    import logging
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    with caplog.at_level(logging.DEBUG, logger="example_server.tools.answer_bls_question"):
        result = await _call(
            monkeypatch, client, question="What is the unemployment rate?"
        )
    # Only verify logging when the tool proceeded to data retrieval
    if "series_id" in result:
        assert any("bls_api_called=True" in r.message for r in caplog.records)


async def test_log_does_not_expose_api_key(monkeypatch, caplog) -> None:
    """Log records must never contain a 32-char hex API key."""
    import logging
    import re
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    with caplog.at_level(logging.DEBUG, logger="example_server.tools.answer_bls_question"):
        await _call(monkeypatch, client, question="What is the unemployment rate?")
    key_pattern = re.compile(r"[0-9a-fA-F]{32}")
    for record in caplog.records:
        assert not key_pattern.search(record.message), (
            f"Log record may expose an API key: {record.message!r}"
        )
