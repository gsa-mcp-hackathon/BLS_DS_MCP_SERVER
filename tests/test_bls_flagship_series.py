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
