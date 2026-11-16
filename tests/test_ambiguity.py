"""Tests for the ambiguity module (src/example_server/ambiguity.py).

Covers:
- QueryIntent / CandidateSeries construction (Phase 2 validation)
- parse_intent_from_query keyword detection
- filter_candidates eligibility rules
- detect_unresolved_dimensions
- generate_clarification question text
- SAFE_DEFAULTS per-survey values
"""

from __future__ import annotations

import pytest

from example_server.models import CandidateSeries, QueryIntent


# ---------------------------------------------------------------------------
# Phase 2 — data structure construction
# ---------------------------------------------------------------------------


def test_query_intent_construction() -> None:
    """QueryIntent can be constructed with only the two required fields."""
    intent = QueryIntent(original_query="test", normalized_query="test")
    assert intent.original_query == "test"
    assert intent.concept is None
    assert intent.requested_measure_type is None
    assert intent.applied_defaults == []
    assert intent.unresolved_dimensions == []


def test_query_intent_all_fields() -> None:
    intent = QueryIntent(
        original_query="unemployment rate",
        normalized_query="unemployment rate",
        concept="unemployment_rate",
        requested_measure_type="rate",
        dataset="LN",
        geography_type="national",
        seasonal_adjustment="S",
    )
    assert intent.dataset == "LN"
    assert intent.requested_measure_type == "rate"


def test_candidate_series_construction() -> None:
    c = CandidateSeries(
        series_id="LNS14000000",
        description="Unemployment Rate — SA",
        dataset="LN",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
        geography=None,
        seasonal_adjustment="S",
        frequency="monthly",
        available_date_range=None,
        match_score=3,
    )
    assert c.eligible is True
    assert c.rejection_reason is None
    assert c.mismatch_reasons == []


def test_candidate_series_ineligible() -> None:
    c = CandidateSeries(
        series_id="LNS12300000",
        description="Employment-Population Ratio",
        dataset="LN",
        concept="employment_population_ratio",
        measure_type="rate",
        unit="percent",
        geography=None,
        seasonal_adjustment="S",
        frequency="monthly",
        available_date_range=None,
        match_score=2,
        eligible=False,
        rejection_reason="measure_type conflicts: requested level, got rate",
    )
    assert c.eligible is False
    assert "level" in c.rejection_reason


# ---------------------------------------------------------------------------
# Phase 3 — SAFE_DEFAULTS
# ---------------------------------------------------------------------------


def test_safe_defaults_ce_is_seasonally_adjusted() -> None:
    from example_server.ambiguity import SAFE_DEFAULTS
    assert SAFE_DEFAULTS["CE"] == "S"


def test_safe_defaults_cu_is_unadjusted() -> None:
    from example_server.ambiguity import SAFE_DEFAULTS
    assert SAFE_DEFAULTS["CU"] == "U"


def test_safe_defaults_la_is_seasonally_adjusted() -> None:
    from example_server.ambiguity import SAFE_DEFAULTS
    assert SAFE_DEFAULTS["LA"] == "S"


def test_safe_defaults_ln_is_seasonally_adjusted() -> None:
    from example_server.ambiguity import SAFE_DEFAULTS
    assert SAFE_DEFAULTS["LN"] == "S"


def test_safe_defaults_sm_is_unadjusted() -> None:
    from example_server.ambiguity import SAFE_DEFAULTS
    assert SAFE_DEFAULTS["SM"] == "U"


# ---------------------------------------------------------------------------
# Phase 3 — parse_intent_from_query
# ---------------------------------------------------------------------------


def test_parse_intent_detects_rate_measure() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("What is the unemployment rate?")
    assert intent.requested_measure_type == "rate"


def test_parse_intent_detects_level_measure() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("Show me the employment level")
    assert intent.requested_measure_type == "level"


def test_parse_intent_detects_percent_change() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("What is the inflation rate?")
    assert intent.requested_measure_type == "percent_change"


def test_parse_intent_detects_ranking() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("What industry added the most jobs?")
    assert intent.calculation_type == "ranking"


def test_parse_intent_detects_geography() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("unemployment rate in California")
    assert intent.geography_value is not None
    assert "california" in intent.geography_value.lower()


def test_parse_intent_detects_seasonally_adjusted() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("Show seasonally adjusted payrolls")
    assert intent.seasonal_adjustment == "S"


def test_parse_intent_stock_vs_flow_lost_jobs() -> None:
    from example_server.ambiguity import parse_intent_from_query
    intent = parse_intent_from_query("How many people lost jobs?")
    # Should detect stock/flow ambiguity — multiple plausible concepts
    assert "stock_flow" in intent.unresolved_dimensions


