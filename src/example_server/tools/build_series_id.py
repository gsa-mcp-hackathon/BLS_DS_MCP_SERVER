"""Tool: build_series_id — assemble a BLS series ID from named parts."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_series_schema import build_id, decode_id


def register(mcp: FastMCP) -> None:
    """Register the build_series_id tool."""

    @mcp.tool(
        name="build_series_id",
        annotations={
            "title": "Build BLS Series ID",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def build_series_id(
        survey: Annotated[
            str,
            "Survey prefix: 'SM', 'CE', 'LA', 'JT', 'CU', 'LN', 'PR', 'MP', 'CI'.",
        ],
        seasonal_adjustment: Annotated[
            str,
            "'S' for seasonally adjusted, 'U' for not seasonally adjusted.",
        ],
        state_code: Annotated[
            str, "2-digit state FIPS code (SM/JT only, e.g. '17' for Illinois)."
        ] = "",
        area_code: Annotated[
            str,
            "Area code (SM: 5-digit metro code; LA: 15-char area code;"
            " CU: 4-char code).",
        ] = "",
        supersector_code: Annotated[
            str, "2-digit supersector code (SM/CE only, e.g. '05' for Total Private)."
        ] = "",
        industry_code: Annotated[
            str, "6-digit industry code (SM/CE/JT, e.g. '000000' for Total Nonfarm)."
        ] = "",
        data_type_code: Annotated[
            str, "2-digit data type code (SM/CE, e.g. '01' for All Employees)."
        ] = "",
        measure_code: Annotated[
            str,
            "2-digit measure code (LA: e.g. '03' for unemployment rate;"
            " PR: e.g. '01' for output per hour).",
        ] = "",
        sizeclass_code: Annotated[
            str, "2-digit size class code (JT only, e.g. '00' for All size classes)."
        ] = "",
        dataelement_code: Annotated[
            str, "2-char data element code (JT only, e.g. 'JO' for Job Openings)."
        ] = "",
        ratelevel_code: Annotated[
            str, "1-char rate/level code (JT only, e.g. 'L' for level, 'R' for rate)."
        ] = "",
        periodicity: Annotated[
            str, "1-char periodicity code (CU only, e.g. 'R' for monthly)."
        ] = "",
        item_code: Annotated[
            str,
            "Up to 8-char item/expenditure code (CU only, e.g. 'SA0' for All Items).",
        ] = "",
        sector_code: Annotated[
            str, "4-digit sector code (PR/MP only, e.g. '3000' for Manufacturing)."
        ] = "",
        class_code: Annotated[
            str, "1-digit class code (PR only, e.g. '6' for Output per job)."
        ] = "",
        duration_code: Annotated[
            str, "1-digit duration/index type code (PR/MP only, e.g. '3' for index)."
        ] = "",
        owner_code: Annotated[
            str,
            "1-digit ownership type code (CI only, e.g. '1' for Civilian workers).",
        ] = "",
        estimate_code: Annotated[
            str,
            "2-digit estimate type code (CI only, e.g. '01' for Total compensation).",
        ] = "",
        series_code: Annotated[
            str,
            "10-char opaque series identifier (CI only).",
        ] = "",
        periodicity_code: Annotated[
            str,
            "1-char periodicity/change type code (CI only,"
            " e.g. 'I' for index, 'C' for % change).",
        ] = "",
    ) -> dict[str, Any]:
        """Assemble a valid BLS series ID from named dimension values.

        Use lookup_area_code and lookup_industry_code to find the right codes
        before calling this tool.

        Returns on success:
            {"series_id": "SMU17169800500000001", "decoded": {...}}

        Returns on failure:
            {"error": "...", "missing_fields": [...], "required_fields": [...]}
        """
        kwargs: dict[str, str] = {
            "seasonal": seasonal_adjustment,
            "state_code": state_code,
            "area_code": area_code,
            "supersector_code": supersector_code,
            "industry_code": industry_code,
            "data_type_code": data_type_code,
            "measure_code": measure_code,
            "sizeclass_code": sizeclass_code,
            "dataelement_code": dataelement_code,
            "ratelevel_code": ratelevel_code,
            "periodicity": periodicity,
            "item_code": item_code,
            "sector_code": sector_code,
            "class_code": class_code,
            "duration_code": duration_code,
            "owner_code": owner_code,
            "estimate_code": estimate_code,
            "series_code": series_code,
            "periodicity_code": periodicity_code,
        }
        # Strip empty strings so build_id can detect missing required fields.
        kwargs = {k: v for k, v in kwargs.items() if v}

        result = build_id(survey, **kwargs)
        if isinstance(result, dict):
            # Error from build_id
            return result

        # Success — enrich with decoded segments.
        return {"series_id": result, "decoded": decode_id(result)}
