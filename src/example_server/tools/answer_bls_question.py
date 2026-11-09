"""Tool: answer_bls_question — answer a natural-language BLS data question.

Orchestrates the discovery → validation → retrieval pipeline in one call:

  1. suggest_series (flagship table) to find candidate series IDs for the topic.
  2. validate_series_id to confirm the top candidate is well-formed (local check).
  3. get_series_data to fetch live observations from the BLS Public Data API.
  4. Return a structured response with the observations, a plain-language summary
     line, and full provenance (series ID, label, api_version, footnote guide).

The caller never needs to know BLS Series IDs, survey codes, or v1/v2 limits.

If the caller already knows the series ID, pass it via `series_id` to skip the
discovery step and go straight to validation + retrieval.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_flagship_series import search_flagship
from example_server.bls_series_schema import decode_id
from example_server.config import get_bls_api_version
from example_server.models import BLSSeriesRequest
from example_server.utils import (
    BLSAPIError,
    UpstreamServiceError,
    fetch_bls,
    unwrap_bls_response,
    validate_series_request,
)

# ---------------------------------------------------------------------------
# Internal helpers (not registered as MCP tools)
# ---------------------------------------------------------------------------


def _build_summary(series_id: str, label: str, observations: list[dict]) -> str:
    """Return a single plain-English sentence summarising the most recent data."""
    if not observations:
        return f"No observations returned for {series_id}."
    # BLS returns data newest-first in the data array.
    latest = observations[0]
    year = latest.get("year", "")
    period_name = latest.get("periodName", latest.get("period_name", ""))
    value = latest.get("value", "")
    footnotes = latest.get("footnotes", [])
    flag = ""
    if footnotes:
        codes = [
            f.get("code", "") if isinstance(f, dict) else str(f) for f in footnotes if f
        ]
        if "P" in codes:
            flag = " (preliminary)"
        elif "R" in codes:
            flag = " (revised)"
    period_str = f"{period_name} {year}".strip()
    return f"Most recent value for {label}: {value}{flag} ({period_str})."


def _discover_series(question: str) -> dict[str, Any] | None:
    """Return the top flagship suggestion for the question, or None."""
    hits = search_flagship(question, limit=3)
    if not hits:
        return None
    best = hits[0]
    return {
        "series_id": best.series_id,
        "survey_name": best.survey_name,
        "description": best.description,
        "rationale": best.notes,
    }


def _validate_locally(series_id: str) -> tuple[bool, list[str]]:
    """Return (valid, issues) using a lightweight local prefix check.

    Only the survey prefix is required to be recognised — length and catalog
    mismatches are surfaced as informational issues but do NOT block retrieval.
    BLS publishes valid series IDs (e.g. CPI items shorter than 16 chars,
    national aggregate codes absent from local TSV files) that would fail
    stricter checks; the live API is the authoritative validator.
    """
    from example_server.bls_series_schema import SCHEMAS, get_schema  # noqa: PLC0415

    sid = series_id.strip().upper()
    schema = get_schema(sid)
    if schema is None:
        prefix = sid[:2] if len(sid) >= 2 else sid
        known = ", ".join(sorted(SCHEMAS))
        return False, [f"Unrecognised survey prefix '{prefix}'. Supported: {known}."]
    # Prefix is recognised — treat the ID as valid for the purposes of
    # attempting retrieval.  Non-fatal warnings are informational only.
    return True, []


async def _fetch_observations(
    series_id: str,
    start_year: int | None,
    end_year: int | None,
) -> tuple[list[dict], str | None]:
    """Fetch observations; return (observations, error_message)."""
    try:
        request = BLSSeriesRequest(
            series_ids=[series_id],
            start_year=start_year,
            end_year=end_year,
        )
    except Exception as exc:
        return [], str(exc)

    try:
        validate_series_request(request)
    except BLSAPIError as exc:
        return [], str(exc)

    payload: dict[str, Any] = {"seriesid": [series_id]}
    if start_year is not None:
        payload["startyear"] = str(start_year)
    if end_year is not None:
        payload["endyear"] = str(end_year)

    try:
        raw = await fetch_bls(payload)
        series_list = unwrap_bls_response(raw)
    except (BLSAPIError, UpstreamServiceError) as exc:
        return [], str(exc)

    if not series_list:
        return [], "BLS returned an empty series list."
    return series_list[0].get("data", []), None


def _label_for(series_id: str) -> str:
    """Derive a human-readable label from the decoded series ID segments."""
    decoded = decode_id(series_id.strip().upper())
    if "error" in decoded or not decoded.get("segments"):
        return series_id
    parts = [
        s["label"] or s["value"]
        for s in decoded["segments"]
        if s.get("label") or s.get("value")
    ]
    return f"{decoded.get('survey', series_id)} — " + ", ".join(parts[:3])


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------


def register(mcp: FastMCP) -> None:
    """Register the answer_bls_question orchestrator tool."""

    @mcp.tool(
        name="answer_bls_question",
        annotations={
            "title": "Answer a BLS Data Question",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def answer_bls_question(
        question: Annotated[
            str,
            "Natural-language question about BLS data "
            "(e.g. 'What was the national unemployment rate in 2023?').",
        ],
        series_id: Annotated[
            str | None,
            "Optional: provide a known BLS series ID to skip discovery "
            "(e.g. 'LNS14000000'). When omitted, the tool discovers the "
            "best matching series automatically.",
        ] = None,
        start_year: Annotated[
            int | None,
            "Optional 4-digit start year (e.g. 2020). "
            "When omitted, BLS returns its default range (last 3 years).",
        ] = None,
        end_year: Annotated[
            int | None,
            "Optional 4-digit end year (e.g. 2024). Must be >= start_year.",
        ] = None,
    ) -> dict[str, Any]:
        """Answer a natural-language question about BLS time-series data.

        Orchestrates the full pipeline in one call:
          1. Discovery  — suggest_series finds the best matching series ID.
          2. Validation — local schema + catalog check (no network call).
          3. Retrieval  — get_series_data fetches live BLS observations.
          4. Response   — structured answer with observations and provenance.

        Skip step 1 by supplying a known series_id directly.

        This tool makes exactly one live network call (step 3). To conserve
        the daily BLS API quota (v1: 25/day, v2: 500/day), prefer batching
        multiple series via get_series_data when you need several series at once.

        Data freshness: BLS publishes monthly updates. Values marked 'P' are
        preliminary estimates subject to revision; 'R' indicates a revised value.
        All values are returned as strings to preserve published precision.

        Returns:
            {
              "question":         str,
              "series_id":        str,
              "series_label":     str,
              "api_version":      "v1"|"v2",
              "observations":     [{"year","period","periodName","value",
                                    "footnotes"}, ...],
              "summary":          str,   # plain-English most-recent value
              "suggestion_used":  dict | null,  # discovery metadata
              "notes":            str
            }

        On error:
            {
              "question": str,
              "error":    str,
              "hint":     str
            }
        """
        suggestion: dict[str, Any] | None = None

        # ------------------------------------------------------------------
        # Step 1 — Discover series ID (unless caller supplied one).
        # ------------------------------------------------------------------
        if series_id:
            resolved_id = series_id.strip().upper()
        else:
            suggestion = _discover_series(question)
            if suggestion is None:
                return {
                    "question": question,
                    "error": (
                        "No BLS series matched your question. "
                        "Try being more specific (e.g. include 'CPI', "
                        "'unemployment', 'payrolls', 'job openings')."
                    ),
                    "hint": (
                        "Use suggest_series or search_series to explore "
                        "available series, then call get_series_data directly."
                    ),
                }
            resolved_id = suggestion["series_id"]

        # ------------------------------------------------------------------
        # Step 2 — Validate locally (no network call).
        # ------------------------------------------------------------------
        valid, issues = _validate_locally(resolved_id)
        if not valid:
            return {
                "question": question,
                "error": f"Series ID '{resolved_id}' failed validation: "
                + "; ".join(issues),
                "hint": (
                    "Use validate_series_id for details, or suggest_series "
                    "to find a valid series ID for your topic."
                ),
            }

        # ------------------------------------------------------------------
        # Step 3 — Fetch live observations.
        # ------------------------------------------------------------------
        observations, fetch_error = await _fetch_observations(
            resolved_id, start_year, end_year
        )
        if fetch_error:
            return {
                "question": question,
                "error": fetch_error,
                "hint": (
                    "Check that BLS_API_KEY is configured for v2 access, "
                    "or reduce the year range for v1 (max 10 years, 25 req/day)."
                ),
            }

        # ------------------------------------------------------------------
        # Step 4 — Shape the response.
        # ------------------------------------------------------------------
        label = _label_for(resolved_id)
        summary = _build_summary(resolved_id, label, observations)

        return {
            "question": question,
            "series_id": resolved_id,
            "series_label": label,
            "api_version": get_bls_api_version(),
            "observations": observations,
            "summary": summary,
            "suggestion_used": suggestion,
            "notes": (
                "Data sourced from BLS Public Data API. "
                "Values are strings to preserve published precision. "
                "Footnote 'P' = preliminary; 'R' = revised."
            ),
        }
