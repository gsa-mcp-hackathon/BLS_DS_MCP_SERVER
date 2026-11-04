"""Tool: lookup_area_code — find BLS area codes by place name."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.catalog import catalog


def register(mcp: FastMCP) -> None:
    """Register the lookup_area_code tool."""

    @mcp.tool(
        name="lookup_area_code",
        annotations={
            "title": "Look Up BLS Area Code",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def lookup_area_code(
        query: Annotated[
            str,
            "Place name or code fragment to search (e.g. 'Chicago', 'AL', '01001').",
        ],
        survey: Annotated[
            str | None,
            "Optional survey filter: 'SM', 'LA', or 'QCEW'."
            " Omit to search all surveys.",
        ] = None,
        limit: Annotated[int, "Maximum results to return (1–50)."] = 20,
    ) -> dict[str, Any]:
        """Search BLS area codes by place name across SM, LA, and QCEW surveys.

        Returns area codes used to build BLS series IDs. Covers metropolitan
        areas (SM), state and county areas (LA), and FIPS-based areas (QCEW).
        Results are sorted: exact code match first, then starts-with, then contains.

        Args:
            query:  Place name or code fragment (e.g. "Chicago", "TX", "17169").
            survey: Restrict to a single survey prefix. Defaults to all three.
            limit:  Max results (1–50).

        Returns:
            {"query": str, "results": [{"code", "name", "survey", "dimension"}],
             "count": int}
        """
        limit = max(1, min(50, limit))
        survey_dims: list[tuple[str, str]] = [
            ("sm", "area"),
            ("la", "area"),
            ("qcew", "area"),
        ]
        if survey:
            key = survey.lower()
            survey_dims = [(s, d) for s, d in survey_dims if s == key]

        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for sv, dim in survey_dims:
            for hit in catalog.search(sv, dim, query, max_results=limit):
                uid = f"{hit['survey']}:{hit['code']}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(hit)
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break

        return {
            "query": query,
            "results": results[:limit],
            "count": len(results[:limit]),
        }
