"""Tool: decode_series_id — break an opaque BLS series ID into labelled segments."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_series_schema import decode_id


def register(mcp: FastMCP) -> None:
    """Register the decode_series_id tool."""

    @mcp.tool(
        name="decode_series_id",
        annotations={
            "title": "Decode BLS Series ID",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def decode_series_id(
        series_id: Annotated[
            str,
            "The BLS series ID to decode (e.g. 'CUUR0000SA0', 'SMU17169800500000001').",
        ],
    ) -> dict[str, Any]:
        """Decode a BLS series ID into its named, human-readable segment fields.

        Supported survey prefixes: SM, CE, LA, JT, CU.
        Each segment value is looked up in the local reference catalog;
        unknown codes have a null label rather than a fabricated description.

        Returns on success:
            {
              "series_id": "SMU17169800500000001",
              "prefix": "SM",
              "survey": "State and Metro Area Employment, Hours, and Earnings",
              "segments": [
                {"name": "seasonal", "value": "U",
                 "label": "Not Seasonally Adjusted"},
                {"name": "state_code", "value": "17",    "label": "Illinois"},
                ...
              ]
            }

        Returns on unknown prefix:
            {"error": "Unrecognised series ID prefix 'XX'.", "series_id": "XX..."}
        """
        return decode_id(series_id)
