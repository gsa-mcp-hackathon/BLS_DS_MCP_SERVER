"""Tests for example_server.bls_flagship_series."""

from __future__ import annotations

import pytest

from example_server.bls_flagship_series import (
    FLAGSHIP_SERIES,
    FlagshipEntry,
    get_flagship,
    search_flagship,
)

# ---------------------------------------------------------------------------
# FLAGSHIP_SERIES integrity
# ---------------------------------------------------------------------------


def test_all_five_surveys_represented() -> None:
    surveys = {e.survey for e in FLAGSHIP_SERIES}
    assert surveys == {"SM", "CE", "LA", "JT", "CU"}


def test_each_survey_has_at_least_six_entries() -> None:
    for survey in ("SM", "CE", "LA", "JT", "CU"):
        count = sum(1 for e in FLAGSHIP_SERIES if e.survey == survey)
        assert count >= 6, f"Survey {survey} has only {count} entries"


def test_no_duplicate_series_ids() -> None:
    ids = [e.series_id for e in FLAGSHIP_SERIES]
    assert len(ids) == len(set(ids)), "Duplicate series IDs found in FLAGSHIP_SERIES"


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_entry_has_required_fields(entry: FlagshipEntry) -> None:
    assert entry.series_id, "series_id must not be empty"
    assert entry.survey in ("SM", "CE", "LA", "JT", "CU"), (
        f"Unknown survey: {entry.survey}"
    )
    assert entry.survey_name, "survey_name must not be empty"
    assert entry.description, "description must not be empty"
    assert isinstance(entry.keywords, list), "keywords must be a list"
    assert len(entry.keywords) >= 1, "keywords must have at least one entry"
    assert entry.notes, "notes must not be empty"


def test_series_ids_are_uppercase() -> None:
    for entry in FLAGSHIP_SERIES:
        assert entry.series_id == entry.series_id.upper(), (
            f"{entry.series_id} should be uppercase"
        )


# ---------------------------------------------------------------------------
# get_flagship
# ---------------------------------------------------------------------------


def test_get_flagship_exact_match() -> None:
    entry = get_flagship("CUUR0000SA0")
    assert entry is not None
    assert entry.series_id == "CUUR0000SA0"
    assert entry.survey == "CU"


def test_get_flagship_unknown_returns_none() -> None:
    assert get_flagship("ZZUNKNOWN") is None


def test_get_flagship_case_insensitive_lookup() -> None:
    # The function strips and uppercases internally
    entry = get_flagship("cuur0000sa0")
    assert entry is not None


def test_get_flagship_ce_nonfarm() -> None:
    entry = get_flagship("CES0000000001")
    assert entry is not None
    assert entry.survey == "CE"


def test_get_flagship_la_national() -> None:
    entry = get_flagship("LAUST000000000000003")
    assert entry is not None
    assert entry.survey == "LA"


def test_get_flagship_jt_openings() -> None:
    entry = get_flagship("JTS000000000000001")
    assert entry is not None
    assert entry.survey == "JT"


# ---------------------------------------------------------------------------
# search_flagship
# ---------------------------------------------------------------------------


def test_search_flagship_cpi_keyword() -> None:
    hits = search_flagship("cpi")
    assert len(hits) > 0
    assert all(e.survey == "CU" for e in hits)


def test_search_flagship_unemployment_keyword() -> None:
    hits = search_flagship("unemployment rate")
    assert len(hits) > 0
    # Should find LA entries
    assert any(e.survey == "LA" for e in hits)


def test_search_flagship_case_insensitive() -> None:
    hits_lower = search_flagship("inflation")
    hits_upper = search_flagship("INFLATION")
    assert len(hits_lower) == len(hits_upper)


def test_search_flagship_limit_respected() -> None:
    all_hits = search_flagship("employment", limit=100)
    limited = search_flagship("employment", limit=2)
    assert len(limited) <= 2
    assert len(all_hits) >= len(limited)


def test_search_flagship_no_match_returns_empty() -> None:
    hits = search_flagship("zzznomatchkeyword")
    assert hits == []


def test_search_flagship_empty_topic_returns_up_to_limit() -> None:
    hits = search_flagship("", limit=5)
    assert len(hits) <= 5


def test_search_flagship_nonfarm_payrolls() -> None:
    hits = search_flagship("nonfarm payrolls")
    assert any(e.survey == "CE" for e in hits)


def test_search_flagship_jolts_quits() -> None:
    hits = search_flagship("quits")
    assert any(e.survey == "JT" for e in hits)


# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit
# ---------------------------------------------------------------------------


def test_flagship_entry_has_concept_field() -> None:
    from example_server.bls_flagship_series import FlagshipEntry

    e = FlagshipEntry(
        series_id="TEST000001",
        survey="CE",
        survey_name="Test Survey",
        description="Test",
        keywords=["test"],
        notes="Test notes.",
        concept="test_concept",
        measure_type="level",
        unit="thousands of persons",
    )
    assert e.concept == "test_concept"
    assert e.measure_type == "level"
    assert e.unit == "thousands of persons"


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_concept(entry: FlagshipEntry) -> None:
    assert entry.concept, f"{entry.series_id}: concept must not be empty"


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_measure_type(entry: FlagshipEntry) -> None:
    valid = {"level", "rate", "index", "dollar_amount"}
    assert entry.measure_type in valid, (
        f"{entry.series_id}: measure_type '{entry.measure_type}' not in {valid}"
    )


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_unit(entry: FlagshipEntry) -> None:
    assert entry.unit, f"{entry.series_id}: unit must not be empty"


def test_cpi_entries_are_index_type() -> None:
    from example_server.bls_flagship_series import get_flagship

    for sid in ("CUUR0000SA0", "CUSR0000SA0", "CUUR0000SAF1"):
        e = get_flagship(sid)
        assert e is not None
        assert e.measure_type == "index"
        assert e.unit == "index 1982-84=100"


def test_la_entries_are_rate_percent() -> None:
    from example_server.bls_flagship_series import get_flagship

    for sid in ("LAUST000000000000003", "LAUNT000000000000003"):
        e = get_flagship(sid)
        assert e is not None
        assert e.measure_type == "rate"
        assert e.unit == "percent"


def test_ce_nonfarm_is_level_thousands() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("CES0000000001")
    assert e is not None
    assert e.concept == "nonfarm_payrolls"
    assert e.measure_type == "level"
    assert e.unit == "thousands of persons"


def test_ce_earnings_is_dollar_amount() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("CES0500000003")
    assert e is not None
    assert e.concept == "average_hourly_earnings"
    assert e.measure_type == "dollar_amount"
    assert e.unit == "dollars per hour"


def test_jt_openings_level() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("JTS000000000000001")
    assert e is not None
    assert e.concept == "job_openings"
    assert e.measure_type == "level"


def test_jt_openings_rate() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("JTS000000000000JOR")
    assert e is not None
    assert e.concept == "job_openings_rate"
    assert e.measure_type == "rate"
    assert e.unit == "percent"
