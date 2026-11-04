"""Shared helpers: HTTP client, response formatting, and pagination.

Import these from your tool modules instead of re-implementing them. Keeping
I/O and formatting here keeps each tool file focused on its own logic.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlsplit

import httpx

if TYPE_CHECKING:
    from example_server.models import BLSSeriesRequest

from example_server.config import (
    BLS_V1_BASE_URL,
    BLS_V1_MAX_SERIES,
    BLS_V1_MAX_YEAR_RANGE,
    BLS_V2_BASE_URL,
    BLS_V2_MAX_SERIES,
    BLS_V2_MAX_YEAR_RANGE,
    get_bls_api_version,
    settings,
)

# Federal APIs can be slow or intermittently unresponsive — always use an
# explicit timeout. Bump this for large exports.
DEFAULT_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 5_000_000

# Keep outbound origins operator-controlled. Do not replace this with a tool
# argument; add another narrowly scoped client when integrating another API.
API_BASE_URL = "https://api.example.gov/v1/"


class UpstreamServiceError(RuntimeError):
    """Sanitized external-service failure safe to return to an MCP client."""


class BLSAPIError(RuntimeError):
    """BLS API-level failure: bad envelope status, missing data, or rejected key.

    Distinct from UpstreamServiceError (transport/HTTP failures) so callers can
    give the agent precise, actionable feedback about what went wrong.
    """


def _validate_relative_path(path: str) -> str:
    """Reject paths that could select or escape the configured API origin."""
    parsed = urlsplit(path)
    decoded_path = parsed.path
    for _ in range(3):
        decoded = unquote(decoded_path)
        if decoded == decoded_path:
            break
        decoded_path = decoded
    segments = decoded_path.replace("\\", "/").split("/")
    if (
        not path
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or decoded_path.startswith(("/", "\\"))
        or any(segment in {".", ".."} for segment in segments)
    ):
        raise ValueError("path must be a relative API path without a query or fragment")
    return path


async def fetch_json(
    path: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """GET a path from the fixed API origin and return parsed JSON.

    Raises:
        ValueError: if path could select or escape the configured API origin.
        UpstreamServiceError: with a sanitized message for external failures.
    """
    safe_path = _validate_relative_path(path)
    try:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            follow_redirects=False,
            timeout=timeout,
            trust_env=False,
        ) as client:
            async with client.stream(
                "GET", safe_path, params=params, headers=headers
            ) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE_BYTES:
                        raise UpstreamServiceError(
                            "Upstream response exceeded the size limit."
                        )
                return json.loads(content)
    except UpstreamServiceError:
        raise
    except httpx.HTTPStatusError as exc:
        raise UpstreamServiceError(
            f"Upstream service returned status {exc.response.status_code}."
        ) from None
    except (httpx.DecodingError, json.JSONDecodeError, UnicodeDecodeError):
        raise UpstreamServiceError("Upstream service returned invalid JSON.") from None
    except httpx.RequestError:
        raise UpstreamServiceError("Upstream service request failed.") from None


async def fetch_bls(
    payload: dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST a request to the BLS Public Data API and return the raw JSON envelope.

    Automatically selects v1 or v2 based on whether BLS_API_KEY is configured.
    When using v2, injects the registration key into a copy of the payload —
    the caller's dict is never mutated, and the key value is never logged or
    returned in any error message.

    Args:
        payload: BLS request body (seriesid, startyear, endyear, etc.).
                 Do NOT include registrationKey — it is injected here when needed.
        timeout: HTTP timeout in seconds (default: 30).

    Returns:
        The full parsed JSON envelope from BLS (status, message, Results, ...).

    Raises:
        BLSAPIError: if the registration key is rejected (HTTP 401/403 on v2).
        UpstreamServiceError: for transport failures, non-auth HTTP errors,
                              response size exceeded, or malformed JSON.
    """
    version = get_bls_api_version()
    base_url = BLS_V2_BASE_URL if version == "v2" else BLS_V1_BASE_URL

    # Copy payload before injecting key — never mutate the caller's dict.
    request_payload = dict(payload)
    if version == "v2":
        request_payload["registrationKey"] = settings.bls_api_key.get_secret_value()

    endpoint = f"{base_url}timeseries/data/"
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            trust_env=False,
        ) as client:
            async with client.stream(
                "POST",
                endpoint,
                json=request_payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status_code in (401, 403) and version == "v2":
                    raise BLSAPIError(
                        "BLS API rejected the registration key. "
                        "Verify BLS_API_KEY is a valid registered key."
                    )
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE_BYTES:
                        raise UpstreamServiceError(
                            "BLS API response exceeded the size limit."
                        )
                return json.loads(content)
    except (BLSAPIError, UpstreamServiceError):
        raise
    except httpx.HTTPStatusError as exc:
        raise UpstreamServiceError(
            f"BLS API returned HTTP {exc.response.status_code}."
        ) from None
    except (httpx.DecodingError, json.JSONDecodeError, UnicodeDecodeError):
        raise UpstreamServiceError("BLS API returned invalid JSON.") from None
    except httpx.RequestError:
        raise UpstreamServiceError("BLS API request failed.") from None


def unwrap_bls_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the BLS response envelope and return the raw series list.

    Data integrity guarantees:
    - Value strings are returned exactly as published by BLS ("274.310", not 274.31).
    - Missing observations ("-" or ".") pass through unchanged — never replaced with 0.
    - footnotes, period, and periodName are returned verbatim.
    - No fields are fabricated when absent.

    Args:
        payload: The full JSON dict returned by fetch_bls().

    Returns:
        The list of series dicts from payload["Results"]["series"].

    Raises:
        BLSAPIError: if status is not REQUEST_SUCCEEDED, or Results/series keys
                     are missing from a nominally successful response.
    """
    status = payload.get("status", "")
    if status != "REQUEST_SUCCEEDED":
        # Extract BLS message lines for the error, but never include any value
        # that could be the API key (keys are 32-char hex strings).
        raw_messages = payload.get("message", [])
        safe_messages = [m for m in raw_messages if not _contains_api_key(str(m))]
        detail = "; ".join(safe_messages) if safe_messages else "No details provided."
        raise BLSAPIError(f"BLS API returned status '{status}': {detail}")

    results = payload.get("Results")
    if results is None:
        raise BLSAPIError(
            "BLS API reported REQUEST_SUCCEEDED but 'Results' is missing."
        )
    series = results.get("series")
    if series is None:
        raise BLSAPIError(
            "BLS API reported REQUEST_SUCCEEDED but 'Results.series' is missing."
        )
    return series


def _contains_api_key(value: str) -> bool:
    """Return True if the string contains an embedded 32-character hex API key."""
    import re

    return bool(re.search(r"[0-9a-fA-F]{32}", value))


def validate_series_request(request: "BLSSeriesRequest") -> None:
    """Enforce version-specific BLS API limits before issuing a network request.

    The Pydantic model (BLSSeriesRequest) applies the absolute maximum limits
    (v2 values). This function applies the stricter v1 limits — or v2 limits —
    based on the API version currently configured via BLS_API_KEY.

    Args:
        request: A validated BLSSeriesRequest instance.

    Raises:
        BLSAPIError: with an actionable message when a limit is exceeded.
    """
    # Deferred import to avoid circular dependency at module load time.
    from example_server.models import BLSSeriesRequest

    if not isinstance(request, BLSSeriesRequest):
        raise TypeError("request must be a BLSSeriesRequest instance.")

    version = get_bls_api_version()

    if version == "v1":
        # ── Series count ──────────────────────────────────────────────────────
        if len(request.series_ids) > BLS_V1_MAX_SERIES:
            raise BLSAPIError(
                f"v1 allows up to {BLS_V1_MAX_SERIES} series per request "
                f"({len(request.series_ids)} provided). "
                "Configure BLS_API_KEY to use v2 "
                f"(up to {BLS_V2_MAX_SERIES} series)."
            )
        # ── Year range ────────────────────────────────────────────────────────
        if request.start_year is not None and request.end_year is not None:
            span = request.end_year - request.start_year + 1
            if span > BLS_V1_MAX_YEAR_RANGE:
                raise BLSAPIError(
                    f"v1 allows a maximum year range of {BLS_V1_MAX_YEAR_RANGE} years "
                    f"({span} years requested). "
                    "Configure BLS_API_KEY to use v2 "
                    f"(up to {BLS_V2_MAX_YEAR_RANGE} years)."
                )
        # ── v2-only options ───────────────────────────────────────────────────
        if request.calculations:
            raise BLSAPIError(
                "The calculations option requires BLS API v2. "
                "Configure BLS_API_KEY to enable v2."
            )
        if request.annual_average:
            raise BLSAPIError(
                "The annual_average option requires BLS API v2. "
                "Configure BLS_API_KEY to enable v2."
            )
    else:
        # ── v2 series count ───────────────────────────────────────────────────
        if len(request.series_ids) > BLS_V2_MAX_SERIES:
            raise BLSAPIError(
                f"v2 allows a maximum of {BLS_V2_MAX_SERIES} series per request "
                f"({len(request.series_ids)} provided)."
            )
        # ── v2 year range ─────────────────────────────────────────────────────
        if request.start_year is not None and request.end_year is not None:
            span = request.end_year - request.start_year + 1
            if span > BLS_V2_MAX_YEAR_RANGE:
                raise BLSAPIError(
                    f"v2 allows a maximum year range of {BLS_V2_MAX_YEAR_RANGE} years "
                    f"({span} years requested)."
                )


def paginate(items: list[Any], limit: int, offset: int) -> dict[str, Any]:
    """Slice a list and return a standard pagination envelope.

    Returns a dict with `total`, `count`, `offset`, `items`, `has_more`, and
    `next_offset` — the shape recommended in the MCP best-practices guide.
    """
    total = len(items)
    window = items[offset : offset + limit]
    next_offset = offset + len(window)
    return {
        "total": total,
        "count": len(window),
        "offset": offset,
        "items": window,
        "has_more": next_offset < total,
        "next_offset": next_offset if next_offset < total else None,
    }