# ---------------------------------------------------------------------------
# Phase 3 — filter_candidates
# ---------------------------------------------------------------------------

def _make_candidate(
    series_id: str,
    concept: str,
    measure_type: str,
    seasonal: str = "S",
    score: int = 2,
) -> CandidateSeries:
    return CandidateSeries(
        series_id=series_id,
        description=f"{concept} ({measure_type})",
        dataset=series_id[:2],
        concept=concept,
        measure_type=measure_type,
        unit="percent" if measure_type == "rate" else "thousands of persons",
        geography=None,
        seasonal_adjustment=seasonal,
        frequency="monthly",
        available_date_range=None,
        match_score=score,
    )


def test_filter_candidates_rejects_rate_when_level_requested() -> None:
    from example_server.ambiguity import filter_candidates
    intent = QueryIntent(
        original_query="employment level",
        normalized_query="employment level",
        requested_measure_type="level",
    )
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level"),
        _make_candidate("LNS12300000", "employment_population_ratio", "rate"),
    ]
    eligible = filter_candidates(intent, candidates)
    ids = [c.series_id for c in eligible]
    assert "CES0000000001" in ids
    assert "LNS12300000" not in ids


def test_filter_candidates_keeps_all_when_no_measure_requested() -> None:
    from example_server.ambiguity import filter_candidates
    intent = QueryIntent(
        original_query="employment",
        normalized_query="employment",
        requested_measure_type=None,
    )
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level"),
        _make_candidate("LNS12300000", "employment_population_ratio", "rate"),
    ]
    eligible = filter_candidates(intent, candidates)
    assert len(eligible) == 2


def test_filter_candidates_respects_explicit_seasonal() -> None:
    from example_server.ambiguity import filter_candidates
    intent = QueryIntent(
        original_query="unemployment rate seasonally adjusted",
        normalized_query="unemployment rate seasonally adjusted",
        seasonal_adjustment="S",
    )
    candidates = [
        _make_candidate("LNS14000000", "unemployment_rate", "rate", seasonal="S"),
        _make_candidate("LNU04000000", "unemployment_rate", "rate", seasonal="U"),
    ]
    eligible = filter_candidates(intent, candidates)
    ids = [c.series_id for c in eligible]
    assert "LNS14000000" in ids
    assert "LNU04000000" not in ids


# ---------------------------------------------------------------------------
# Phase 3 — detect_unresolved_dimensions
# ---------------------------------------------------------------------------


def test_detect_unresolved_flags_concept_conflict() -> None:
    from example_server.ambiguity import detect_unresolved_dimensions
    intent = QueryIntent(original_query="employment", normalized_query="employment")
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level"),
        _make_candidate("LNS12000000", "civilian_employment", "level"),
    ]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert "concept" in unresolved


def test_detect_unresolved_flags_measure_type_conflict() -> None:
    from example_server.ambiguity import detect_unresolved_dimensions
    intent = QueryIntent(original_query="employment", normalized_query="employment")
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level"),
        _make_candidate("LNS12300000", "employment_population_ratio", "rate"),
    ]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert "measure_type" in unresolved


def test_detect_unresolved_no_conflict_single_candidate() -> None:
    from example_server.ambiguity import detect_unresolved_dimensions
    intent = QueryIntent(original_query="unemployment rate", normalized_query="unemployment rate")
    candidates = [_make_candidate("LNS14000000", "unemployment_rate", "rate")]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert unresolved == []


def test_detect_unresolved_no_conflict_same_concept_different_sa() -> None:
    """SA vs NSA on same concept is NOT a concept conflict — resolved by default."""
    from example_server.ambiguity import detect_unresolved_dimensions
    intent = QueryIntent(original_query="unemployment rate", normalized_query="unemployment rate")
    candidates = [
        _make_candidate("LNS14000000", "unemployment_rate", "rate", seasonal="S"),
        _make_candidate("LNU04000000", "unemployment_rate", "rate", seasonal="U"),
    ]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    # Same concept + same measure_type → safe default handles it, no unresolved flag
    assert "concept" not in unresolved
    assert "measure_type" not in unresolved


