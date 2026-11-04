"""Tool: search_series — find BLS series IDs matching free-text criteria."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_series_schema import SCHEMAS, build_id, decode_id
from example_server.catalog import catalog
from example_server.utils import paginate

# ---------------------------------------------------------------------------
# Keyword tables — map query words to dimension values.
# ---------------------------------------------------------------------------

# Seasonal-adjustment keywords
_SEASONAL_HINTS: dict[str, str] = {
    "seasonally adjusted": "S",
    "seasonal": "S",
    " sa ": "S",
    "not seasonally": "U",
    "unadjusted": "U",
    "nsa": "U",
}

# SM/CE data-type hints
_SM_DATATYPE_HINTS: dict[str, str] = {
    "employment": "01",
    "employees": "01",
    "payroll": "01",
    "jobs": "01",
    "weekly hours": "02",
    "hours": "02",
    "earnings": "03",
    "wages": "03",
}

# LA measure hints
_LA_MEASURE_HINTS: dict[str, str] = {
    "unemployment rate": "03",
    "unemployment": "03",
    "rate": "03",
    "unemployed": "04",
    "employed": "05",
    "labor force": "06",
}

# JT data-element hints
_JT_DE_HINTS: dict[str, str] = {
    "job openings": "JO",
    "openings": "JO",
    "hires": "HI",
    "hiring": "HI",
    "quits": "QU",
    "layoffs": "LD",
    "separations": "OS",
}

# CU item hints
_CU_ITEM_HINTS: dict[str, str] = {
    "all items": "SA0",
    "cpi": "SA0",
    "food": "SAF1",
    "energy": "SA0E",
    "core cpi": "SA0L1E",
    "housing": "SAH",
    "transportation": "SAT",
    "medical": "SAM",
}

# Survey hints — map question words to survey prefixes
_SURVEY_HINTS: dict[str, str] = {
    "cpi": "CU",
    "consumer price": "CU",
    "inflation": "CU",
    "price index": "CU",
    "job openings": "JT",
    "jolts": "JT",
    "hires": "JT",
    "quits": "JT",
    "unemployment": "LA",
    "unemployment rate": "LA",
    "laus": "LA",
    "payroll": "CE",
    "nonfarm": "CE",
    "metro employment": "SM",
    "state employment": "SM",
}


def _match_first(text: str, hints: dict[str, str]) -> str:
    """Return the value for the first key found in text (case-insensitive)."""
    tl = text.lower()
    for kw, val in hints.items():
        if kw in tl:
            return val
    return ""


def _detect_survey(query: str, explicit_survey: str | None) -> list[str]:
    """Return the list of survey prefixes to search."""
    if explicit_survey:
        return [explicit_survey.upper()]
    detected = _match_first(query, _SURVEY_HINTS)
    return [detected] if detected else list(SCHEMAS.keys())


def register(mcp: FastMCP) -> None:
    """Register the search_series tool."""

    @mcp.tool(
        name="search_series",
        annotations={
            "title": "Search BLS Series IDs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def search_series(
        query: Annotated[
            str,
            "Free-text description of the series"
            " (e.g. 'unemployment rate Chicago 2023').",
        ],
        survey: Annotated[
            str | None,
            "Optional survey filter: 'SM', 'CE', 'LA', 'JT', or 'CU'.",
        ] = None,
        limit: Annotated[int, "Maximum results to return (1–25)."] = 10,
    ) -> dict[str, Any]:
        """Search for BLS series IDs matching a free-text description.

        Parses the query for area, industry, measure, and seasonality hints,
        looks up matching codes in the local catalog, assembles candidate series
        IDs, and ranks them by how many query dimensions matched.

        This is a local-only tool — no network call is made.

        Returns:
            {"query": str, "results": [...], "count": int}
            or {"results": [], "suggestion": "..."} when no matches found.
        """
        limit = max(1, min(25, limit))
        surveys_to_try = _detect_survey(query, survey)

        seasonal = _match_first(query, _SEASONAL_HINTS) or "U"

        results: list[dict[str, Any]] = []

        for sv in surveys_to_try:
            if sv == "SM":
                results.extend(_search_sm(query, seasonal, limit))
            elif sv == "CE":
                results.extend(_search_ce(query, seasonal, limit))
            elif sv == "LA":
                results.extend(_search_la(query, seasonal, limit))
            elif sv == "JT":
                results.extend(_search_jt(query, seasonal, limit))
            elif sv == "CU":
                results.extend(_search_cu(query, seasonal, limit))

        # Deduplicate by series_id
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for r in sorted(results, key=lambda x: x.get("match_score", 0), reverse=True):
            if r["series_id"] not in seen:
                seen.add(r["series_id"])
                unique.append(r)
            if len(unique) >= limit:
                break

        if not unique:
            return {
                "query": query,
                "results": [],
                "count": 0,
                "suggestion": (
                    "No series found. Try lookup_area_code or lookup_industry_code "
                    "to find exact codes, then use build_series_id."
                ),
            }

        page = paginate(unique, limit, 0)
        return {"query": query, "results": page["items"], "count": page["total"]}


# ---------------------------------------------------------------------------
# Per-survey candidate builders
# ---------------------------------------------------------------------------


def _make_result(series_id: str, score: int) -> dict[str, Any] | None:
    decoded = decode_id(series_id)
    if "error" in decoded:
        return None
    label_parts = [
        s["label"] or s["value"]
        for s in decoded.get("segments", [])
        if s["label"] or s["value"]
    ]
    label = f"{decoded['survey']} — " + ", ".join(label_parts[:3])
    return {
        "series_id": series_id,
        "label": label,
        "survey": decoded["survey"],
        "match_score": score,
    }


def _area_tokens(query: str) -> list[str]:
    """Return candidate location substrings from a query (words and 2-word phrases)."""
    words = query.split()
    tokens: list[str] = []
    # Skip common non-place words
    stopwords = {
        "employment",
        "payrolls",
        "jobs",
        "earnings",
        "wages",
        "hours",
        "rate",
        "unemployment",
        "cpi",
        "inflation",
        "seasonally",
        "adjusted",
        "nonfarm",
        "total",
        "national",
        "metro",
        "state",
        "county",
        "data",
        "statistics",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
    }
    kept = [w for w in words if w.lower() not in stopwords]
    tokens.extend(kept)
    # 2-word phrases
    for i in range(len(kept) - 1):
        tokens.append(f"{kept[i]} {kept[i + 1]}")
    return tokens


def _search_sm(query: str, seasonal: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    tokens = _area_tokens(query)
    area_hits: list[dict[str, Any]] = []
    state_hits: list[dict[str, Any]] = []
    for tok in tokens:
        area_hits.extend(catalog.search("sm", "area", tok, max_results=3))
        state_hits.extend(catalog.search("sm", "state", tok, max_results=2))
    # Deduplicate by code
    seen_a: set[str] = set()
    area_hits = [
        h for h in area_hits if not (h["code"] in seen_a or seen_a.add(h["code"]))
    ]  # type: ignore[func-returns-value]
    seen_s: set[str] = set()
    state_hits = [
        h for h in state_hits if not (h["code"] in seen_s or seen_s.add(h["code"]))
    ]  # type: ignore[func-returns-value]
    dtype = _match_first(query, _SM_DATATYPE_HINTS) or "01"
    industry = "00000000"  # default total nonfarm

    locations = [(h["code"], "area") for h in area_hits] + [
        (h["code"], "state") for h in state_hits
    ]
    if not locations:
        return results

    for code, kind in locations[:limit]:
        if kind == "area":
            state = "00"
            area = code.zfill(5)
        else:
            state = code.zfill(2)
            area = "00000"
        sid = build_id(
            "SM",
            seasonal=seasonal,
            state_code=state,
            area_code=area,
            supersector_code="00",
            industry_code=industry,
            data_type_code=dtype,
        )
        if isinstance(sid, str):
            score = 2 if kind == "area" else 1
            r = _make_result(sid, score)
            if r:
                results.append(r)
    return results


def _search_ce(query: str, seasonal: str, limit: int) -> list[dict[str, Any]]:
    dtype = _match_first(query, _SM_DATATYPE_HINTS) or "01"
    # Total nonfarm national CE series
    sid = build_id(
        "CE",
        seasonal=seasonal,
        supersector_code="00",
        industry_code="000000",
        data_type_code=dtype,
    )
    if isinstance(sid, dict):
        return []
    r = _make_result(sid, 1)
    return [r] if r else []


def _search_la(query: str, seasonal: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    measure = _match_first(query, _LA_MEASURE_HINTS) or "03"
    tokens = _area_tokens(query)
    area_hits: list[dict[str, Any]] = []
    seen_la: set[str] = set()
    for tok in tokens:
        for h in catalog.search("la", "area", tok, max_results=limit):
            if h["code"] not in seen_la:
                seen_la.add(h["code"])
                area_hits.append(h)
    for hit in area_hits[:limit]:
        area_code = hit["code"]  # already 15 chars
        sid = build_id(
            "LA",
            seasonal=seasonal,
            area_code=area_code,
            measure_code=measure,
        )
        if isinstance(sid, str):
            score = 3 if "unemployment rate" in query.lower() else 2
            r = _make_result(sid, score)
            if r:
                results.append(r)
    return results


def _search_jt(query: str, seasonal: str, limit: int) -> list[dict[str, Any]]:
    de = _match_first(query, _JT_DE_HINTS) or "JO"
    sid = build_id(
        "JT",
        seasonal=seasonal,
        state_code="00",
        industry_code="000000",
        sizeclass_code="00",
        dataelement_code=de,
        ratelevel_code="L",
    )
    if isinstance(sid, dict):
        return []
    r = _make_result(sid, 2)
    return [r] if r else []


def _search_cu(query: str, seasonal: str, limit: int) -> list[dict[str, Any]]:
    item = _match_first(query, _CU_ITEM_HINTS) or "SA0"
    area = "0000"  # U.S. city average
    sid = build_id(
        "CU",
        seasonal=seasonal,
        periodicity="R",
        area_code=area,
        item_code=item,
    )
    if isinstance(sid, dict):
        return []
    r = _make_result(sid, 2)
    return [r] if r else []
