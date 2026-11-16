"""Tool: suggest_series — suggest curated BLS series IDs for a topic."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_flagship_series import search_flagship
from example_server.bls_series_schema import decode_id


def register(mcp: FastMCP) -> None:
    """Register the suggest_series tool."""

    @mcp.tool(
        name="suggest_series",
        annotations={
            "title": "Suggest BLS Series IDs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def suggest_series(
        topic: Annotated[
            str,
            "Free-text topic or question"
            " (e.g. 'retail trade in Texas', 'national inflation').",
        ],
        limit: Annotated[int, "Maximum suggestions to return (1–15)."] = 5,
    ) -> dict[str, Any]:
        """Suggest curated BLS series IDs relevant to a topic.

        Searches the flagship series table (30+ canonical series across SM,
        CE, LA, JT, and CU surveys) and returns ranked suggestions with a
        plain-language rationale for each.

        Use this tool for discovery when you don't know which BLS survey or
        series covers a given topic.  For precise lookup by area/industry name,
        use search_series instead.

        Returns:
            {"topic": str, "suggestions": [...], "count": int}
            Each suggestion: {"series_id", "survey_name", "description", "rationale",
                              "concept", "measure_type", "unit"}
        """
        limit = max(1, min(15, limit))
        hits = search_flagship(topic, limit=limit)

        suggestions: list[dict[str, Any]] = []
        for entry in hits:
            decoded = decode_id(entry.series_id)
            description = entry.description
            if "error" not in decoded:
                # Use the label from the first meaningful segment if available.
                segs = decoded.get("segments", [])
                labels = [s["label"] for s in segs if s["label"]]
                if labels:
                    description = entry.description  # keep the authored description

            suggestions.append(
                {
                    "series_id": entry.series_id,
                    "survey_name": entry.survey_name,
                    "description": description,
                    "rationale": entry.notes,
                    "concept": entry.concept,
                    "measure_type": entry.measure_type,
                    "unit": entry.unit,
                }
            )

        if not suggestions:
            return {
                "topic": topic,
                "suggestions": [],
                "count": 0,
                "has_measure_type_conflict": False,
                "message": (
                    "No flagship series matched your topic. "
                    "Try search_series for a broader catalog search."
                ),
            }

        # Detect whether the suggestions span multiple measure types — a signal
        # that callers should disambiguate before retrieving data.
        measure_types = {s["measure_type"] for s in suggestions if s.get("measure_type")}
        has_conflict = len(measure_types) > 1

        return {
            "topic": topic,
            "suggestions": suggestions,
            "count": len(suggestions),
            "has_measure_type_conflict": has_conflict,
        }