def test_detect_unresolved_flags_stock_flow() -> None:
    from example_server.ambiguity import detect_unresolved_dimensions
    intent = QueryIntent(
        original_query="how many people lost jobs",
        normalized_query="how many people lost jobs",
        unresolved_dimensions=["stock_flow"],
    )
    candidates = [
        _make_candidate("LNS13200000", "unemployed_job_losers", "level"),
        _make_candidate("JTS000000000000LDL", "layoffs_and_discharges", "level"),
    ]
    unresolved = detect_unresolved_dimensions(intent, candidates)
    assert "stock_flow" in unresolved


# ---------------------------------------------------------------------------
# Phase 3 — generate_clarification
# ---------------------------------------------------------------------------


def test_generate_clarification_employment_level_vs_ratio() -> None:
    from example_server.ambiguity import generate_clarification
    intent = QueryIntent(original_query="show employment", normalized_query="show employment")
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level"),
        _make_candidate("LNS12300000", "employment_population_ratio", "rate"),
    ]
    q = generate_clarification(intent, candidates, ["measure_type"])
    assert isinstance(q, str)
    assert len(q) > 10


def test_generate_clarification_cpi_index_vs_rate() -> None:
    from example_server.ambiguity import generate_clarification
    intent = QueryIntent(
        original_query="what is the inflation rate",
        normalized_query="what is the inflation rate",
        requested_measure_type="percent_change",
    )
    candidates = [
        _make_candidate("CUUR0000SA0", "cpi_all_items", "index"),
    ]
    q = generate_clarification(intent, candidates, ["measure_type"])
    assert "CPI" in q or "inflation" in q.lower() or "percent" in q.lower()


def test_generate_clarification_lost_jobs() -> None:
    from example_server.ambiguity import generate_clarification
    intent = QueryIntent(
        original_query="how many people lost jobs",
        normalized_query="how many people lost jobs",
    )
    candidates = [
        _make_candidate("LNS13200000", "unemployed_job_losers", "level"),
        _make_candidate("JTS000000000000LDL", "layoffs_and_discharges", "level"),
    ]
    q = generate_clarification(intent, candidates, ["stock_flow"])
    assert isinstance(q, str)
    assert len(q) > 10


def test_generate_clarification_ranking_needs_period() -> None:
    from example_server.ambiguity import generate_clarification
    intent = QueryIntent(
        original_query="what industry added the most jobs",
        normalized_query="what industry added the most jobs",
        calculation_type="ranking",
    )
    q = generate_clarification(intent, [], ["comparison_period"])
    assert "period" in q.lower() or "month" in q.lower() or "year" in q.lower()


# ---------------------------------------------------------------------------
# Phase 3 — apply_safe_defaults
# ---------------------------------------------------------------------------


def test_apply_safe_defaults_ce_sets_sa() -> None:
    from example_server.ambiguity import apply_safe_defaults
    intent = QueryIntent(original_query="payrolls", normalized_query="payrolls", dataset="CE")
    candidates = [
        _make_candidate("CES0000000001", "nonfarm_payrolls", "level", seasonal="S"),
        _make_candidate("CEU0000000001", "nonfarm_payrolls", "level", seasonal="U"),
    ]
    resolved, defaults_applied = apply_safe_defaults(intent, candidates)
    assert len(resolved) == 1
    assert resolved[0].series_id == "CES0000000001"
    assert any("seasonally adjusted" in d.lower() for d in defaults_applied)


def test_apply_safe_defaults_cu_sets_nsa() -> None:
    from example_server.ambiguity import apply_safe_defaults
    intent = QueryIntent(original_query="cpi", normalized_query="cpi", dataset="CU")
    candidates = [
        _make_candidate("CUUR0000SA0", "cpi_all_items", "index", seasonal="U"),
        _make_candidate("CUSR0000SA0", "cpi_all_items", "index", seasonal="S"),
    ]
    resolved, defaults_applied = apply_safe_defaults(intent, candidates)
    assert len(resolved) == 1
    assert resolved[0].series_id == "CUUR0000SA0"


def test_apply_safe_defaults_no_op_when_sa_explicit() -> None:
    from example_server.ambiguity import apply_safe_defaults
    intent = QueryIntent(
        original_query="cpi",
        normalized_query="cpi",
        dataset="CU",
        seasonal_adjustment="S",
    )
    candidates = [
        _make_candidate("CUUR0000SA0", "cpi_all_items", "index", seasonal="U"),
        _make_candidate("CUSR0000SA0", "cpi_all_items", "index", seasonal="S"),
    ]
    resolved, defaults_applied = apply_safe_defaults(intent, candidates)
    # Explicit SA="S" in intent overrides the default
    assert len(resolved) == 1
    assert resolved[0].series_id == "CUSR0000SA0"
