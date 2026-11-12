"""Tests for build_series_id, decode_series_id, and validate_series_id tools."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Shared helper to capture the inner tool function from register()
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
# build_series_id
# ---------------------------------------------------------------------------


def test_build_series_id_valid_sm() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(
        survey="SM",
        seasonal_adjustment="U",
        state_code="17",
        area_code="16980",
        supersector_code="05",
        industry_code="000000",
        data_type_code="01",
    )
    assert "series_id" in result
    assert result["series_id"] == "SMU17169800500000001"
    assert "decoded" in result
    assert result["decoded"]["prefix"] == "SM"


def test_build_series_id_valid_ce() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(
        survey="CE",
        seasonal_adjustment="S",
        supersector_code="00",
        industry_code="000000",
        data_type_code="01",
    )
    assert "series_id" in result
    assert result["series_id"] == "CES0000000001"


def test_build_series_id_missing_required_field() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(
        survey="SM",
        seasonal_adjustment="U",
        state_code="17",
        # missing area_code, supersector_code, industry_code, data_type_code
    )
    assert "error" in result
    assert "missing_fields" in result
    assert len(result["missing_fields"]) > 0


def test_build_series_id_unknown_survey() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(survey="ZZ", seasonal_adjustment="U")
    assert "error" in result


# ---------------------------------------------------------------------------
# decode_series_id
# ---------------------------------------------------------------------------


def test_decode_series_id_known_sm() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="SMU17169800500000001")
    assert result["prefix"] == "SM"
    assert "segments" in result
    assert len(result["segments"]) > 0


def test_decode_series_id_state_label_resolved() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="SMU17169800500000001")
    state_seg = next(s for s in result["segments"] if s["name"] == "state_code")
    # Illinois (17) should resolve to a label
    assert state_seg["label"] is not None
    assert "Illinois" in state_seg["label"] or state_seg["value"] == "17"


def test_decode_series_id_unknown_prefix() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="ZZUNKNOWN")
    assert "error" in result
    assert result["series_id"] == "ZZUNKNOWN"


def test_decode_series_id_label_null_for_unknown_code() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    # State code "88" is not in sm.state catalog (verified absent)
    result = fn(series_id="SMU88169800500000001")
    state_seg = next(s for s in result["segments"] if s["name"] == "state_code")
    # "88" is not a real state FIPS — label must be None, not fabricated
    assert state_seg["label"] is None


def test_decode_series_id_ce() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="CES0000000001")
    assert result["prefix"] == "CE"
    segs = {s["name"]: s for s in result["segments"]}
    assert segs["seasonal"]["value"] == "S"


def test_decode_series_id_la() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="LAUST060000000000003")
    assert result["prefix"] == "LA"
    segs = {s["name"]: s for s in result["segments"]}
    assert len(segs["area_code"]["value"]) == 15
    assert segs["measure_code"]["value"] == "03"


# ---------------------------------------------------------------------------
# validate_series_id
# ---------------------------------------------------------------------------


def test_validate_valid_sm_series() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="SMU17169800500000001")
    assert result["valid"] is True
    assert result["issues"] == []
    assert result["decoded"] is not None


def test_validate_unknown_prefix() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="ZZUNKNOWN")
    assert result["valid"] is False
    assert any("Unrecognised" in issue for issue in result["issues"])


def test_validate_wrong_length() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    # SM series should be 20 chars; "SM" + 5 chars = 7 total
    result = fn(series_id="SMUXX")
    assert result["valid"] is False
    assert any("length" in issue.lower() for issue in result["issues"])


def test_validate_code_not_in_catalog_reports_issue() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    # State code "88" is not in sm.state catalog (verified absent)
    result = fn(series_id="SMU88169800500000001")
    # valid=False because state_code "88" is not in catalog
    assert result["valid"] is False
    assert any("state_code" in issue for issue in result["issues"])


def test_validate_valid_ce_series() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="CES0000000001")
    assert result["valid"] is True


def test_validate_valid_la_series() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="LAUST060000000000003")
    # CA area code should be in la.area catalog
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# build_series_id — PR and CI (new surveys)
# ---------------------------------------------------------------------------


def test_build_series_id_valid_pr() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(
        survey="PR",
        seasonal_adjustment="S",
        sector_code="3000",
        class_code="6",
        measure_code="01",
        duration_code="3",
    )
    assert "series_id" in result
    assert result["series_id"] == "PRS30006013"
    assert result["decoded"]["prefix"] == "PR"


def test_build_series_id_valid_ci() -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    # CI schema: seasonal(1)+owner_code(1)+estimate_code(2)+series_code(10)+periodicity_code(1)
    # Total body = 15; with "CI" prefix = 17 chars.
    result = fn(
        survey="CI",
        seasonal_adjustment="S",
        owner_code="1",
        estimate_code="01",
        series_code="0000000000",
        periodicity_code="I",
    )
    assert "series_id" in result
    assert result["series_id"].startswith("CI")
    assert len(result["series_id"]) == 17
    assert result["decoded"]["prefix"] == "CI"


@pytest.mark.parametrize("survey", ["CW", "WP", "EI"])
def test_build_series_id_variable_length_error(survey: str) -> None:
    import example_server.tools.build_series_id as mod

    fn = _capture(mod)
    result = fn(survey=survey, seasonal_adjustment="U")
    assert "error" in result


# ---------------------------------------------------------------------------
# decode_series_id — PR and CI (new surveys)
# ---------------------------------------------------------------------------


def test_decode_series_id_pr() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="PRS30006013")
    assert result["prefix"] == "PR"
    segs = {s["name"]: s for s in result["segments"]}
    assert segs["seasonal"]["value"] == "S"
    assert segs["sector_code"]["label"] is not None  # "3000" → "Manufacturing"


def test_decode_series_id_ci() -> None:
    import example_server.tools.decode_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="CIS1010000000000I")
    assert result["prefix"] == "CI"
    segs = {s["name"]: s for s in result["segments"]}
    assert segs["owner_code"]["label"] == "Civilian workers"


# ---------------------------------------------------------------------------
# validate_series_id — PR, CI, and variable-length CW (new surveys)
# ---------------------------------------------------------------------------


def test_validate_valid_pr_series() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="PRS30006013")
    assert result["valid"] is True
    assert result["issues"] == []


def test_validate_valid_ci_series() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="CIS1010000000000I")
    assert result["valid"] is True


def test_validate_variable_length_cw_no_length_failure() -> None:
    import example_server.tools.validate_series_id as mod

    fn = _capture(mod)
    result = fn(series_id="CWSR0000SA0")
    # A variable-length series must not fail due to length mismatch
    length_issues = [i for i in result.get("issues", []) if "length" in i.lower()]
    assert length_issues == [], f"Unexpected length issues: {length_issues}"
