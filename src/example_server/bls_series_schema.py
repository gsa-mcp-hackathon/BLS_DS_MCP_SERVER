"""BLS series ID structural schemas.

Maps every supported survey prefix to its segment layout so build_id,
decode_id, and validate_series_id share one authoritative definition.

Reference: https://www.bls.gov/help/hlpforma.htm

Supported surveys: SM, CE, LA, JT, CU
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SeriesSegment:
    """One named field within a BLS series ID.

    Attributes:
        name:        Python-friendly field name (e.g. "state_code").
        start:       0-based character position (after stripping the 2-char prefix).
        length:      Number of characters.
        description: Human-readable label shown in decode output.
        catalog_key: Optional (survey, dimension) pair for code→name resolution
                     via catalog.get(survey, dimension)[value].
        lookup_pad:  Optional string appended to the raw value before the catalog
                     lookup.  Use when the series ID stores a shorter code than the
                     catalog key (e.g. SM industry_code is 6 chars in the ID but
                     8 chars in sm.industry → lookup_pad="00").
    """

    name: str
    start: int
    length: int
    description: str
    catalog_key: tuple[str, str] | None = None
    lookup_pad: str = ""


@dataclass
class SeriesSchema:
    """Full layout definition for one BLS survey prefix.

    Attributes:
        prefix:        2-character series ID prefix (e.g. "SM").
        survey_name:   Human-readable survey name.
        total_length:  Total expected series ID length including the prefix.
                       None means the length is variable (not applicable here,
                       all currently supported surveys have fixed lengths).
        segments:      Ordered list of segments AFTER the 2-char prefix.
    """

    prefix: str
    survey_name: str
    total_length: int
    segments: list[SeriesSegment] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

# SM — State and Metro Area Employment, Hours, and Earnings
# Format: SM(2) + seasonal(1) + state(2) + area(5) + supersector(2) + industry(8)
#         + data_type(2)
# Total: 2 + 1 + 2 + 5 + 2 + 8 - 2 ... let's count from real IDs:
# Example: SMU17169800500000001  -> 20 chars
# SM(2) + U(1) + 17(2) + 16980(5) + 05(2) + 00000000(8) + 01(2) = 22? No.
# BLS docs: SM(2)+seasonal(1)+state(2)+area(5)+supersector(2)+industry(6)
#           +data_type(2) = 20
_SM = SeriesSchema(
    prefix="SM",
    survey_name="State and Metro Area Employment, Hours, and Earnings",
    total_length=20,
    segments=[
        SeriesSegment("seasonal", 0, 1, "Seasonal adjustment code", ("ce", "seasonal")),
        SeriesSegment("state_code", 1, 2, "State FIPS code", ("sm", "state")),
        SeriesSegment("area_code", 3, 5, "Metropolitan area code", ("sm", "area")),
        SeriesSegment(
            "supersector_code", 8, 2, "Supersector code", ("sm", "supersector")
        ),
        SeriesSegment(
            "industry_code", 10, 6, "Industry code", ("sm", "industry"), lookup_pad="00"
        ),
        SeriesSegment("data_type_code", 16, 2, "Data type code", ("sm", "data_type")),
    ],
)

# CE — Current Employment Statistics
# Format: CE(2) + seasonal(1) + supersector(2) + industry(6) + data_type(2) = 13
_CE = SeriesSchema(
    prefix="CE",
    survey_name="Current Employment Statistics",
    total_length=13,
    segments=[
        SeriesSegment("seasonal", 0, 1, "Seasonal adjustment code", ("ce", "seasonal")),
        SeriesSegment(
            "supersector_code", 1, 2, "Supersector code", ("ce", "supersector")
        ),
        SeriesSegment(
            "industry_code", 3, 6, "Industry code", ("ce", "industry"), lookup_pad="00"
        ),
        SeriesSegment("data_type_code", 9, 2, "Data type code", ("ce", "datatype")),
    ],
)

# LA — Local Area Unemployment Statistics
# Format: LA(2) + seasonal(1) + area_code(15) + measure(2) = 20
# area_code column in la.area is 15 chars (e.g. "ST0100000000000")
_LA = SeriesSchema(
    prefix="LA",
    survey_name="Local Area Unemployment Statistics",
    total_length=20,
    segments=[
        SeriesSegment("seasonal", 0, 1, "Seasonal adjustment code", ("ce", "seasonal")),
        SeriesSegment("area_code", 1, 15, "Area code", ("la", "area")),
        SeriesSegment("measure_code", 16, 2, "Measure code", ("la", "measure")),
    ],
)

# JT — Job Openings and Labor Turnover Survey
# Format: JT(2) + seasonal(1) + state(2) + industry(6) + sizeclass(2)
#         + dataelement(2) + ratelevel(1) = 16 after prefix
# Total: 18 chars  e.g. "JTS000000000000001"
_JT = SeriesSchema(
    prefix="JT",
    survey_name="Job Openings and Labor Turnover Survey",
    total_length=18,
    segments=[
        SeriesSegment("seasonal", 0, 1, "Seasonal adjustment code", ("ce", "seasonal")),
        SeriesSegment("state_code", 1, 2, "State code", ("jt", "state")),
        SeriesSegment("industry_code", 3, 6, "Industry code", ("jt", "industry")),
        SeriesSegment(
            "sizeclass_code", 9, 2, "Establishment size class", ("jt", "sizeclass")
        ),
        SeriesSegment(
            "dataelement_code", 11, 2, "Data element code", ("jt", "dataelement")
        ),
        SeriesSegment("ratelevel_code", 13, 1, "Rate or level", ("jt", "ratelevel")),
    ],
)

# CU — Consumer Price Index — All Urban Consumers
# Format: CU(2) + seasonal(1) + periodicity(1) + area(4) + item(8) = 16
_CU = SeriesSchema(
    prefix="CU",
    survey_name="Consumer Price Index — All Urban Consumers",
    total_length=16,
    segments=[
        SeriesSegment("seasonal", 0, 1, "Seasonal adjustment code", ("ce", "seasonal")),
        SeriesSegment("periodicity", 1, 1, "Periodicity code", None),
        SeriesSegment("area_code", 2, 4, "Area code", ("cu", "area")),
        SeriesSegment("item_code", 6, 8, "Item/expenditure category", ("cu", "item")),
    ],
)

# Master registry
SCHEMAS: dict[str, SeriesSchema] = {
    "SM": _SM,
    "CE": _CE,
    "LA": _LA,
    "JT": _JT,
    "CU": _CU,
}


def get_schema(series_id: str) -> SeriesSchema | None:
    """Return the schema for the given series ID, or None if unrecognised."""
    return SCHEMAS.get(series_id[:2].upper())


def decode_id(series_id: str) -> dict[str, Any]:
    """Decode a BLS series ID into named, labelled segments.

    Returns:
        On success::

            {
                "series_id": "SMU17...",
                "prefix": "SM",
                "survey": "State and Metro Area Employment...",
                "segments": [
                    {"name": "seasonal", "value": "U",
                     "label": "Not Seasonally Adjusted"},
                    ...
                ]
            }

        On unknown prefix::

            {"error": "Unrecognised series ID prefix 'XX'.",
             "series_id": "XX..."}
    """
    # Import here to avoid circular import at module load time.
    from example_server.catalog import catalog  # noqa: PLC0415

    sid = series_id.strip().upper()
    schema = get_schema(sid)
    if schema is None:
        prefix = sid[:2] if len(sid) >= 2 else sid
        return {
            "error": f"Unrecognised series ID prefix '{prefix}'.",
            "series_id": series_id,
        }

    body = sid[2:]  # strip prefix
    segments: list[dict[str, Any]] = []

    for seg in schema.segments:
        value = body[seg.start : seg.start + seg.length]
        label: str | None = None
        if seg.catalog_key is not None:
            mapping = catalog.get(*seg.catalog_key)
            lookup_key = value + seg.lookup_pad if seg.lookup_pad else value
            label = mapping.get(lookup_key)  # None when code not in catalog
        segments.append({"name": seg.name, "value": value, "label": label})

    return {
        "series_id": series_id,
        "prefix": schema.prefix,
        "survey": schema.survey_name,
        "segments": segments,
    }


def build_id(survey: str, **kwargs: str) -> str | dict[str, Any]:
    """Assemble a BLS series ID from named keyword arguments.

    Args:
        survey:  Survey prefix (e.g. "SM", "CE", "LA").
        **kwargs: Segment name → value mappings (e.g. seasonal="U",
                  state_code="17", area_code="16980", ...).

    Returns:
        The assembled series ID string on success, or an error dict::

            {"error": "...",
             "missing_fields": ["area_code", ...],
             "required_fields": [...]}
    """
    schema = SCHEMAS.get(survey.upper())
    if schema is None:
        return {
            "error": f"Unknown survey prefix '{survey}'. "
            f"Supported: {', '.join(sorted(SCHEMAS))}.",
            "missing_fields": [],
            "required_fields": [],
        }

    # Build a blank body of the expected length (minus the 2-char prefix).
    body_len = schema.total_length - 2
    body = [" "] * body_len

    missing: list[str] = []
    for seg in schema.segments:
        value = kwargs.get(seg.name, "")
        if not value:
            missing.append(seg.name)
            continue
        # Pad / truncate to the exact segment length.
        value = str(value)[: seg.length].ljust(seg.length)
        for i, ch in enumerate(value):
            body[seg.start + i] = ch

    if missing:
        return {
            "error": f"Missing required fields for {survey.upper()} series ID.",
            "missing_fields": missing,
            "required_fields": [s.name for s in schema.segments],
        }

    return schema.prefix + "".join(body)
