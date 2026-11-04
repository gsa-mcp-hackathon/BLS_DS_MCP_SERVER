"""Tool: validate_series_id — check a BLS series ID without a network call."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_series_schema import SCHEMAS, decode_id, get_schema


def register(mcp: FastMCP) -> None:
    """Register the validate_series_id tool."""

    @mcp.tool(
        name="validate_series_id",
        annotations={
            "title": "Validate BLS Series ID",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def validate_series_id(
        series_id: Annotated[
            str, "The BLS series ID to validate (e.g. 'CUUR0000SA0')."
        ],
    ) -> dict[str, Any]:
        """Check a BLS series ID for structural validity and catalog membership.

        Checks performed (all local — no network call):
        1. The 2-char prefix maps to a known survey schema (SM, CE, LA, JT, CU).
        2. The total length matches the schema's expected length.
        3. Each segment code is present in the corresponding catalog table.

        Returns:
            {
              "series_id": str,
              "valid": bool,
              "issues": [str, ...],   # empty on success
              "decoded": dict | null
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
                "decoded": None,
            }

        # Length check
        if len(sid) != schema.total_length:
            issues.append(
                f"Expected length {schema.total_length} for {schema.prefix} series, "
                f"got {len(sid)}."
            )

        # Segment catalog checks (only when length is correct)
        decoded: dict[str, Any] | None = None
        if not issues:
            decoded = decode_id(sid)
            for seg_info in decoded.get("segments", []):
                if seg_info["label"] is None:
                    # Find the segment definition to name the catalog
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

        return {
            "series_id": series_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "decoded": decoded,
        }
