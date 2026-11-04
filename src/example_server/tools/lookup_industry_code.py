"""Tool: lookup_industry_code — find BLS industry codes by name or NAICS."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.catalog import catalog


def register(mcp: FastMCP) -> None:
    """Register the lookup_industry_code tool."""

    @mcp.tool(
        name="lookup_industry_code",
        annotations={
            "title": "Look Up BLS Industry Code",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def lookup_industry_code(
        query: Annotated[
            str,
            "Industry name or NAICS code fragment"
            " (e.g. 'healthcare', '622', 'manufacturing').",
        ],
        survey: Annotated[
            str | None,
            "Optional survey filter: 'CE', 'SM', 'JT', or 'QCEW'."
            " Omit to search all surveys.",
        ] = None,
        limit: Annotated[int, "Maximum results to return (1–50)."] = 20,
    ) -> dict[str, Any]:
        """Search BLS industry codes by name or NAICS code across CE, SM, JT, and QCEW.

        Different BLS surveys use different industry taxonomies:
        - CE/SM: 6-digit or 8-digit hierarchical codes
        - JT:    6-digit codes aligned with NAICS
        - QCEW:  NAICS-based codes with county-level detail

        Args:
            query:  Industry name or partial NAICS code (e.g. "healthcare", "622").
            survey: Restrict to one survey prefix. Defaults to all four.
            limit:  Max results (1–50).

        Returns:
            {"query": str, "results": [{"code", "name", "survey"}], "count": int}
        """
        limit = max(1, min(50, limit))
        survey_dims: list[tuple[str, str]] = [
            ("ce", "industry"),
            ("sm", "industry"),
            ("jt", "industry"),
            ("qcew", "industry"),
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
                    results.append(
                        {
                            "code": hit["code"],
                            "name": hit["name"],
                            "survey": hit["survey"],
                        }
                    )
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break

        return {
            "query": query,
            "results": results[:limit],
            "count": len(results[:limit]),
        }
