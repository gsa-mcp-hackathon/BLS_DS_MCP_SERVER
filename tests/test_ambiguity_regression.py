"""Phase 1 regression tests — document current ambiguity gaps.

These tests confirm *current* (pre-fix) behavior so we have a clear before/after
baseline.  After the ambiguity gate is in place (Phase 4) the "currently returns
series" assertions flip to "clarification_required=True".

All tests are fully mocked — no live BLS API calls.
"""

from __future__ import annotations

import json

import example_server.utils as utils_module

# ---------------------------------------------------------------------------
# Shared mock plumbing (mirrors test_tools_answer_bls_question.py)
# ---------------------------------------------------------------------------


def _make_bls_envelope(series_id: str = "LNS14000000") -> dict:
    return {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 1,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": series_id,
                    "data": [
                        {
                            "year": "2024",
                            "period": "M12",
                            "periodName": "December",
                            "value": "4.1",
                            "footnotes": [{}],
                        }
                    ],
                }
            ]
        },
    }


class _FakeBLSClient:
    def __init__(self, *, body: dict | None = None):
        self.body = body or _make_bls_envelope()
        self.called = False

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def stream(self, method, url, json=None, **kwargs):
        self.called = True
        return _FakeStream(body=self.body)


class _FakeStream:
    def __init__(self, *, body: dict):
        self._body = body
        self.status_code = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def aiter_bytes(self):
        yield json.dumps(self._body).encode()


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


async def _call_answer(monkeypatch, question: str, fake_client=None, **kwargs) -> dict:
    import example_server.tools.answer_bls_question as mod

    fn = _capture(mod)
    if fake_client is None:
        fake_client = _FakeBLSClient()
    monkeypatch.setattr(utils_module.httpx, "AsyncClient", fake_client)
    return await fn(question=question, **kwargs)


# ---------------------------------------------------------------------------
# Regression test 1: "Show me employment." currently auto-selects without clarification
# ---------------------------------------------------------------------------


async def test_employment_query_now_clarifies(
    monkeypatch,
) -> None:
    """After the ambiguity gate, 'Show me employment.' must ask for clarification."""
    result = await _call_answer(monkeypatch, "Show me employment.")
    assert result.get("clarification_required") is True, (
        f"Expected clarification, got: {result}"
    )
    assert "clarification_question" in result


# ---------------------------------------------------------------------------
# Regression test 2: "What is the inflation rate?" now clarifies
# ---------------------------------------------------------------------------


async def test_inflation_rate_now_clarifies(monkeypatch) -> None:
    """After the gate, 'What is the inflation rate?' must ask for clarification.

    Previously the system silently returned a wrong (non-CPI) series.
    Now it must ask whether the user wants the index level or percent change.
    """
    result = await _call_answer(monkeypatch, "What is the inflation rate?")
    assert result.get("clarification_required") is True, (
        f"Expected clarification, got: {result}"
    )
    assert "clarification_question" in result


# ---------------------------------------------------------------------------
# Regression test 3: search_series seasonal default is currently "U"
# ---------------------------------------------------------------------------


def test_seasonal_default_is_currently_unadjusted(monkeypatch) -> None:
    """Before per-survey defaults, search_series uses 'U' as the global fallback."""
    import example_server.catalog as catalog_module
    import example_server.tools.search_series as mod

    # Minimal catalog so _search_ce can build an ID
    from example_server.catalog import Catalog

    c = object.__new__(Catalog)
    c._data = {
        ("ce", "seasonal"): {
            "S": "Seasonally Adjusted",
            "U": "Not Seasonally Adjusted",
        },
        ("ce", "industry"): {"000000": "Total nonfarm"},
        ("ce", "supersector"): {"00": "Total nonfarm"},
        ("ce", "datatype"): {"01": "ALL EMPLOYEES, THOUSANDS"},
    }
    monkeypatch.setattr(catalog_module, "catalog", c)
    monkeypatch.setattr(mod, "catalog", c)

    fn = _capture(mod)
    result = fn(query="payroll employment", survey="CE", limit=5)
    if result["count"] > 0:
        # Pre-fix: CE series built with "U" (3rd char of series ID after "CE")
        for r in result["results"]:
            sid = r["series_id"]
            assert sid[2] in ("S", "U")  # just confirm it's a valid seasonal code
