"""Coverage regression tests for BLS top-picks series.

These tests run entirely from local cache — no network access required.

After Sub-Task 1 (loader) is complete, the loader and structural tests pass.
The parametrized flagship-coverage tests will fail until Sub-Tasks 3–6 add
the missing entries to bls_flagship_series.py.
"""

from __future__ import annotations

import pytest

from example_server.bls_flagship_series import get_flagship
from example_server.bls_series_schema import decode_id
from example_server.bls_top_picks import TOP_PICKS, TOP_PICKS_BY_ID, TopPickEntry

# ---------------------------------------------------------------------------
# Loader and structural integrity
# ---------------------------------------------------------------------------


def test_top_picks_loader_parses_all_series() -> None:
    """Exactly 29 entries must be loaded with non-empty required fields."""
    assert len(TOP_PICKS) == 29, (
        f"Expected 29 TopPickEntry objects, got {len(TOP_PICKS)}"
    )
    for entry in TOP_PICKS:
        assert entry.series_id, f"Empty series_id in entry: {entry!r}"
        assert entry.title, f"Empty title in entry: {entry!r}"
        assert entry.category, f"Empty category in entry: {entry!r}"


def test_top_picks_categories_present() -> None:
    """All four expected categories must appear in TOP_PICKS."""
    categories = {e.category for e in TOP_PICKS}
    expected = {"Employment", "Productivity", "Price Indexes", "Compensation"}
    assert expected <= categories, f"Missing categories: {expected - categories}"


def test_no_duplicate_top_picks_series_ids() -> None:
    """No series ID must appear more than once in TOP_PICKS."""
    ids = [e.series_id for e in TOP_PICKS]
    assert len(ids) == len(set(ids)), "Duplicate series IDs found in TOP_PICKS: " + str(
        [sid for sid in set(ids) if ids.count(sid) > 1]
    )


def test_top_picks_by_id_index_matches_list() -> None:
    """TOP_PICKS_BY_ID must contain exactly the same entries as TOP_PICKS."""
    assert len(TOP_PICKS_BY_ID) == len(TOP_PICKS)
    for entry in TOP_PICKS:
        assert TOP_PICKS_BY_ID.get(entry.series_id) is entry


# ---------------------------------------------------------------------------
# Parametrized: every top-pick must be in the flagship table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", TOP_PICKS)
def test_all_top_picks_in_flagship(entry: TopPickEntry) -> None:
    """Every top-picks series_id must be found by get_flagship().

    This test fails for the ~20 series that are missing from the flagship
    table until Sub-Tasks 3–6 are complete.
    """
    result = get_flagship(entry.series_id)
    assert result is not None, (
        f"series_id {entry.series_id!r} ({entry.title!r}) is not in FLAGSHIP_SERIES"
    )


# ---------------------------------------------------------------------------
# Parametrized: every top-pick ID must be decodable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", TOP_PICKS)
def test_all_top_picks_decodable(entry: TopPickEntry) -> None:
    """decode_id() must not return an 'error' key for any top-picks series."""
    result = decode_id(entry.series_id)
    assert "error" not in result, (
        f"decode_id({entry.series_id!r}) returned error: {result.get('error')}"
    )


# ---------------------------------------------------------------------------
# Parametrized: flagship metadata completeness for entries that ARE present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", TOP_PICKS)
def test_all_top_picks_flagship_metadata_correct(entry: TopPickEntry) -> None:
    """For top-picks entries present in the flagship table, required metadata
    fields must be non-empty.

    Skipped (not failed) when the entry is not yet in the flagship table so
    that this check does not duplicate the failure already reported by
    test_all_top_picks_in_flagship.
    """
    flagship = get_flagship(entry.series_id)
    if flagship is None:
        pytest.skip(
            f"{entry.series_id!r} not yet in flagship table — "
            "covered by test_all_top_picks_in_flagship"
        )
    assert flagship.series_id, (
        f"Empty series_id on flagship entry for {entry.series_id!r}"
    )
    assert flagship.survey, f"Empty survey on flagship entry for {entry.series_id!r}"
    assert flagship.concept, f"Empty concept on flagship entry for {entry.series_id!r}"
    assert flagship.measure_type, (
        f"Empty measure_type on flagship entry for {entry.series_id!r}"
    )
    assert flagship.unit, f"Empty unit on flagship entry for {entry.series_id!r}"


# ---------------------------------------------------------------------------
# Per-program-family coverage (each family must have ≥1 flagship match)
# ---------------------------------------------------------------------------


def _flagship_ids_for_prefix(prefix: str) -> set[str]:
    return {e.series_id for e in TOP_PICKS if e.series_id.startswith(prefix)}


def _any_in_flagship(series_ids: set[str]) -> bool:
    return any(get_flagship(sid) is not None for sid in series_ids)


def test_top_picks_ln_coverage() -> None:
    """LN (Labor Force Statistics) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("LN")
    assert ids, "No LN series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the LN top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_ce_coverage() -> None:
    """CE (Current Employment Statistics) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("CE")
    assert ids, "No CE series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the CE top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_pr_coverage() -> None:
    """PR (Productivity) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("PR")
    assert ids, "No PR series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the PR top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_mp_coverage() -> None:
    """MP (Multifactor Productivity) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("MP")
    assert ids, "No MP series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the MP top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_cu_coverage() -> None:
    """CU (CPI-U) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("CU")
    assert ids, "No CU series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the CU top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_cw_coverage() -> None:
    """CW (CPI-W) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("CW")
    assert ids, "No CW series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the CW top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_wp_coverage() -> None:
    """WP (PPI) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("WP")
    assert ids, "No WP series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the WP top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_ei_coverage() -> None:
    """EI (Import/Export Price Indexes) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("EI")
    assert ids, "No EI series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the EI top-picks {ids} are in FLAGSHIP_SERIES"
    )


def test_top_picks_ci_coverage() -> None:
    """CI (Employment Cost Index) top-picks have ≥1 flagship match."""
    ids = _flagship_ids_for_prefix("CI")
    assert ids, "No CI series in TOP_PICKS"
    assert _any_in_flagship(ids), (
        f"None of the CI top-picks {ids} are in FLAGSHIP_SERIES"
    )
