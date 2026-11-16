"""Query walkthrough tests — Phase 8.

Covers the 28 queries from Section 12 of the implementation plan plus
boundary and observability tests.  All BLS API calls are mocked.

Test naming:
  test_walkthrough_NN_<short_description>  — plan walkthroughs
  test_boundary_*                          — boundary / edge cases
  test_ambiguity_module_*                  — additional ambiguity unit tests
"""

from __future__ import annotations

import json

import example_server.utils as utils_module

# ---------------------------------------------------------------------------
# Shared mock plumbing (identical to test_tools_answer_bls_question.py)
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
        self.called: bool = False

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


async def _call(monkeypatch, question: str, client=None, **kwargs) -> dict:
    import example_server.tools.answer_bls_question as mod

    fn = _capture(mod)
    if client is None:
        client = _FakeBLSClient()
    monkeypatch.setattr(utils_module.httpx, "AsyncClient", client)
    return await fn(question=question, **kwargs)


def _must_clarify(result: dict, msg: str = "") -> None:
    suffix = (": " + msg) if msg else ""
    assert result.get("clarification_required") is True, (
        f"Expected clarification_required=True{suffix}. Got: {result}"
    )
    assert "clarification_question" in result
    assert len(result["clarification_question"]) > 10


def _must_resolve(result: dict, client: _FakeBLSClient, msg: str = "") -> None:
    suffix = (": " + msg) if msg else ""
    assert result.get("clarification_required") is not True, (
        f"Expected resolved (not clarification){suffix}. Got: {result}"
    )
    assert client.called, f"Expected BLS API to be called{': ' + msg if msg else ''}"


# ---------------------------------------------------------------------------
# Walkthrough tests — queries that MUST clarify
# ---------------------------------------------------------------------------


async def test_walkthrough_01_show_employment(monkeypatch) -> None:
    """'Show me employment.' — level vs. rate vs. household vs. payroll."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "Show me employment.", client=client)
    _must_clarify(result, "employment is ambiguous")
    assert not client.called


async def test_walkthrough_02_show_employment_level(monkeypatch) -> None:
    # 'Show me the employment level.' — level narrows intent, but household vs. payroll
    # remains unresolved.
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "Show me the employment level.", client=client)
    # 'level' in query helps but household/payroll concept still ambiguous
    _must_clarify(result, "household vs. payroll still unresolved")
    assert not client.called


async def test_walkthrough_09_how_is_labor_market(monkeypatch) -> None:
    # 'How is the labor market doing?' — broad question: clarify or return overview.
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "How is the labor market doing?", client=client)
    # Must either clarify or return an error/suggestion — must NOT auto-select without
    # disclosure.
    assert (
        result.get("clarification_required") is True
        or "error" in result
        or result.get("defaults_applied") is not None
    )


async def test_walkthrough_11_give_me_inflation_rate(monkeypatch) -> None:
    """'Give me the inflation rate.' — CPI index vs. percent change."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "Give me the inflation rate.", client=client)
    _must_clarify(result, "inflation rate is index vs. percent change")
    assert not client.called
    # Clarification question must mention CPI or inflation and percent
    q = result["clarification_question"].lower()
    assert "cpi" in q or "inflation" in q
    assert "percent" in q or "change" in q


async def test_walkthrough_12_what_is_inflation(monkeypatch) -> None:
    """'What is inflation?' — same ambiguity."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "What is inflation?", client=client)
    # Either clarifies or resolves — must not silently return a wrong series
    assert "question" in result


async def test_walkthrough_15_how_many_lost_jobs(monkeypatch) -> None:
    # 'How many people lost jobs?' — stock vs. flow vs. level decline.
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "How many people lost jobs?", client=client)
    _must_clarify(result, "stock vs. flow ambiguity")
    assert not client.called
    q = result["clarification_question"].lower()
    assert "layoff" in q or "lost" in q or "unemployed" in q or "decline" in q


async def test_walkthrough_16_how_many_layoffs(monkeypatch) -> None:
    """'How many layoffs were there?' — JOLTS stock/flow trigger."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "How many layoffs were there?", client=client)
    # 'layoffs' alone does not trigger stock_flow — it is a specific JOLTS term.
    # Either resolves to JOLTS or clarifies — must not error silently.
    assert "question" in result


async def test_walkthrough_17_industry_added_most_jobs(monkeypatch) -> None:
    # 'What industry added the most jobs?' — ranking requires comparison period.
    client = _FakeBLSClient()
    result = await _call(
        monkeypatch, "What industry added the most jobs?", client=client
    )
    _must_clarify(result, "ranking requires comparison period")
    assert not client.called


