"""Tool: get_series_metadata — local decode + validate + flagship notes."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_flagship_series import get_flagship
from example_server.bls_series_schema import SCHEMAS, decode_id, get_schema


def register(mcp: FastMCP) -> None:
    """Register the get_series_metadata tool."""

    @mcp.tool(
        name="get_series_metadata",
        annotations={
            "title": "Get BLS Series Metadata",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def get_series_metadata(
        series_id: Annotated[
            str, "The BLS series ID to describe (e.g. 'CUUR0000SA0')."
        ],
    ) -> dict[str, Any]:
        """Return everything known about a BLS series ID without making a network call.

        Combines:
        - Structural validation (prefix, length, segment codes)
        - Decoded segment labels from the local catalog
        - Publication notes for known flagship series

        Always local — use get_series_data to fetch actual observations.

        Returns:
            {
              "series_id": str,
              "valid": bool,
              "issues": [str, ...],
              "survey": str,
              "prefix": str,
              "segments": [...],
              "notes": str         # only for flagship series
              "concept": str       # only for flagship series
              "measure_type": str  # only for flagship series
              "unit": str          # only for flagship series
            }
        """
        sid = series_id.strip().upper()
        issues: list[str] = []

        schema = get_schema(sid)
        if schema is None:
            prefix = sid[:2] if len(sid) >= 2 else sid
            known = ", ".join(sorted(SCHEMAS))
            issues.append(f"Unrecognised survey prefix '{prefix}'. Supported: {known}.")
            return {
                "series_id": series_id,
                "valid": False,
                "issues": issues,
                "survey": None,
                "prefix": prefix,
                "segments": [],
            }

        if len(sid) != schema.total_length:
            issues.append(
                f"Expected length {schema.total_length} for {schema.prefix} series, "
                f"got {len(sid)}."
            )

        decoded = decode_id(sid)
        segments = decoded.get("segments", [])

        if not issues:
            for seg_info in segments:
                if seg_info["label"] is None:
                    matching_segs = [
                        s for s in schema.segments if s.name == seg_info["name"]
                    ]
                    if matching_segs and matching_segs[0].catalog_key:
                        sv, dim = matching_segs[0].catalog_key
                        issues.append(
                            f"Code '{seg_info['value']}' for field"
                            f" '{seg_info['name']}' "
                            f"not found in {sv}.{dim} catalog."
                        )

        result: dict[str, Any] = {
            "series_id": series_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "survey": schema.survey_name,
            "prefix": schema.prefix,
            "segments": segments,
        }

        flagship = get_flagship(sid)
        if flagship is not None:
            result["notes"] = flagship.notes
            if flagship.concept:
                result["concept"] = flagship.concept
            if flagship.measure_type:
                result["measure_type"] = flagship.measure_type
            if flagship.unit:
                result["unit"] = flagship.unit

        return result
