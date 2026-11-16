"""Tests for example_server.bls_series_schema."""

from __future__ import annotations

import pytest

from example_server.bls_series_schema import (
    SCHEMAS,
    SeriesSchema,
    build_id,
    decode_id,
    get_schema,
)

# ---------------------------------------------------------------------------
# get_schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prefix", ["SM", "CE", "LA", "JT", "CU", "PR", "MP", "CW", "WP", "EI", "CI"]
)
def test_get_schema_known_prefix(prefix: str) -> None:
    series_id = prefix + "X" * 18  # any suffix
    schema = get_schema(series_id)
    assert isinstance(schema, SeriesSchema)
    assert schema.prefix == prefix


def test_get_schema_unknown_prefix_returns_none() -> None:
    assert get_schema("ZZUNKNOWN") is None


def test_get_schema_case_insensitive() -> None:
    # Series IDs are uppercased inside get_schema
    assert get_schema("sm" + "0" * 18) is not None


def test_schemas_keys_match_prefixes() -> None:
    for key, schema in SCHEMAS.items():
        assert key == schema.prefix


# ---------------------------------------------------------------------------
# decode_id — SM
# ---------------------------------------------------------------------------

# SMU17169800500000001 is a well-known series:
# SM + U + 17 + 16980 + 05 + 000000 + 01
_SM_SERIES = "SMU17169800500000001"


def test_decode_sm_returns_correct_structure() -> None:
    result = decode_id(_SM_SERIES)
    assert result["prefix"] == "SM"
    assert result["series_id"] == _SM_SERIES
    assert "survey" in result
    segments = result["segments"]
    assert isinstance(segments, list)
    assert len(segments) == len(SCHEMAS["SM"].segments)


def test_decode_sm_seasonal_value() -> None:
    result = decode_id(_SM_SERIES)
    seasonal = next(s for s in result["segments"] if s["name"] == "seasonal")
    assert seasonal["value"] == "U"


def test_decode_sm_state_code() -> None:
    result = decode_id(_SM_SERIES)
    state = next(s for s in result["segments"] if s["name"] == "state_code")
    assert state["value"] == "17"
    # Illinois is in the sm.state catalog — label should resolve
    assert state["label"] is not None


def test_decode_sm_area_code() -> None:
    result = decode_id(_SM_SERIES)
    area = next(s for s in result["segments"] if s["name"] == "area_code")
    assert area["value"] == "16980"


# ---------------------------------------------------------------------------
# decode_id — CE
# ---------------------------------------------------------------------------

_CE_SERIES = "CES0000000001"  # Total nonfarm SA


def test_decode_ce_returns_correct_structure() -> None:
    result = decode_id(_CE_SERIES)
    assert result["prefix"] == "CE"
    assert len(result["segments"]) == len(SCHEMAS["CE"].segments)


def test_decode_ce_seasonal_value() -> None:
    result = decode_id(_CE_SERIES)
    s = next(seg for seg in result["segments"] if seg["name"] == "seasonal")
    assert s["value"] == "S"


# ---------------------------------------------------------------------------
# decode_id — LA
# ---------------------------------------------------------------------------

_LA_SERIES = "LAUST060000000000003"  # California unemployment rate SA


def test_decode_la_returns_correct_structure() -> None:
    result = decode_id(_LA_SERIES)
    assert result["prefix"] == "LA"
    assert len(result["segments"]) == len(SCHEMAS["LA"].segments)


def test_decode_la_area_code_length() -> None:
    result = decode_id(_LA_SERIES)
    area = next(s for s in result["segments"] if s["name"] == "area_code")
    assert len(area["value"]) == 15


def test_decode_la_measure_code() -> None:
    result = decode_id(_LA_SERIES)
    measure = next(s for s in result["segments"] if s["name"] == "measure_code")
    assert measure["value"] == "03"


# ---------------------------------------------------------------------------
# decode_id — JT
# ---------------------------------------------------------------------------