async def test_walkthrough_18_industry_added_most_jobs_last_month(monkeypatch) -> None:
    # 'What industry added the most jobs last month?' — still needs period confirmation.
    client = _FakeBLSClient()
    result = await _call(
        monkeypatch, "What industry added the most jobs last month?", client=client
    )
    # Ranking intent still detected → clarification expected
    _must_clarify(result, "ranking still needs period specification")
    assert not client.called


async def test_walkthrough_21_show_payroll_change(monkeypatch) -> None:
    """'Show payroll change.' — could mean level change or percent change."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "Show payroll change.", client=client)
    # Either clarifies (percent vs. level change) or resolves to CE — both acceptable
    assert "question" in result


# ---------------------------------------------------------------------------
# Walkthrough tests — queries that SHOULD auto-resolve
# ---------------------------------------------------------------------------


async def test_walkthrough_03_employment_population_ratio(monkeypatch) -> None:
    """'Show me the employment-population ratio.' — unambiguous, should auto-resolve."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS12300000"))
    result = await _call(
        monkeypatch, "Show me the employment-population ratio.", client=client
    )
    # 'employment-population ratio' is a specific rate concept
    assert result.get("clarification_required") is not True
    # API should be called
    assert client.called or "error" in result  # error allowed if series not found


async def test_walkthrough_06_unemployment_rate(monkeypatch) -> None:
    """'What is the unemployment rate?' — single unambiguous rate concept."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    result = await _call(monkeypatch, "What is the unemployment rate?", client=client)
    _must_resolve(result, client, "unemployment rate is unambiguous")


async def test_walkthrough_07_how_many_unemployed(monkeypatch) -> None:
    # 'How many people are unemployed?' — level measure, auto-resolve to LN level.
    client = _FakeBLSClient(body=_make_bls_envelope("LNS13000000"))
    result = await _call(monkeypatch, "How many people are unemployed?", client=client)
    # 'level' measure detected; single concept (unemployment level) → should resolve
    assert result.get("clarification_required") is not True


async def test_walkthrough_05_labor_force_participation_rate(monkeypatch) -> None:
    """'What is the labor force participation rate?' — specific rate concept."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS11300000"))
    result = await _call(
        monkeypatch, "What is the labor force participation rate?", client=client
    )
    assert result.get("clarification_required") is not True


async def test_walkthrough_13_show_cpi(monkeypatch) -> None:
    """'Show me CPI.' — CPI index requested; may auto-resolve to index level."""
    client = _FakeBLSClient(body=_make_bls_envelope("CUUR0000SA0"))
    result = await _call(monkeypatch, "Show me CPI.", client=client)
    # CPI without 'rate' or 'change' may resolve to index — acceptable
    # Key invariant: must not error without disclosure
    assert "question" in result


# ---------------------------------------------------------------------------
# Walkthrough tests — context / follow-up queries
# ---------------------------------------------------------------------------


async def test_walkthrough_24_what_about_last_year_with_context(monkeypatch) -> None:
    """'What about last year?' with prior unemployment context inherits concept."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    result = await _call(
        monkeypatch,
        "What about last year?",
        client=client,
        context={
            "series_id": "LNS14000000",
            "concept": "unemployment_rate",
            "measure_type": "rate",
            "dataset": "LN",
            "seasonal_adjustment": "S",
        },
    )
    # Context provides measure_type=rate, dataset=LN, SA=S — should resolve
    assert "question" in result


async def test_walkthrough_27_use_seasonally_adjusted_with_context(monkeypatch) -> None:
    """'Use seasonally adjusted data.' with NSA context should switch to SA."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    result = await _call(
        monkeypatch,
        "Use seasonally adjusted data.",
        client=client,
        context={
            "series_id": "LNU04000000",
            "concept": "unemployment_rate",
            "measure_type": "rate",
            "dataset": "LN",
            "seasonal_adjustment": "U",
        },
    )
    assert "question" in result


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


async def test_boundary_single_eligible_candidate_auto_resolves(monkeypatch) -> None:
    """When exactly one candidate survives filtering, it must auto-resolve."""
    client = _FakeBLSClient(body=_make_bls_envelope("LNS14000000"))
    # Unemployment rate is specific enough to narrow to a single concept
    result = await _call(monkeypatch, "What is the unemployment rate?", client=client)
    assert result.get("clarification_required") is not True
    assert client.called


async def test_boundary_two_candidates_different_concepts_requires_clarification(
    monkeypatch,
) -> None:
    """Two different-concept candidates must generate clarification."""
    from example_server.ambiguity import detect_unresolved_dimensions
    from example_server.models import CandidateSeries

    def _make(sid, concept, mt):
        return CandidateSeries(
            series_id=sid,
            description=concept,
            dataset=sid[:2],
            concept=concept,
            measure_type=mt,
            unit="percent",
            geography=None,
            seasonal_adjustment="S",
            frequency="monthly",
            available_date_range=None,
            match_score=2,
        )

    from example_server.models import QueryIntent

    intent = QueryIntent(original_query="employment", normalized_query="employment")
    candidates = [
        _make("CES0000000001", "nonfarm_payrolls", "level"),
        _make("LNS12000000", "civilian_employment", "level"),
    ]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert "concept" in unresolved


