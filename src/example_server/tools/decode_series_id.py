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

        IMPORTANT — how to interpret CE (Current Employment Statistics) series:
        CE series IDs have a supersector_code AND an industry_code segment.
        The supersector_code label is the primary industry descriptor
        (e.g. "Private education and health services" for supersector "65").
        When industry_code is "000000" its label resolves to "Total nonfarm" —
        this means "all industries within that supersector", NOT the national
        nonfarm total. Always read supersector_code first to identify the
        industry group; industry_code "000000" simply means no further
        industry sub-division is applied.

        Example: CES6500000001
          supersector_code = "65" → "Private education and health services"
          industry_code    = "000000" → all industries within that supersector
          data_type_code   = "01" → All Employees, Thousands (SA)
          Plain English: Total employees in Private Education & Health Services, SA

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
