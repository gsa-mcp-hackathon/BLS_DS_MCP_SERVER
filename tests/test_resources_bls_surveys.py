"""Tests for example_server.resources.bls_surveys.

Covers both content-builder functions (_build_overview, _build_survey_detail)
and the MCP resource registration (bls://surveys/overview and the
bls://surveys/{survey_code} template).  No network calls are made — all data
comes from the local-cache files and in-process schema definitions.
"""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from example_server.bls_series_schema import SCHEMAS
from example_server.resources.bls_surveys import _build_overview, _build_survey_detail

# ---------------------------------------------------------------------------
# _build_overview — content checks
# ---------------------------------------------------------------------------


def test_overview_contains_all_five_survey_prefixes() -> None:
    """Every supported survey prefix must appear in the overview."""
    text = _build_overview()
    for prefix in SCHEMAS:
        assert prefix in text, f"Survey prefix '{prefix}' missing from overview"


def test_overview_contains_survey_full_names() -> None:
    text = _build_overview()
    assert "State and Metro Area Employment" in text
    assert "Current Employment Statistics" in text
    assert "Local Area Unemployment Statistics" in text
    assert "Job Openings and Labor Turnover" in text
    assert "Consumer Price Index" in text


def test_overview_contains_key_tool_names() -> None:
    """Tools that agents need to call must be named in the overview."""
    text = _build_overview()
    for tool in (
        "get_series_data",
        "suggest_series",
        "search_series",
        "build_series_id",
    ):
        assert tool in text, f"Tool '{tool}' missing from overview"


def test_overview_contains_api_version_info() -> None:
    """v1 and v2 limits must be documented so agents understand constraints."""
    text = _build_overview()
    assert "v1" in text
    assert "v2" in text
    assert "500" in text  # v2 daily limit
    assert "25" in text  # v1 daily limit


def test_overview_contains_registration_url() -> None:
    text = _build_overview()
    assert "data.bls.gov/registrationEngine" in text


def test_overview_contains_step_instructions() -> None:
    """Step-by-step guidance headings must appear."""
    text = _build_overview()
    assert "Step 1" in text
    assert "Step 2" in text
    assert "Step 3" in text


def test_overview_is_non_empty_string() -> None:
    text = _build_overview()
    assert isinstance(text, str)
    assert len(text) > 500


# ---------------------------------------------------------------------------
# _build_survey_detail — per-survey content checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("survey_code", list(SCHEMAS.keys()))
def test_survey_detail_renders_without_error(survey_code: str) -> None:
    """Every supported survey code must produce a non-empty string."""
    text = _build_survey_detail(survey_code)
    assert isinstance(text, str)
    assert len(text) > 100


@pytest.mark.parametrize("survey_code", list(SCHEMAS.keys()))
def test_survey_detail_contains_prefix(survey_code: str) -> None:
    """The survey code must appear in its own detail page."""
    text = _build_survey_detail(survey_code)
    assert survey_code in text


@pytest.mark.parametrize("survey_code", list(SCHEMAS.keys()))
def test_survey_detail_contains_series_length(survey_code: str) -> None:
    """Series ID total length must be documented."""
    text = _build_survey_detail(survey_code)
    expected_length = str(SCHEMAS[survey_code].total_length)
    assert expected_length in text


def test_survey_detail_sm_contains_segment_positions() -> None:
    """SM detail must show character position layout."""
    text = _build_survey_detail("SM")
    assert "Pos" in text
    assert "seasonal" in text
    assert "state_code" in text
    assert "area_code" in text


def test_survey_detail_sm_contains_catalog_entry_counts() -> None:
    """SM detail must show live code counts from local-cache."""
    text = _build_survey_detail("SM")
    # sm.area has 433 entries; any positive integer count should appear
    assert "codes" in text


def test_survey_detail_la_contains_area_type_note() -> None:
    """LA detail must document area type codes (A=Statewide, etc.)."""
    text = _build_survey_detail("LA")
    assert "A=Statewide" in text or "Statewide" in text
    assert "area_type" in text.lower()


def test_survey_detail_jt_contains_dataelement_codes() -> None:
    """JT detail must mention key JOLTS data elements."""
    text = _build_survey_detail("JT")
    assert "JO" in text  # Job Openings
    assert "HI" in text  # Hires
    assert "QU" in text  # Quits


def test_survey_detail_cu_contains_common_item_codes() -> None:
    """CU detail must mention common CPI item codes."""
    text = _build_survey_detail("CU")
    assert "SA0" in text  # All Items
    assert "SA0L1E" in text  # Core CPI


def test_survey_detail_cu_contains_periodicity_note() -> None:
    text = _build_survey_detail("CU")
    assert "R=Monthly" in text or "Monthly" in text


def test_survey_detail_ce_contains_update_frequency() -> None:
    text = _build_survey_detail("CE")
    assert "Employment Situation" in text or "Monthly" in text


def test_survey_detail_unknown_survey_returns_error_message() -> None:
    text = _build_survey_detail("XX")
    assert "not supported" in text.lower()
    assert "XX" in text


def test_survey_detail_unknown_lists_supported_codes() -> None:
    text = _build_survey_detail("ZZ")
    for prefix in SCHEMAS:
        assert prefix in text


def test_survey_detail_unknown_points_to_overview() -> None:
    text = _build_survey_detail("XX")
    assert "bls://surveys/overview" in text


def test_survey_detail_contains_tool_guidance() -> None:
    """Each survey detail must include step-by-step tool guidance."""
    for survey_code in SCHEMAS:
        text = _build_survey_detail(survey_code)
        assert "get_series_data" in text, (
            f"get_series_data missing from {survey_code} detail"
        )


# ---------------------------------------------------------------------------
# MCP resource registration — read via the live server instance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overview_resource_is_listed() -> None:
    """bls://surveys/overview must appear in the static resource list."""
    from example_server.app import mcp

    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "bls://surveys/overview" in uris


@pytest.mark.asyncio
async def test_detail_template_is_listed() -> None:
    """bls://surveys/{survey_code} must appear as a resource template."""
    from example_server.app import mcp

    templates = await mcp.list_resource_templates()
    uri_templates = {r.uri_template for r in templates}
    assert "bls://surveys/{survey_code}" in uri_templates


@pytest.mark.asyncio
async def test_overview_resource_returns_content() -> None:
    from example_server.app import mcp

    result = await mcp.read_resource("bls://surveys/overview")
    text = result.contents[0].content
    assert "BLS Time Series Surveys" in text
    assert len(text) > 500


@pytest.mark.asyncio
@pytest.mark.parametrize("survey_code", list(SCHEMAS.keys()))
async def test_detail_resource_returns_content_for_each_survey(
    survey_code: str,
) -> None:
    from example_server.app import mcp

    result = await mcp.read_resource(f"bls://surveys/{survey_code}")
    text = result.contents[0].content
    assert survey_code in text
    assert len(text) > 100


@pytest.mark.asyncio
async def test_detail_resource_unknown_survey_returns_graceful_message() -> None:
    from example_server.app import mcp

    result = await mcp.read_resource("bls://surveys/XX")
    text = result.contents[0].content
    assert "not supported" in text.lower()


@pytest.mark.asyncio
async def test_resources_register_without_error() -> None:
    """register() must not raise when called on a fresh FastMCP instance."""
    from example_server.resources.bls_surveys import register

    register(FastMCP("test-bls-resources"))  # must not raise