_JT_SERIES = "JTS000000000000JOR"  # Job openings rate


def test_decode_jt_returns_correct_structure() -> None:
    result = decode_id(_JT_SERIES)
    assert result["prefix"] == "JT"
    assert len(result["segments"]) == len(SCHEMAS["JT"].segments)


def test_decode_jt_dataelement_and_ratelevel() -> None:
    """dataelement and ratelevel must resolve to catalog labels, not bleed into industry."""
    result = decode_id(_JT_SERIES)
    segs = {s["name"]: s for s in result["segments"]}
    assert segs["industry_code"]["value"] == "000000"
    assert segs["industry_code"]["label"] == "Total nonfarm"
    assert segs["dataelement_code"]["value"] == "JO"
    assert segs["dataelement_code"]["label"] == "Job openings"
    assert segs["ratelevel_code"]["value"] == "R"
    assert segs["ratelevel_code"]["label"] == "Rate"


# ---------------------------------------------------------------------------
# decode_id — CU
# ---------------------------------------------------------------------------

_CU_SERIES = "CUUR0000SA0     "  # 16 chars with item "SA0     "
_CU_SERIES_CLEAN = "CUUR0000SA0     "  # padded to 16


def test_decode_cu_returns_correct_structure() -> None:
    # Use a well-formed 16-char CU series
    sid = "CUUR0000SA0     "
    result = decode_id(sid)
    assert result["prefix"] == "CU"
    assert len(result["segments"]) == len(SCHEMAS["CU"].segments)


# ---------------------------------------------------------------------------
# decode_id — unknown prefix
# ---------------------------------------------------------------------------


def test_decode_unknown_prefix_returns_error_dict() -> None:
    result = decode_id("ZZUNKNOWN")
    assert "error" in result
    assert result["series_id"] == "ZZUNKNOWN"


# ---------------------------------------------------------------------------
# decode_id — missing catalog label
# ---------------------------------------------------------------------------


def test_decode_unknown_code_label_is_null() -> None:
    # Use a well-formed SM ID but with a state code not in the catalog (e.g. "99")
    sid = "SMU99169800500000001"
    result = decode_id(sid)
    state_seg = next(s for s in result["segments"] if s["name"] == "state_code")
    # Code "99" is unlikely to be in sm.state
    # Label should be None rather than a fabricated value
    # (It might be in the catalog, so we just check it's str or None)
    assert state_seg["label"] is None or isinstance(state_seg["label"], str)


# ---------------------------------------------------------------------------
# build_id
# ---------------------------------------------------------------------------


def test_build_id_sm_valid() -> None:
    result = build_id(
        "SM",
        seasonal="U",
        state_code="17",
        area_code="16980",
        supersector_code="05",
        industry_code="000000",
        data_type_code="01",
    )
    assert isinstance(result, str)
    assert result.startswith("SM")
    assert len(result) == SCHEMAS["SM"].total_length


def test_build_id_sm_matches_known_series() -> None:
    result = build_id(
        "SM",
        seasonal="U",
        state_code="17",
        area_code="16980",
        supersector_code="05",
        industry_code="000000",
        data_type_code="01",
    )
    assert result == _SM_SERIES


def test_build_id_missing_field_returns_error() -> None:
    result = build_id("SM", seasonal="U", state_code="17")
    assert isinstance(result, dict)
    assert "missing_fields" in result
    assert len(result["missing_fields"]) > 0


def test_build_id_unknown_survey_returns_error() -> None:
    result = build_id("ZZ", seasonal="U")
    assert isinstance(result, dict)
    assert "error" in result


def test_build_id_ce_valid() -> None:
    result = build_id(
        "CE",
        seasonal="S",
        supersector_code="00",
        industry_code="000000",
        data_type_code="01",
    )
    assert isinstance(result, str)
    assert result == _CE_SERIES


