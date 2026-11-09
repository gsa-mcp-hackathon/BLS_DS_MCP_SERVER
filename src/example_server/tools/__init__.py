"""Tools submodule — one tool per file.

Each tool module exposes a `register(mcp)` function that attaches its
`@mcp.tool`-decorated function to the server. This file aggregates them
into a single `register_tools(mcp)` that `app.py` calls.
"""

from __future__ import annotations

from example_server.tools import (
    answer_bls_question,
    build_series_id,
    decode_series_id,
    get_series_data,
    get_series_metadata,
    lookup_area_code,
    lookup_industry_code,
    search_series,
    suggest_series,
    validate_series_id,
)


def register_tools(mcp) -> None:
    """Register all tools with the MCP server."""
    # BLS lookup helpers
    lookup_area_code.register(mcp)
    lookup_industry_code.register(mcp)

    # Series ID tools
    build_series_id.register(mcp)
    decode_series_id.register(mcp)
    validate_series_id.register(mcp)

    # Search and discovery
    search_series.register(mcp)
    suggest_series.register(mcp)

    # Metadata and data retrieval
    get_series_metadata.register(mcp)
    get_series_data.register(mcp)

    # Orchestrator — natural-language question answering
    answer_bls_question.register(mcp)


__all__ = ["register_tools"]