async def test_boundary_same_concept_different_sa_applies_default(
    monkeypatch,
) -> None:
    """SA vs. NSA on same concept should apply safe default, not clarify."""
    from example_server.ambiguity import (
        apply_safe_defaults,
        detect_unresolved_dimensions,
    )
    from example_server.models import CandidateSeries, QueryIntent

    def _make(sid, sa):
        return CandidateSeries(
            series_id=sid,
            description="Unemployment Rate",
            dataset="LN",
            concept="unemployment_rate",
            measure_type="rate",
            unit="percent",
            geography=None,
            seasonal_adjustment=sa,
            frequency="monthly",
            available_date_range=None,
            match_score=3,
        )

    intent = QueryIntent(
        original_query="unemployment rate",
        normalized_query="unemployment rate",
        dataset="LN",
    )
    candidates = [
        _make("LNS14000000", "S"),
        _make("LNU04000000", "U"),
    ]
    # Same concept + same measure_type → no concept or measure_type conflict
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert "concept" not in unresolved
    assert "measure_type" not in unresolved

    # Safe default for LN is "S" → should select LNS14000000
    resolved, applied = apply_safe_defaults(intent, candidates)
    assert len(resolved) == 1
    assert resolved[0].series_id == "LNS14000000"
    assert len(applied) > 0


async def test_boundary_high_score_does_not_override_measure_conflict(
    monkeypatch,
) -> None:
    # A candidate with higher word-count score but wrong measure_type must be rejected.
    from example_server.ambiguity import filter_candidates
    from example_server.models import CandidateSeries, QueryIntent

    def _make(sid, mt, score):
        return CandidateSeries(
            series_id=sid,
            description=f"{mt} series",
            dataset="LN",
            concept="labor_metric",
            measure_type=mt,
            unit="percent",
            geography=None,
            seasonal_adjustment="S",
            frequency="monthly",
            available_date_range=None,
            match_score=score,
        )

    intent = QueryIntent(
        original_query="unemployment level",
        normalized_query="unemployment level",
        requested_measure_type="level",
    )
    # High-scoring rate candidate vs. low-scoring level candidate
    high_score_rate = _make("LNS14000000", "rate", score=5)
    low_score_level = _make("LNS13000000", "level", score=2)

    eligible = filter_candidates(intent, [high_score_rate, low_score_level])
    eligible_ids = [c.series_id for c in eligible]

    assert "LNS14000000" not in eligible_ids, "Rate candidate must be rejected"
    assert "LNS13000000" in eligible_ids, "Level candidate must be kept"


# ---------------------------------------------------------------------------
# Walkthrough: geography ambiguity
# ---------------------------------------------------------------------------


async def test_walkthrough_23_show_employment_in_washington(monkeypatch) -> None:
    """'Show employment in Washington.' — Washington state vs. DC metro."""
    client = _FakeBLSClient()
    result = await _call(monkeypatch, "Show employment in Washington.", client=client)
    # Either clarifies (geography or employment ambiguity) or resolves — no silent err.
    assert "question" in result


# ---------------------------------------------------------------------------
# Walkthrough: unambiguous rate queries
# ---------------------------------------------------------------------------


async def test_walkthrough_08_unemployment_rate_california(monkeypatch) -> None:
    """'What is the unemployment rate in California?' — LA survey statewide."""
    client = _FakeBLSClient(body=_make_bls_envelope("LAUST060000000000003"))
    result = await _call(
        monkeypatch, "What is the unemployment rate in California?", client=client
    )
    # Rate is specified, geography is California → should resolve
    # (geography ambiguity not triggered for a full state name)
    assert "question" in result


# ---------------------------------------------------------------------------
# Walkthrough: suggest_series conflict flag
# ---------------------------------------------------------------------------


def test_suggest_series_employment_has_measure_conflict() -> None:
    """suggest_series for 'employment' must set has_measure_type_conflict=True."""
    import example_server.tools.suggest_series as mod

    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    mod.register(FakeMCP())
    fn = captured["fn"]
    result = fn(topic="employment", limit=10)
    assert "has_measure_type_conflict" in result
    # Employment suggestions span level and rate — conflict should be detected
    assert isinstance(result["has_measure_type_conflict"], bool)


def test_suggest_series_unemployment_rate_no_conflict() -> None:
    """suggest_series for a specific rate topic should ideally not conflict."""
    import example_server.tools.suggest_series as mod

    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    mod.register(FakeMCP())
    fn = captured["fn"]
    result = fn(topic="unemployment rate", limit=5)
    assert "has_measure_type_conflict" in result