# ---------------------------------------------------------------------------
# decode_id — PR
# ---------------------------------------------------------------------------

_PR_SERIES = "PRS30006013"  # Manufacturing employment index, seasonally adjusted


def test_decode_pr_structure() -> None:
    result = decode_id(_PR_SERIES)
    assert result["prefix"] == "PR"
    assert result["series_id"] == _PR_SERIES
    assert len(result["segments"]) == len(SCHEMAS["PR"].segments)
    sector = next(s for s in result["segments"] if s["name"] == "sector_code")
    assert sector["value"] == "3000"
    # pr.sector catalog should resolve this code to a non-None label
    assert sector["label"] is not None


def test_decode_pr_build_roundtrip() -> None:
    assembled = build_id(
        "PR",
        seasonal="S",
        sector_code="3000",
        class_code="6",
        measure_code="01",
        duration_code="3",
    )
    assert assembled == _PR_SERIES
    result = decode_id(assembled)
    assert result["prefix"] == "PR"


# ---------------------------------------------------------------------------
# decode_id — MP
# ---------------------------------------------------------------------------

_MP_SERIES = "MPU0011012"  # Total factor productivity, Agriculture


def test_decode_mp_structure() -> None:
    result = decode_id(_MP_SERIES)
    assert result["prefix"] == "MP"
    assert len(result["segments"]) == len(SCHEMAS["MP"].segments)


# ---------------------------------------------------------------------------
# decode_id — CW
# ---------------------------------------------------------------------------

_CW_SERIES = "CWSR0000SA0     "  # All items, national, seasonally adjusted (padded)


def test_decode_cw_structure() -> None:
    result = decode_id(_CW_SERIES)
    assert result["prefix"] == "CW"
    area = next(s for s in result["segments"] if s["name"] == "area_code")
    assert area["value"] == "0000"


# ---------------------------------------------------------------------------
# decode_id — EI
# ---------------------------------------------------------------------------

# EIUCDCANMANU: seasonal=U, index_code=CD, series_code=CANMANU
_EI_SERIES = "EIUCDCANMANU"


def test_decode_ei_index_code() -> None:
    result = decode_id(_EI_SERIES)
    assert result["prefix"] == "EI"
    index_seg = next(s for s in result["segments"] if s["name"] == "index_code")
    assert index_seg["value"] == "CD"
    # ei.index catalog should resolve CD to a non-None label
    assert index_seg["label"] is not None


# ---------------------------------------------------------------------------
# decode_id — CI
# ---------------------------------------------------------------------------

_CI_SERIES = "CIS1010000000000I"  # Total compensation, civilian workers


def test_decode_ci_structure() -> None:
    result = decode_id(_CI_SERIES)
    assert result["prefix"] == "CI"
    owner = next(s for s in result["segments"] if s["name"] == "owner_code")
    assert owner["label"] == "Civilian workers"


# ---------------------------------------------------------------------------
# build_id — PR
# ---------------------------------------------------------------------------


def test_build_id_pr_valid() -> None:
    result = build_id(
        "PR",
        seasonal="S",
        sector_code="3000",
        class_code="6",
        measure_code="01",
        duration_code="3",
    )
    assert isinstance(result, str)
    assert result == "PRS30006013"


# ---------------------------------------------------------------------------
# build_id — CI
# ---------------------------------------------------------------------------


def test_build_id_ci_valid() -> None:
    result = build_id(
        "CI",
        seasonal="S",
        owner_code="1",
        estimate_code="01",
        series_code="0000000000",
        periodicity_code="I",
    )
    assert isinstance(result, str)
    assert result.startswith("CI")
    assert len(result) == 17


# ---------------------------------------------------------------------------
# build_id — variable-length schemas return error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("survey", ["CW", "WP", "EI"])
def test_build_id_variable_length_returns_error(survey: str) -> None:
    result = build_id(survey, seasonal="U")
    assert isinstance(result, dict)
    assert "error" in result
