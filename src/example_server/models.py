"""Pydantic models and enums for tool parameters and responses.

Typed parameters give MCP clients a precise schema, which helps the LLM call
your tools correctly. Prefer enums for closed sets of values and Pydantic
models for structured inputs/outputs.

These are illustrative — replace them with models for your own service.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ResponseFormat(str, Enum):
    """How a tool should shape its return value.

    - JSON     → machine-readable dict/list (best for chaining tool calls)
    - MARKDOWN → human-readable text (best for direct display)
    """

    JSON = "json"
    MARKDOWN = "markdown"


class PaginationParams(BaseModel):
    """Reusable pagination inputs for list-style tools.

    Federal APIs almost always paginate. Expose these to the caller (or handle
    paging internally) and return `has_more` / `next_offset` in your response.
    """

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return (1–100).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip from the start of the result set.",
    )


# ── BLS series ID format ───────────────────────────────────────────────────────
# BLS series IDs are uppercase alphanumeric strings. The practical length range
# across all BLS surveys is 1–20 characters.
_BLS_SERIES_ID_RE = re.compile(r"^[A-Z0-9]{1,20}$")


class BLSSeriesRequest(BaseModel):
    """Input parameters for a BLS time-series data request.

    Validated against BLS Public Data API constraints before any network call.
    The most permissive limits (v2) are applied at model level; stricter v1
    limits are enforced at call time by validate_series_request() in utils.py
    once the active API version is known.

    BLS API reference:
      v1: https://www.bls.gov/developers/api_signature.htm
      v2: https://www.bls.gov/developers/api_signature_v2.htm
    """

    series_ids: list[str] = Field(
        description=(
            "One or more BLS series IDs (e.g. 'CUUR0000SA0'). "
            "Uppercase alphanumeric, 1–20 characters each. "
            "v1 max: 25 series; v2 max: 50 series."
        ),
    )
    start_year: int | None = Field(
        default=None,
        description=(
            "4-digit start year for the data range (e.g. 2020). "
            "When omitted, BLS returns its default range (typically last 3 years)."
        ),
    )
    end_year: int | None = Field(
        default=None,
        description=(
            "4-digit end year for the data range (e.g. 2024). "
            "Must be >= start_year. "
            "v1 max range: 10 years; v2 max range: 20 years."
        ),
    )
    calculations: bool = Field(
        default=False,
        description=(
            "Include net and percent change calculations in the response. "
            "Requires BLS API v2 (BLS_API_KEY must be configured)."
        ),
    )
    annual_average: bool = Field(
        default=False,
        description=(
            "Include the annual average row in the response. "
            "Requires BLS API v2 (BLS_API_KEY must be configured)."
        ),
    )

    @field_validator("series_ids")
    @classmethod
    def validate_series_ids(cls, v: list[str]) -> list[str]:
        """Require at least one series ID and enforce BLS format."""
        if not v:
            raise ValueError("series_ids must contain at least one series ID.")
        for sid in v:
            if not _BLS_SERIES_ID_RE.match(sid):
                raise ValueError(
                    f"Invalid series ID '{sid}'. "
                    "BLS series IDs must be uppercase alphanumeric, 1–20 characters "
                    "(e.g. 'CUUR0000SA0')."
                )
        return v

    @field_validator("start_year", "end_year", mode="before")
    @classmethod
    def validate_year_digits(cls, v: object) -> object:
        """Require 4-digit years when provided."""
        if v is None:
            return v
        year = int(v)  # pydantic will already have coerced str→int for int fields
        if not (1000 <= year <= 9999):
            raise ValueError(
                f"'{v}' is not a valid 4-digit year. "
                "Years must be between 1000 and 9999."
            )
        return year

    @model_validator(mode="after")
    def validate_year_range(self) -> Self:
        """Enforce start_year <= end_year and the absolute maximum range of 20 years."""
        if self.start_year is not None and self.end_year is not None:
            if self.start_year > self.end_year:
                raise ValueError(
                    f"start_year ({self.start_year}) must be <= "
                    f"end_year ({self.end_year})."
                )
            span = self.end_year - self.start_year + 1
            if span > 20:
                raise ValueError(
                    f"Year range of {span} years exceeds the maximum of 20 years "
                    "(BLS API v2 limit). For v1, the maximum is 10 years."
                )
        return self
