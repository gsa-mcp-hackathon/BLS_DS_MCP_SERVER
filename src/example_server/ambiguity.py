"""Ambiguity detection and clarification logic for BLS data queries.

This module is the central policy layer.  It is called by
``answer_bls_question`` before any BLS API request is made.

Public API
----------
parse_intent_from_query(query, context=None) -> QueryIntent
filter_candidates(intent, candidates)        -> list[CandidateSeries]
detect_unresolved_dimensions(intent, eligible_candidates) -> list[str]
apply_safe_defaults(intent, candidates)      -> tuple[list[CandidateSeries], list[str]]
generate_clarification(intent, candidates, unresolved) -> str
flagship_to_candidate(entry)                 -> CandidateSeries

Constants
---------
SAFE_DEFAULTS  — per-survey seasonal-adjustment defaults
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from example_server.models import CandidateSeries, QueryIntent

# ---------------------------------------------------------------------------
# Safe seasonal-adjustment defaults by survey
# ---------------------------------------------------------------------------

SAFE_DEFAULTS: dict[str, str] = {
    # survey prefix → "S" (seasonally adjusted) or "U" (not seasonally adjusted)
    "CE": "S",   # CE headline is SA (CES0000000001)
    "LA": "S",   # LA national/state headline is SA
    "LN": "S",   # LN CPS headline series are SA
    "JT": "S",   # JOLTS headline figures are SA
    "PR": "S",   # Productivity headline is SA
    "CU": "U",   # CPI-U NSA is the reference series (CUUR0000SA0)
    "CW": "U",   # CPI-W NSA is the COLA reference
    "SM": "U",   # State/metro data is predominantly NSA
    "MP": "U",   # Multifactor productivity is annual, NSA
    "EI": "U",   # International price — NSA
    "WP": "U",   # PPI commodity — NSA
    "CI": "S",   # ECEC headline is SA
}

# ---------------------------------------------------------------------------
# Keyword tables for intent parsing
# ---------------------------------------------------------------------------

# Words / phrases that signal "rate" measure type
_RATE_SIGNALS = {
    "unemployment rate",
    "participation rate",
    "openings rate",
    "hires rate",
    "quit rate",
    "layoff rate",
    "employment-population ratio",
    "employment population ratio",
    "epop",
    "job openings rate",
}

# Words / phrases that signal "level" measure type
_LEVEL_SIGNALS = {
    "employment level",
    "level of employment",
    "number of employed",
    "number of unemployed",
    "unemployment level",
    "labor force level",
    "number of people",
    "how many people are employed",
    "how many people are unemployed",
    "how many are unemployed",
    "how many unemployed",
    "how many workers",
    "labor force size",
}

# "percent change" / "inflation rate" signals → percent_change
_PCT_CHANGE_SIGNALS = {
    "inflation rate",
    "percent change",
    "percentage change",
    "rate of inflation",
    "rate of change",
    "price change",
    "earnings growth",
    "wage growth",
    "how much did prices rise",
    "how much did prices increase",
}

# Ranking signals
_RANKING_SIGNALS = {
    "which industry",
    "what industry",
    "which sector",
    "most jobs",
    "fewest jobs",
    "added the most",
    "lost the most",
    "grew the fastest",
    "fastest growing",
    "highest rate",
    "lowest rate",
    "largest gain",
    "largest decline",
    "most employment",
    "largest percent",
}

# Stock vs flow ambiguity triggers
_STOCK_FLOW_TRIGGERS = {
    "lost jobs",
    "people lost jobs",
    "job losers",
    "how many lost",
    "workers lost",
    "jobs lost",
}

# Geography extractor — rough phrase patterns
_GEO_PATTERNS = [
    r"\bin ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",       # "in California"
    r"\bfor ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",       # "for Texas"
    r"\b([A-Z][a-z]+)\s+(?:state|metro|area)\b",     # "Washington state"
]

# Map of "stock/flow" concepts that share keywords → need disambiguation
_STOCK_FLOW_CONCEPTS = {
    "unemployed_job_losers",
    "layoffs_and_discharges",
    "layoffs",
    "job_losers",
}

# Concepts that are household (CPS) vs establishment (CE) — need disambiguation
_HOUSEHOLD_CONCEPTS = {
    "civilian_employment",
    "civilian_labor_force",
    "civilian_unemployment",
}
_ESTABLISHMENT_CONCEPTS = {
    "nonfarm_payrolls",
    "private_payrolls",
    "goods_producing_payrolls",
    "service_payrolls",
}


def _query_lower(query: str) -> str:
    return query.lower().strip()


def parse_intent_from_query(
    query: str,
    context: dict | None = None,
) -> QueryIntent:
    """Extract structured intent from a free-text BLS data query.

    Uses deterministic keyword matching — no model call.  Returns a
    ``QueryIntent`` whose ``None`` fields represent dimensions that could not
    be resolved from the query text alone.

    Args:
        query:   The user's natural-language question.
        context: Optional dict from a prior conversation turn.  Keys:
                 ``series_id``, ``concept``, ``measure_type``, ``geography``,
                 ``seasonal_adjustment``, ``dataset``.
    """
    ql = _query_lower(query)
    intent = QueryIntent(original_query=query, normalized_query=ql)

    # ── Measure type ──────────────────────────────────────────────────────
    if any(sig in ql for sig in _PCT_CHANGE_SIGNALS):
        intent.requested_measure_type = "percent_change"
    elif any(sig in ql for sig in _RATE_SIGNALS):
        intent.requested_measure_type = "rate"
    elif any(sig in ql for sig in _LEVEL_SIGNALS):
        intent.requested_measure_type = "level"
    elif "index" in ql:
        intent.requested_measure_type = "index"

    # ── Concept detection — narrow to a specific concept when phrasing is explicit ──
    # These exact-phrase matches allow the eligibility filter to remove
    # irrelevant same-measure-type candidates from search_flagship results.
    _CONCEPT_PHRASES: list[tuple[str, str]] = [
        ("employment-population ratio", "employment_population_ratio"),
        ("employment population ratio", "employment_population_ratio"),
        ("epop", "employment_population_ratio"),
        ("labor force participation rate", "labor_force_participation_rate"),
        ("participation rate", "labor_force_participation_rate"),
        ("lfpr", "labor_force_participation_rate"),
        ("unemployment rate", "unemployment_rate"),
        ("how many people are unemployed", "civilian_unemployment"),
        ("how many are unemployed", "civilian_unemployment"),
        ("how many unemployed", "civilian_unemployment"),
        ("number of unemployed", "civilian_unemployment"),
        ("nonfarm payroll", "nonfarm_payrolls"),
        ("payroll employment", "nonfarm_payrolls"),
        ("core cpi", "cpi_core"),
        ("core inflation", "cpi_core"),
        ("cpi-u all items", "cpi_all_items"),
        ("job openings rate", "job_openings_rate"),
        ("job openings", "job_openings"),
        ("layoffs and discharges", "layoffs_and_discharges"),
        ("average hourly earnings", "average_hourly_earnings"),
        ("hourly earnings", "average_hourly_earnings"),
    ]
    for phrase, concept_name in _CONCEPT_PHRASES:
        if phrase in ql:
            intent.concept = concept_name
            break

    # ── Calculation type ──────────────────────────────────────────────────
    if any(sig in ql for sig in _RANKING_SIGNALS):
        intent.calculation_type = "ranking"

    # ── Seasonal adjustment ───────────────────────────────────────────────
    if "not seasonally adjusted" in ql or "unadjusted" in ql or " nsa" in ql:
        intent.seasonal_adjustment = "U"
    elif "seasonally adjusted" in ql or " sa " in ql or ql.endswith(" sa"):
        intent.seasonal_adjustment = "S"

    # ── Geography ─────────────────────────────────────────────────────────
    for pat in _GEO_PATTERNS:
        m = re.search(pat, query)
        if m:
            intent.geography_value = m.group(1)
            intent.geography_type = "state"  # conservative default
            break

    # ── Stock vs. flow ambiguity ──────────────────────────────────────────
    if any(sig in ql for sig in _STOCK_FLOW_TRIGGERS):
        intent.unresolved_dimensions = (
            list(intent.unresolved_dimensions) + ["stock_flow"]
        )

    # ── Context inheritance ───────────────────────────────────────────────
    if context:
        inherited = []
        if intent.dataset is None and context.get("dataset"):
            intent.dataset = context["dataset"]
            inherited.append("dataset")
        if intent.requested_measure_type is None and context.get("measure_type"):
            intent.requested_measure_type = context["measure_type"]
            inherited.append("measure_type")
        if intent.geography_value is None and context.get("geography"):
            intent.geography_value = context["geography"]
            inherited.append("geography")
        if intent.seasonal_adjustment is None and context.get("seasonal_adjustment"):
            intent.seasonal_adjustment = context["seasonal_adjustment"]
            inherited.append("seasonal_adjustment")
        intent.inherited_context = inherited

    return intent


# ---------------------------------------------------------------------------
# Candidate conversion helper
# ---------------------------------------------------------------------------


def flagship_to_candidate(entry: object) -> CandidateSeries:
    """Convert a ``FlagshipEntry`` to a ``CandidateSeries``.

    ``FlagshipEntry`` carries ``concept``, ``measure_type``, and ``unit``
    but not seasonal-adjustment or frequency directly.  We derive those from
    the series ID prefix and the ``notes`` text as a best-effort heuristic;
    the ``SAFE_DEFAULTS`` table is authoritative for defaults.
    """
    # Determine seasonal adjustment from the series ID character after the
    # 2-char prefix (position 2): "S" = seasonally adjusted, "U" otherwise.
    series_id: str = entry.series_id  # type: ignore[attr-defined]
    sa_char = series_id[2:3].upper() if len(series_id) > 2 else "U"
    # Normalise: BLS uses S/U across most surveys; LN uses S (LNS) / U (LNU)
    if sa_char not in ("S", "U"):
        sa_char = "U"

    # Frequency: most BLS flagship series are monthly; PR/MP/CI are quarterly.
    survey: str = entry.survey  # type: ignore[attr-defined]
    freq = "quarterly" if survey in ("PR", "MP", "CI") else "monthly"

    return CandidateSeries(
        series_id=series_id,
        description=entry.description,  # type: ignore[attr-defined]
        dataset=survey,
        concept=entry.concept,  # type: ignore[attr-defined]
        measure_type=entry.measure_type,  # type: ignore[attr-defined]
        unit=entry.unit,  # type: ignore[attr-defined]
        geography=None,
        seasonal_adjustment=sa_char,
        frequency=freq,
        available_date_range=None,
        match_score=0,
    )


# ---------------------------------------------------------------------------
# Eligibility filter
# ---------------------------------------------------------------------------


def filter_candidates(
    intent: QueryIntent,
    candidates: list[CandidateSeries],
) -> list[CandidateSeries]:
    """Return only candidates compatible with the stated intent.

    Rejection rules (deterministic):
    - If ``intent.requested_measure_type`` is set, reject candidates whose
      ``measure_type`` differs, **unless** the intent is ``percent_change``
      and the candidate is ``index`` (index is the source for percent change —
      flag it as needing a calculation note instead of rejecting).
    - If ``intent.seasonal_adjustment`` is explicitly set, reject candidates
      with a different ``seasonal_adjustment``.

    Candidates are marked ineligible (``eligible=False``) with a
    ``rejection_reason``; they are still returned in the list so callers can
    inspect why they were rejected.  ``filter_candidates`` returns only the
    *eligible* subset.
    """
    result: list[CandidateSeries] = []
    for c in candidates:
        reasons: list[str] = []

        # Concept conflict — when the query explicitly names a concept, reject
        # candidates with a different concept.
        if intent.concept is not None and c.concept != intent.concept:
            reasons.append(
                f"concept conflicts: requested {intent.concept}, got {c.concept}"
            )

        # Measure-type conflict
        if intent.requested_measure_type is not None:
            req = intent.requested_measure_type
            got = c.measure_type
            # percent_change is *derived* from index/level — do not reject index
            # candidates when percent_change is requested; flag instead.
            if req != got and not (
                req == "percent_change" and got in ("index", "level")
            ):
                reasons.append(
                    f"measure_type conflicts: requested {req}, got {got}"
                )

        # Seasonal-adjustment conflict (only when explicitly stated in query)
        if intent.seasonal_adjustment is not None:
            if c.seasonal_adjustment != intent.seasonal_adjustment:
                reasons.append(
                    f"seasonal_adjustment conflicts: "
                    f"requested {intent.seasonal_adjustment}, "
                    f"got {c.seasonal_adjustment}"
                )

        if reasons:
            c.eligible = False
            c.rejection_reason = "; ".join(reasons)
            c.mismatch_reasons = reasons
        else:
            result.append(c)

    return result


# ---------------------------------------------------------------------------
# Unresolved-dimension detection
# ---------------------------------------------------------------------------


def detect_unresolved_dimensions(
    intent: QueryIntent,
    eligible_candidates: list[CandidateSeries],
) -> list[str]:
    """Return the names of material dimensions that remain unresolved.

    A dimension is unresolved when eligible candidates still differ along it
    in a way that would change the answer.  SA vs. NSA on the *same* concept
    is handled by ``apply_safe_defaults`` and is therefore NOT flagged here.

    Returns an empty list when the candidates can be safely auto-resolved.
    """
    unresolved: list[str] = list(intent.unresolved_dimensions)

    if not eligible_candidates:
        return unresolved

    # Concept conflict — candidates measure different economic things
    concepts = {c.concept for c in eligible_candidates}
    if len(concepts) > 1:
        # Exception: SA vs NSA pairs share the same concept — not a conflict
        # Check whether the concept variance is *only* due to seasonal adjustment
        sa_groups: dict[str, set[str]] = {}
        for c in eligible_candidates:
            sa_groups.setdefault(c.concept, set()).add(c.seasonal_adjustment)
        # True conflict: more than one distinct concept key
        if len(sa_groups) > 1:
            if "concept" not in unresolved:
                unresolved.append("concept")

    # Measure-type conflict — candidates have different mathematical forms
    measure_types = {c.measure_type for c in eligible_candidates}
    if len(measure_types) > 1:
        # SA vs NSA pairs have the same measure_type — this is a real type conflict
        if "measure_type" not in unresolved:
            unresolved.append("measure_type")

    # Household vs. establishment conflict
    concepts_set = {c.concept for c in eligible_candidates}
    if concepts_set & _HOUSEHOLD_CONCEPTS and concepts_set & _ESTABLISHMENT_CONCEPTS:
        if "household_vs_establishment" not in unresolved:
            unresolved.append("household_vs_establishment")

    # Ranking requires a comparison period
    if intent.calculation_type == "ranking" and intent.comparison_period is None:
        if "comparison_period" not in unresolved:
            unresolved.append("comparison_period")

    return unresolved


# ---------------------------------------------------------------------------
# Safe-default application
# ---------------------------------------------------------------------------


def apply_safe_defaults(
    intent: QueryIntent,
    candidates: list[CandidateSeries],
) -> tuple[list[CandidateSeries], list[str]]:
    """Narrow candidates using per-survey seasonal-adjustment defaults.

    Called when ``detect_unresolved_dimensions`` returns no concept or
    measure-type conflict — only SA vs. NSA variants remain.  Picks the
    variant that matches the survey default, and records a disclosure string.

    Returns:
        (resolved_candidates, defaults_applied_descriptions)
    """
    if not candidates:
        return [], []

    # If the intent has an explicit SA setting, honour it (no default needed).
    if intent.seasonal_adjustment is not None:
        target_sa = intent.seasonal_adjustment
        filtered = [c for c in candidates if c.seasonal_adjustment == target_sa]
        return filtered if filtered else candidates, []

    # Determine the survey — prefer intent.dataset, else infer from candidates.
    survey = intent.dataset
    if survey is None and candidates:
        survey = candidates[0].dataset

    default_sa = SAFE_DEFAULTS.get(survey or "", "S")
    preferred = [c for c in candidates if c.seasonal_adjustment == default_sa]
    if not preferred:
        # Default SA not available — return all candidates unchanged.
        return candidates, []

    sa_label = "seasonally adjusted" if default_sa == "S" else "not seasonally adjusted"
    disclosure = (
        f"Seasonal adjustment defaulted to {sa_label} "
        f"(standard for {survey} survey)."
    )
    return preferred, [disclosure]


# ---------------------------------------------------------------------------
# Clarification question generation
# ---------------------------------------------------------------------------

# Canned clarification templates keyed by unresolved dimension name.
# The generator picks the highest-priority unresolved dimension and uses its
# template, filling in candidate descriptions where possible.

def generate_clarification(
    intent: QueryIntent,
    eligible_candidates: list[CandidateSeries],
    unresolved: list[str],
) -> str:
    """Return a concise, user-friendly clarification question.

    Addresses the most material unresolved dimension.  Uses plain language —
    avoids BLS series IDs, survey codes, and technical jargon where possible.
    """
    if not unresolved:
        return ""

    ql = intent.normalized_query

    # Priority order for clarification
    priority = [
        "stock_flow",
        "household_vs_establishment",
        "measure_type",
        "concept",
        "comparison_period",
        "geography",
    ]

    for dim in priority:
        if dim not in unresolved:
            continue

        if dim == "stock_flow":
            return (
                "By 'people who lost jobs,' do you mean:\n"
                "(a) unemployed people classified as job losers"
                " (a count of people currently"
                " unemployed because they lost their previous job),\n"
                "(b) layoffs and discharges recorded during the month"
                " (from the JOLTS survey), or\n"
                "(c) the decline in total payroll employment?"
            )

        if dim == "household_vs_establishment":
            return (
                "Do you want payroll employment"
                " (the number of jobs on employer payrolls,"
                " from the Current Employment Statistics survey)"
                " or household employment"
                " (the number of employed people,"
                " from the Current Population Survey)?"
            )

        if dim == "measure_type":
            # Check whether this is a CPI/inflation context
            is_cpi = any(
                c.concept.startswith("cpi") for c in eligible_candidates
            ) or "inflation" in ql or "cpi" in ql or "price" in ql

            if is_cpi:
                return (
                    "By 'inflation,' do you want:\n"
                    "(a) the CPI index level (e.g. 314.2 on a 1982–84=100 scale),\n"
                    "(b) the one-month percent change in the CPI, or\n"
                    "(c) the 12-month percent change in the CPI (year-over-year)?"
                )

            # Build options from candidates
            opts = _describe_measure_options(eligible_candidates)
            if opts:
                return "Which measure do you want?\n" + "\n".join(
                    f"({chr(97+i)}) {o}" for i, o in enumerate(opts)
                )
            return (
                "Do you want an employment level (number of people or jobs) or a rate"
                " (percent of the labor force or population)?"
            )

        if dim == "concept":
            opts = _describe_concept_options(eligible_candidates)
            if opts:
                return "Which of these did you mean?\n" + "\n".join(
                    f"({chr(97+i)}) {o}" for i, o in enumerate(opts)
                )
            return "Could you clarify which economic concept you are looking for?"

        if dim == "comparison_period":
            return (
                "What time period should I use for the comparison?\n"
                "(a) the latest monthly change (this month vs. last month),\n"
                "(b) the change over the past 12 months (year over year), or\n"
                "(c) another period (please specify)?"
            )

        if dim == "geography":
            return (
                "Several geographic areas match your query. "
                "Could you be more specific — for example, state the full state name,"
                " metropolitan area, or whether you mean the national figure?"
            )

    # Fallback
    dims_str = ", ".join(unresolved)
    return (
        f"Your question is ambiguous in the following dimensions: {dims_str}. "
        "Could you provide more detail?"
    )


def _describe_measure_options(candidates: list[CandidateSeries]) -> list[str]:
    """Build human-readable measure-type option strings from candidates."""
    seen: set[str] = set()
    opts: list[str] = []
    for c in candidates:
        key = (c.measure_type, c.concept)
        if key in seen:
            continue
        seen.add(key)
        concept_label = c.concept.replace("_", " ")
        if c.measure_type == "level":
            opts.append(f"{concept_label} (a count in {c.unit})")
        elif c.measure_type == "rate":
            opts.append(f"{concept_label} (a rate in {c.unit})")
        elif c.measure_type == "index":
            opts.append(f"{concept_label} (an index, {c.unit})")
        elif c.measure_type == "percent_change":
            opts.append(f"{concept_label} (percent change)")
        else:
            opts.append(concept_label)
    return opts[:4]


def _describe_concept_options(candidates: list[CandidateSeries]) -> list[str]:
    """Build human-readable concept option strings from candidates."""
    seen: set[str] = set()
    opts: list[str] = []
    for c in candidates:
        if c.concept in seen:
            continue
        seen.add(c.concept)
        opts.append(f"{c.description} ({c.unit})")
    return opts[:4]
