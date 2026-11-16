"""Tool: answer_bls_question — answer a natural-language BLS data question.

Orchestrates the discovery → ambiguity-check → validation → retrieval pipeline:

  1. Parse structured intent from the question (local, no network).
  2. Discover candidate flagship series via keyword search (local, no network).
  3. Filter candidates for eligibility (measure-type, seasonal-adjustment).
  4. Detect unresolved material dimensions.
     • If unresolved: return a clarification question — do NOT call the BLS API.
     • If SA ambiguity only: apply the per-survey safe default and disclose it.
  5. Validate the selected series ID locally (no network).
  6. Fetch live observations from the BLS Public Data API (one network call).
  7. Return structured response with observations, summary, and provenance.

The caller never needs to know BLS Series IDs, survey codes, or v1/v2 limits.

If the caller already knows the series ID, pass it via ``series_id`` to skip
steps 1–4 and go straight to validation + retrieval.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.ambiguity import (
    apply_safe_defaults,
    detect_unresolved_dimensions,
    filter_candidates,
    flagship_to_candidate,
    generate_clarification,
    parse_intent_from_query,
)
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

logger = logging.getLogger(__name__)

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
        context: Annotated[
            dict | None,
            "Optional conversation context from a prior turn. "
            "Accepted keys: 'series_id', 'concept', 'measure_type', "
            "'dataset', 'geography', 'seasonal_adjustment'. "
            "Dimensions present here are inherited unless the current "
            "question overrides them.",
        ] = None,
    ) -> dict[str, Any]:
        """Answer a natural-language question about BLS time-series data.

        Orchestrates the full pipeline in one call:
          1. Intent parsing  — structured extraction of measure type, geography,
             seasonal adjustment, and other dimensions from the question text.
          2. Discovery       — flagship series table search for candidate series.
          3. Eligibility     — filter candidates for measure-type and SA conflicts.
          4. Ambiguity gate  — if material dimensions remain unresolved, returns
             a clarification question INSTEAD of calling the BLS API.
          5. Safe defaults   — when only SA variants differ, apply the per-survey
             default and disclose it in the response.
          6. Validation      — local schema + prefix check (no network call).
          7. Retrieval       — fetch live BLS observations (one network call).
          8. Response        — structured answer with observations and provenance.

        Skip steps 1–5 by supplying a known ``series_id`` directly.

        Returns on clarification needed:
            {
              "question":                str,
              "clarification_required":  True,
              "clarification_question":  str,
              "clarification_options":   [str, ...],
              "hint":                    str
            }

        Returns on success:
            {
              "question":         str,
              "series_id":        str,
              "series_label":     str,
              "api_version":      "v1"|"v2",
              "observations":     [{"year","period","periodName","value",
                                    "footnotes"}, ...],
              "summary":          str,
              "suggestion_used":  dict | null,
              "defaults_applied": [str, ...],
              "notes":            str
            }

        Returns on error:
            {"question": str, "error": str, "hint": str}

        Data freshness: BLS publishes monthly updates. Values marked 'P' are
        preliminary estimates subject to revision; 'R' indicates a revised value.
        All values are returned as strings to preserve published precision.
        """
        suggestion: dict[str, Any] | None = None
        defaults_applied: list[str] = []

        # ------------------------------------------------------------------
        # Fast path: caller supplied a known series ID — skip discovery.
        # ------------------------------------------------------------------
        if series_id:
            resolved_id = series_id.strip().upper()

            # --- Log ---
            logger.debug(
                "answer_bls_question: series_id override=%s bls_api_called=pending",
                resolved_id,
            )

            valid, issues = _validate_locally(resolved_id)
            if not valid:
                logger.debug(
                    "answer_bls_question: validation_failed series_id=%s issues=%s",
                    resolved_id,
                    issues,
                )
                return {
                    "question": question,
                    "error": f"Series ID '{resolved_id}' failed validation: "
                    + "; ".join(issues),
                    "hint": (
                        "Use validate_series_id for details, or suggest_series "
                        "to find a valid series ID for your topic."
                    ),
                }

            observations, fetch_error = await _fetch_observations(
                resolved_id, start_year, end_year
            )
            logger.debug(
                "answer_bls_question: bls_api_called=True series_id=%s error=%s",
                resolved_id,
                fetch_error,
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

            label = _label_for(resolved_id)
            summary = _build_summary(resolved_id, label, observations)
            return {
                "question": question,
                "series_id": resolved_id,
                "series_label": label,
                "api_version": get_bls_api_version(),
                "observations": observations,
                "summary": summary,
                "suggestion_used": None,
                "defaults_applied": [],
                "notes": (
                    "Data sourced from BLS Public Data API. "
                    "Values are strings to preserve published precision. "
                    "Footnote 'P' = preliminary; 'R' = revised."
                ),
            }

        # ------------------------------------------------------------------
        # Step 1 — Parse structured intent from the question.
        # ------------------------------------------------------------------
        intent = parse_intent_from_query(question, context=context)

        # Early gate: some ambiguities (stock/flow) are detected purely from
        # the query text before discovery.  Clarify immediately so we don't
        # send the user down an unrelated candidate path.
        if intent.unresolved_dimensions:
            clarification_q = generate_clarification(
                intent, [], intent.unresolved_dimensions
            )
            logger.debug(
                "answer_bls_question: early_clarification unresolved=%s query=%r",
                intent.unresolved_dimensions,
                question,
            )
            return {
                "question": question,
                "clarification_required": True,
                "clarification_question": clarification_q,
                "clarification_options": [],
                "hint": (
                    "Please answer the clarification question, then re-call "
                    "answer_bls_question with additional context."
                ),
            }

        # ------------------------------------------------------------------
        # Step 2 — Discover candidate flagship series.
        # ------------------------------------------------------------------
        raw_hits = search_flagship(question, limit=10)
        if not raw_hits:
            logger.debug(
                "answer_bls_question: no_flagship_match query=%r", question
            )
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

        candidates = [flagship_to_candidate(h) for h in raw_hits]
        # Attach word-count scores from search_flagship ordering (index = rank)
        for rank, c in enumerate(candidates):
            c.match_score = len(raw_hits) - rank

        intent.candidate_series = [c.series_id for c in candidates]

        # ------------------------------------------------------------------
        # Step 3 — Eligibility filter.
        # ------------------------------------------------------------------
        eligible = filter_candidates(intent, candidates)

        logger.debug(
            "answer_bls_question: candidates=%d eligible=%d query=%r",
            len(candidates),
            len(eligible),
            question,
        )

        if not eligible:
            # All candidates were filtered out — no matching series.
            rejected_reasons = [
                f"{c.series_id}: {c.rejection_reason}"
                for c in candidates
                if not c.eligible
            ]
            logger.debug(
                "answer_bls_question: all_candidates_rejected reasons=%s",
                rejected_reasons,
            )
            return {
                "question": question,
                "error": (
                    "No BLS series matched the requested measure type or "
                    "seasonal-adjustment requirement. "
                    + " | ".join(rejected_reasons[:3])
                ),
                "hint": (
                    "Use suggest_series or search_series to explore available series."
                ),
            }

        # ------------------------------------------------------------------
        # Step 4 — Detect unresolved dimensions.
        # ------------------------------------------------------------------
        unresolved = detect_unresolved_dimensions(intent, eligible)

        if unresolved:
            clarification_q = generate_clarification(intent, eligible, unresolved)
            logger.debug(
                "answer_bls_question: clarification_required=True "
                "unresolved=%s query=%r",
                unresolved,
                question,
            )
            return {
                "question": question,
                "clarification_required": True,
                "clarification_question": clarification_q,
                "clarification_options": [],   # embedded in the question text
                "hint": (
                    "Please answer the clarification question, then re-call "
                    "answer_bls_question with the additional context in the "
                    "'context' parameter or by rephrasing the question."
                ),
            }

        # ------------------------------------------------------------------
        # Step 5 — Apply safe defaults (SA vs. NSA on the same concept).
        # ------------------------------------------------------------------
        eligible, applied = apply_safe_defaults(intent, eligible)
        defaults_applied.extend(applied)

        # Pick the highest-scoring eligible candidate.
        best_candidate = max(eligible, key=lambda c: c.match_score)
        resolved_id = best_candidate.series_id

        suggestion = {
            "series_id": resolved_id,
            "survey_name": best_candidate.dataset,
            "description": best_candidate.description,
            "rationale": f"concept={best_candidate.concept}, "
                         f"measure_type={best_candidate.measure_type}, "
                         f"unit={best_candidate.unit}",
        }

        logger.debug(
            "answer_bls_question: selected series_id=%s concept=%s "
            "measure_type=%s defaults_applied=%s",
            resolved_id,
            best_candidate.concept,
            best_candidate.measure_type,
            defaults_applied,
        )

        # ------------------------------------------------------------------
        # Step 6 — Validate locally (no network call).
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
        # Step 7 — Fetch live observations.
        # ------------------------------------------------------------------
        observations, fetch_error = await _fetch_observations(
            resolved_id, start_year, end_year
        )
        logger.debug(
            "answer_bls_question: bls_api_called=True series_id=%s error=%s",
            resolved_id,
            fetch_error,
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
        # Step 8 — Shape the response.
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
            "defaults_applied": defaults_applied,
            "notes": (
                "Data sourced from BLS Public Data API. "
                "Values are strings to preserve published precision. "
                "Footnote 'P' = preliminary; 'R' = revised."
            ),
        }
