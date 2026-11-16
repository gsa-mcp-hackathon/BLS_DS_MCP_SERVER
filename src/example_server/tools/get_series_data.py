"""Tool: get_series_data — fetch live BLS time-series observations."""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastmcp import FastMCP

from example_server.bls_flagship_series import get_flagship
from example_server.bls_series_schema import decode_id
from example_server.config import get_bls_api_version
from example_server.models import BLSSeriesRequest
from example_server.utils import (
    BLSAPIError,
    UpstreamServiceError,
    fetch_bls,
    unwrap_bls_response,
    validate_series_request,
)


def register(mcp: FastMCP) -> None:
    """Register the get_series_data tool."""

    @mcp.tool(
        name="get_series_data",
        annotations={
            "title": "Get BLS Series Data",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def get_series_data(
        series_ids: Annotated[
            list[str],
            "One or more BLS series IDs (e.g. ['CUUR0000SA0']). "
            "v1 max: 25 per request; v2 max: 50 per request.",
        ],
        start_year: Annotated[
            int | None,
            "4-digit start year (e.g. 2020). Omit to use BLS default "
            f"(3 most recent years; includes {datetime.date.today().year}).",
        ] = None,
        end_year: Annotated[
            int | None,
            f"4-digit end year (e.g. {datetime.date.today().year - 2} "
            f"or {datetime.date.today().year}). Must be >= start_year. "
            f"Pass {datetime.date.today().year} to include current-year data.",
        ] = None,
        calculations: Annotated[
            bool,
            "Include net/percent change calculations. Requires BLS API v2"
            " (BLS_API_KEY configured).",
        ] = False,
        annual_average: Annotated[
            bool,
            "Include annual average row. Requires BLS API v2.",
        ] = False,
    ) -> dict[str, Any]:
        """Fetch time-series observations from the BLS Public Data API.

        This is the only tool in this server that makes a live network call.
        Use search_series or suggest_series to find the right series IDs first,
        then validate_series_id to confirm they are well-formed.

        Data freshness: BLS publishes monthly updates; values are preliminary
        and may be revised. All values are returned as strings to preserve the
        published precision (e.g. "314.175", not 314.175).

        Returns:
            {
              "api_version": "v1"|"v2",
              "series": [
                {
                  "series_id": str,
                  "label": str,
                  "observations": [
                   {"year","period","period_name","value","footnotes"}
                 ],
                 "notes": str         # only for flagship series
                 "concept": str       # only for flagship series
                 "measure_type": str  # only for flagship series
                 "unit": str          # only for flagship series
                }
              ],
              "notes": "Values are strings to preserve published precision."
            }

        On error:
            {"error": str, "series_ids": [...]}
        """
        # 1. Validate request parameters via Pydantic model.
        try:
            request = BLSSeriesRequest(
                series_ids=series_ids,
                start_year=start_year,
                end_year=end_year,
                calculations=calculations,
                annual_average=annual_average,
            )
        except Exception as exc:
            return {"error": str(exc), "series_ids": series_ids}

        # 2. Enforce version-specific limits.
        try:
            validate_series_request(request)
        except BLSAPIError as exc:
            return {"error": str(exc), "series_ids": series_ids}

        # 3. Build BLS POST payload.
        payload: dict[str, Any] = {"seriesid": request.series_ids}
        if request.start_year is not None:
            payload["startyear"] = str(request.start_year)
        if request.end_year is not None:
            payload["endyear"] = str(request.end_year)
        if request.calculations:
            payload["calculations"] = True
        if request.annual_average:
            payload["annualaverage"] = True

        # 4. Fetch from BLS API.
        try:
            raw = await fetch_bls(payload)
            series_list = unwrap_bls_response(raw)
        except (BLSAPIError, UpstreamServiceError) as exc:
            return {"error": str(exc), "series_ids": series_ids}

        # 5. Enrich each series with a decoded label.
        enriched: list[dict[str, Any]] = []
        for series_obj in series_list:
            sid = series_obj.get("seriesID", "")
            decoded = decode_id(sid) if sid else {}
            if "error" not in decoded and decoded.get("segments"):
                segs = decoded["segments"]
                label_parts = [
                    s["label"] or s["value"]
                    for s in segs
                    if s.get("label") or s.get("value")
                ]
                label = f"{decoded.get('survey', sid)} — " + ", ".join(label_parts[:3])
            else:
                label = sid

            entry: dict[str, Any] = {
                "series_id": sid,
                "label": label,
                "observations": series_obj.get("data", []),
            }
            flagship = get_flagship(sid) if sid else None
            if flagship:
                entry["notes"] = flagship.notes
                if flagship.concept:
                    entry["concept"] = flagship.concept
                if flagship.measure_type:
                    entry["measure_type"] = flagship.measure_type
                if flagship.unit:
                    entry["unit"] = flagship.unit
            enriched.append(entry)

        return {
            "api_version": get_bls_api_version(),
            "series": enriched,
            "notes": (
                "Data sourced from BLS Public Data API. "
                "Values are strings to preserve published precision."
            ),
        }
