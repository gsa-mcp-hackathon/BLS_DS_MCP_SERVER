"""BLS survey reference resources.

Exposes two MCP resources built from local-cache reference files and the
bls_series_schema module:

  bls://surveys/overview
      Index of every survey this server supports — prefix, full name,
      series ID format, available catalog dimensions, and the tools to use.
      Read this first before calling suggest_series, search_series, or
      get_series_data.

  bls://surveys/{survey_code}
      Detailed reference for one survey: series ID segment layout, every
      catalog dimension with entry counts, update frequency, example series
      IDs from the flagship table, and step-by-step usage guidance.

Both resources are served from in-process data (local-cache + schema
definitions) — no network call is made at read time.

Source material:
  - Segment layouts:  src/example_server/bls_series_schema.py (SCHEMAS)
  - Code→name tables: src/example_server/local-cache/  (catalog singleton)
  - Flagship series:  src/example_server/bls_flagship_series.py
  - BLS Public Data API reference: https://www.bls.gov/developers/
  - BLS series ID formats: https://www.bls.gov/help/hlpforma.htm
  - BLS time series pub: https://download.bls.gov/pub/time.series/overview.txt
    (human-readable; automated access blocked by BLS bot policy)
"""

from __future__ import annotations

from fastmcp import FastMCP

from example_server.bls_flagship_series import FLAGSHIP_SERIES
from example_server.bls_series_schema import SCHEMAS
from example_server.catalog import catalog

# ---------------------------------------------------------------------------
# Static per-survey metadata not derivable from bls_series_schema.py alone.
# Update frequency, notes, and tool guidance are sourced from:
#   https://www.bls.gov/developers/  and  https://www.bls.gov/help/hlpforma.htm
# ---------------------------------------------------------------------------

_SURVEY_META: dict[str, dict] = {
    "SM": {
        "full_name": "State and Metro Area Employment, Hours, and Earnings",
        "program": "Current Employment Statistics (State and Metro Area)",
        "update_frequency": "Monthly — released ~3 weeks after the reference month",
        "seasonal_note": (
            "Both seasonally adjusted (S) and not seasonally adjusted (U) series "
            "are available. Preliminary estimates are revised monthly."
        ),
        "unit_note": (
            "All Employees in thousands. Average hourly/weekly earnings in dollars."
        ),
        "data_api_note": (
            "Use the Public Data API timeseries endpoint. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("area", "sm.area", "Metropolitan area code → area name (~433 entries)"),
            ("state", "sm.state", "2-digit state FIPS → state name (51 entries)"),
            ("supersector", "sm.supersector", "2-digit supersector → sector name"),
            ("industry", "sm.industry", "8-digit industry → industry name"),
            ("data_type", "sm.data_type", "2-digit data type → measure description"),
        ],
        "tool_guidance": (
            "1. lookup_area_code   — find a metro area code by city/state name\n"
            "2. lookup_industry_code — find an industry code by keyword\n"
            "3. build_series_id    — assemble the series ID from named parts\n"
            "4. get_series_data    — fetch observations (requires valid series ID)"
        ),
    },
    "CE": {
        "full_name": "Current Employment Statistics (National)",
        "program": "Current Employment Statistics — National",
        "update_frequency": (
            "Monthly — released first or second Friday of the following month "
            "(Employment Situation report)"
        ),
        "seasonal_note": (
            "Seasonally adjusted (S) series are the primary published figures. "
            "Not seasonally adjusted (U) also available. "
            "Benchmark revisions occur annually in February."
        ),
        "unit_note": (
            "All Employees in thousands. Average weekly hours in hours. "
            "Average hourly/weekly earnings in dollars."
        ),
        "data_api_note": (
            "National-level only. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range, "
            "plus net/percent change calculations."
        ),
        "catalog_dimensions": [
            (
                "industry",
                "ce.industry",
                "8-digit NAICS-based industry → name (~900 entries)",
            ),
            ("datatype", "ce.datatype", "2-digit data type → measure description"),
            (
                "seasonal",
                "ce.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),
            ("supersector", "ce.supersector", "2-digit supersector → sector name"),
        ],
        "tool_guidance": (
            "1. lookup_industry_code — find a national industry code by keyword\n"
            "2. build_series_id      — assemble the series ID from named parts\n"
            "3. get_series_data      — fetch observations (requires valid series ID)\n"
            "   OR: use suggest_series with topic='employment' or 'payrolls' for "
            "pre-built flagship series IDs"
        ),
    },
    "LA": {
        "full_name": "Local Area Unemployment Statistics",
        "program": "Local Area Unemployment Statistics (LAUS)",
        "update_frequency": ("Monthly — released ~4 weeks after the reference month"),
        "seasonal_note": (
            "Seasonally adjusted (S) series available for states and"
            " select metro areas. "
            "Not seasonally adjusted (U) available for all geographies."
        ),
        "unit_note": (
            "Unemployment rate in percent. Unemployment and employment"
            " levels in thousands. "
            "Labor force in thousands."
        ),
        "data_api_note": (
            "Widest geographic coverage of any BLS survey (~8,350 area codes). "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("area", "la.area", "15-char area code → area name (~8,351 entries)"),
            (
                "area_type",
                "la.area_type",
                "1-char area type → area type description (7 entries)",
            ),
            ("measure", "la.measure", "2-digit measure code → measure description"),
        ],
        "area_type_note": (
            "Area type codes: A=Statewide, B=Metropolitan areas,"
            " C=Metropolitan divisions, "
            "D=Micropolitan areas, E=Combined areas, F=Counties and equivalents, "
            "G=Cities and towns above 25,000 population"
        ),
        "tool_guidance": (
            "1. lookup_area_code — find an LA area code by place name\n"
            "   (use survey='la' filter for best results — ~8,351 areas available)\n"
            "2. build_series_id  — assemble the series ID from named parts\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   OR: use suggest_series with topic='unemployment rate' for "
            "pre-built national/state flagship series IDs"
        ),
    },
    "JT": {
        "full_name": "Job Openings and Labor Turnover Survey",
        "program": "Job Openings and Labor Turnover Survey (JOLTS)",
        "update_frequency": ("Monthly — released ~5 weeks after the reference month"),
        "seasonal_note": (
            "Seasonally adjusted (S) and not seasonally adjusted (U) series available. "
            "Estimates are subject to revision."
        ),
        "unit_note": ("Levels in thousands of jobs. Rates in percent of employment."),
        "data_api_note": (
            "National and some state-level series available. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("area", "jt.area", "5-digit area code → area name (national + regions)"),
            (
                "state",
                "jt.state",
                "2-digit state code → state name (50 states + DC + US)",
            ),
            ("industry", "jt.industry", "6-digit NAICS industry → industry name"),
            (
                "dataelement",
                "jt.dataelement",
                "2-char data element → turnover type (JO, HI, QU, LD, OS, TS)",
            ),
            (
                "sizeclass",
                "jt.sizeclass",
                "2-digit size class → establishment size range",
            ),
            (
                "ratelevel",
                "jt.ratelevel",
                "1-char rate/level → R=Rate, L=Level in thousands",
            ),
        ],
        "dataelement_note": (
            "Key data elements: JO=Job Openings, HI=Hires, QU=Quits, "
            "LD=Layoffs & Discharges, OS=Other Separations, TS=Total Separations"
        ),
        "tool_guidance": (
            "1. lookup_industry_code — find a JOLTS industry code by keyword\n"
            "2. build_series_id      — assemble the series ID from named parts\n"
            "3. get_series_data      — fetch observations (requires valid series ID)\n"
            "   OR: use suggest_series with topic='job openings' or 'quits' for "
            "pre-built flagship series IDs"
        ),
    },
    "CU": {
        "full_name": "Consumer Price Index — All Urban Consumers",
        "program": "Consumer Price Index (CPI-U)",
        "update_frequency": ("Monthly — released ~2 weeks after the reference month"),
        "seasonal_note": (
            "Seasonally adjusted (S) and not seasonally adjusted (U) series available. "
            "SA series are preferred for trend analysis; NSA used for"
            " cost-of-living adjustments."
        ),
        "unit_note": (
            "Index values (1982-84=100 base period by default). "
            "Percent change calculated from index values."
        ),
        "data_api_note": (
            "Covers ~400 item categories across U.S. city average and"
            " select metro areas. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range, "
            "plus built-in percent change calculations."
        ),
        "periodicity_note": (
            "Periodicity codes: R=Monthly, S=Semi-annual. "
            "Use R for standard monthly CPI series."
        ),
        "catalog_dimensions": [
            (
                "area",
                "cu.area",
                "4-digit area code → area name (U.S. average + metro areas)",
            ),
            (
                "item",
                "cu.item",
                "variable-length item code → expenditure category (~400 entries)",
            ),
        ],
        "tool_guidance": (
            "1. Use suggest_series with topic='CPI' or 'inflation'"
            " for common item codes\n"
            "2. build_series_id — assemble the series ID if you know area"
            " and item codes\n"
            "3. get_series_data — fetch observations (requires valid series ID)\n"
            "   Common items: SA0=All Items, SA0L1E=Core CPI (less food & energy), "
            "SA0E=Energy, SAF1=Food"
        ),
    },
    "LN": {
        "full_name": ("Labor Force Statistics from the Current Population Survey"),
        "program": "Current Population Survey (CPS) — Labor Force Statistics",
        "update_frequency": (
            "Monthly — released first Friday of the following month "
            "(Employment Situation report)"
        ),
        "seasonal_note": (
            "Seasonally adjusted (LNS prefix) and not seasonally adjusted"
            " (LNU prefix) series available. "
            "Seasonal factors are revised annually at year-end."
        ),
        "unit_note": (
            "Rates and ratios (participation rate, unemployment rate,"
            " employment-population ratio) in percent. "
            "Levels (employment, labor force) in thousands of persons."
        ),
        "data_api_note": (
            "National estimates only. Series IDs are opaque — use"
            " suggest_series or the ln.series catalog to find IDs. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "series_id_note": (
            "LN series IDs cannot be decoded segment-by-segment. Only"
            " the 3-char prefix is meaningful: LNS = Seasonally Adjusted,"
            " LNU = Not Seasonally Adjusted. Use suggest_series or"
            " search_series to find series IDs by topic."
        ),
        "catalog_dimensions": [
            (
                "seasonal",
                "ln.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),  # noqa: E501
            ("lfst", "ln.lfst", "Labor force status code → status description"),
            ("sexs", "ln.sexs", "Sex code → Both Sexes / Men / Women"),
            ("ages", "ln.ages", "Age group code → age range description"),
            ("periodicity", "ln.periodicity", "M=Monthly, Q=Quarterly, A=Annual"),
            ("series", "ln.series", "Series ID → series title (~68k entries)"),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='labor force participation rate')"
            " → returns LNS11300000\n"
            "2. get_series_data — fetch observations (requires valid series ID)\n"
            "3. get_series_metadata — decode the seasonal prefix and show"
            " flagship notes\n"
            "   Note: build_series_id is NOT supported for LN — IDs are opaque."
            " Use suggest_series or search_series instead."
        ),
    },
    "PR": {
        "full_name": "Productivity and Costs",
        "program": "Productivity and Costs — Bureau of Labor Statistics",
        "update_frequency": (
            "Quarterly — preliminary estimate ~6 weeks after quarter end; "
            "revised estimate ~3 months after quarter end"
        ),
        "seasonal_note": (
            "Seasonally adjusted (S) series are the primary published figures. "
            "Covers nonfarm business, business, and manufacturing sectors."
        ),
        "unit_note": (
            "Index values (2017=100 base period). "
            "Percent change from previous quarter or previous year. "
            "Levels (hours, compensation) in various units."
        ),
        "data_api_note": (
            "Quarterly frequency. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("sector", "pr.sector", "4-digit sector code → sector name"),
            ("class", "pr.class", "1-digit class code → index/level class"),
            ("measure", "pr.measure", "2-digit measure code → measure description"),
            (
                "duration",
                "pr.duration",
                "1-digit duration → index type or change period",
            ),
            (
                "seasonal",
                "pr.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='labor productivity') → flagship PR series IDs\n"
            "2. decode_series_id — decode sector, measure, and duration from a PR ID\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   Common sectors: 8500=Nonfarm Business, 3000=Manufacturing\n"
            "   Common measures: 09=Labor Productivity, 11=Unit Labor Costs, "
            "15=Real Hourly Compensation\n"
            "   Duration 2 = percent change from previous quarter; "
            "3 = index (2017=100)"
        ),
    },
    "MP": {
        "full_name": "Multifactor Productivity",
        "program": "Multifactor Productivity — Bureau of Labor Statistics",
        "update_frequency": (
            "Annual — released approximately March of the following year"
        ),
        "seasonal_note": (
            "Not seasonally adjusted (U). Annual data only. "
            "Covers private business, private nonfarm business, and "
            "detailed NAICS industry sectors."
        ),
        "unit_note": (
            "Index values (2017=100 base period). "
            "Covers total factor productivity (TFP), capital, labor, "
            "and combined input indexes."
        ),
        "data_api_note": (
            "Annual frequency only. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("sector", "mp.sector", "4-digit sector code → sector/industry name"),
            ("measure", "mp.measure", "2-digit measure code → measure description"),
            ("duration", "mp.duration", "1-digit duration → index type"),
            ("seasonal", "mp.seasonal", "U=Not Seasonally Adjusted"),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='total factor productivity') "
            "→ flagship MP series IDs\n"
            "2. decode_series_id — decode sector and measure from an MP ID\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   Common sectors: 4910=Private Nonfarm Business, "
            "4900=Private Business\n"
            "   Measure 01 = Total Factor Productivity index; "
            "Duration 2 = annual index"
        ),
    },
    "CW": {
        "full_name": "Consumer Price Index — Urban Wage Earners and Clerical Workers",
        "program": "Consumer Price Index (CPI-W)",
        "update_frequency": ("Monthly — released ~2 weeks after the reference month"),
        "seasonal_note": (
            "Seasonally adjusted (S) and not seasonally adjusted (U) series available. "
            "CPI-W NSA is used for Social Security cost-of-living adjustments (COLA)."
        ),
        "unit_note": (
            "Index values (1982-84=100 base period). "
            "Covers urban wage earners and clerical workers (~28% of U.S. population)."
        ),
        "data_api_note": (
            "Covers U.S. city average and select metro areas. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("area", "cw.area", "4-digit area code → area name"),
            ("item", "cw.item", "variable-length item code → expenditure category"),
            (
                "seasonal",
                "cw.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),
            ("periodicity", "cw.periodicity", "R=Monthly, S=Semi-annual"),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='CPI-W') → flagship CW series IDs\n"
            "2. build_series_id — assemble the series ID if you know area "
            "and item codes\n"
            "3. get_series_data — fetch observations (requires valid series ID)\n"
            "   Common items: SA0=All Items, SA0L1E=Core CPI-W (less food & energy), "
            "SA0E=Energy\n"
            "   CWUR prefix = Not Seasonally Adjusted; "
            "CWSR prefix = Seasonally Adjusted"
        ),
    },
    "WP": {
        "full_name": "PPI Commodity Data",
        "program": "Producer Price Index — Commodity Data",
        "update_frequency": ("Monthly — released ~2 weeks after the reference month"),
        "seasonal_note": (
            "Seasonally adjusted (S, WPS prefix) and not seasonally adjusted "
            "(U, WPU prefix) series available."
        ),
        "unit_note": (
            "Index values (1982=100 base period for commodity PPI; "
            "2009=100 for Final Demand series). "
            "Covers commodity-based and Final Demand-Intermediate Demand PPI."
        ),
        "data_api_note": (
            "Broad coverage: commodity groups, Final Demand aggregates, "
            "and industry net output. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("group", "wp.group", "2-digit commodity group code → group name"),
            ("item", "wp.item", "variable-length item code → commodity description"),
            (
                "seasonal",
                "wp.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='producer price') → flagship WP series IDs\n"
            "2. decode_series_id — decode seasonal code from a WP ID\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   Final Demand aggregates: WPSFD4 (SA), WPUFD4 (NSA)\n"
            "   Core FD: WPUFD49104 (less food & energy), "
            "WPUFD49116 (less food, energy & trade)"
        ),
    },
    "EI": {
        "full_name": "International Price Program",
        "program": "International Price Program (IPP) — Import and Export Prices",
        "update_frequency": ("Monthly — released ~2 weeks after the reference month"),
        "seasonal_note": (
            "Not seasonally adjusted (U) only. "
            "Import prices (IR/CO prefix) and export prices (IQ/CD prefix) available."
        ),
        "unit_note": (
            "Index values (2000=100 base period). "
            "Covers import prices by BEA end-use category and country of origin; "
            "export prices by BEA end-use category and destination."
        ),
        "data_api_note": (
            "Variable-length series IDs. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            (
                "index",
                "ei.index",
                "2-char index type → IR=Import BEA End Use, IQ=Export BEA End Use, "
                "CO=Import by Country, CD=Export by Destination",
            ),
            (
                "seasonal",
                "ei.seasonal",
                "U=Not Seasonally Adjusted",
            ),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='import price') or "
            "suggest_series(topic='export price') → flagship EI series IDs\n"
            "2. decode_series_id — decode the index type code from an EI ID\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   All commodities: EIUIR (imports), EIUIQ (exports)\n"
            "   Series IDs are variable-length; build_series_id is not supported"
        ),
    },
    "CI": {
        "full_name": "Employer Costs for Employee Compensation",
        "program": (
            "National Compensation Survey"
            " — Employer Costs for Employee Compensation (ECEC)"
        ),
        "update_frequency": (
            "Quarterly — released ~3 months after the reference quarter"
        ),
        "seasonal_note": (
            "Seasonally adjusted (S, CIS prefix) and not seasonally adjusted "
            "(U, CIU prefix) series available."
        ),
        "unit_note": (
            "Index values (current dollars) and 3-month or 12-month percent change. "
            "Covers total compensation, wages & salaries, and benefits "
            "for civilian, private, and government workers."
        ),
        "data_api_note": (
            "Quarterly frequency. "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            ("owner", "ci.owner", "1-digit owner → Civilian / Private / State & Local"),
            (
                "estimate",
                "ci.estimate",
                "2-digit estimate code → compensation component",
            ),
            ("industry", "ci.industry", "6-digit industry code → industry name"),
            (
                "occupation",
                "ci.occupation",
                "6-digit occupation code → occupation group",
            ),
            (
                "periodicity",
                "ci.periodicity",
                "I=Index, Q=3-month % change, A=12-month % change",
            ),
            (
                "seasonal",
                "ci.seasonal",
                "S=Seasonally Adjusted, U=Not Seasonally Adjusted",
            ),
        ],
        "tool_guidance": (
            "1. suggest_series(topic='employment cost') → flagship CI series IDs\n"
            "2. decode_series_id — decode owner and estimate from a CI ID\n"
            "3. get_series_data  — fetch observations (requires valid series ID)\n"
            "   CIS prefix = Seasonally Adjusted; "
            "CIU prefix = Not Seasonally Adjusted\n"
            "   Periodicity I = index; Q = 3-month % change; "
            "A = 12-month % change\n"
            "   Civilian workers: owner=1; Private: owner=2; "
            "State & Local Govt: owner=3"
        ),
    },
    "PC": {
        "full_name": "Producer Price Index — Industry Data",
        "program": "Producer Price Index (PPI) — Industry Data",
        "update_frequency": "Monthly — released ~2 weeks after the reference month",
        "seasonal_note": (
            "Seasonally adjusted (S) and not seasonally adjusted (U) series available. "
            "PCU prefix = Not Seasonally Adjusted; PCS prefix = Seasonally Adjusted."
        ),
        "unit_note": (
            "Index values (1982=100 base unless otherwise noted). "
            "Measures average change in selling prices received by domestic producers."
        ),
        "data_api_note": (
            "Variable-length series IDs (industry code + product code, NAICS-based). "
            "v1: up to 25 series / 10-year range. "
            "v2 (registered key): up to 50 series / 20-year range."
        ),
        "catalog_dimensions": [
            (
                "industry",
                "pc.industry",
                "6-digit NAICS industry code → industry name",
            ),
            (
                "product",
                "pc.product",
                "Variable-length product code → product name",
            ),
        ],
        "tool_guidance": (
            "1. lookup_industry_code(query='...', survey='PC') — find a NAICS industry code\n"
            "2. get_series_data    — fetch observations using a known PC series ID\n"
            "   Series ID format: PC + seasonal(1) + industry(6) + product(variable)\n"
            "   Example: PCU325412325412 — Pharmaceutical preparation manufacturing"
        ),
    },
}


# ---------------------------------------------------------------------------
# Helper: build dimension summary lines for one survey
# ---------------------------------------------------------------------------


def _dimension_lines(survey_code: str) -> list[str]:
    """Return formatted lines describing each catalog dimension for a survey."""
    meta = _SURVEY_META.get(survey_code.upper(), {})
    dims = meta.get("catalog_dimensions", [])
    lines = []
    for dim_name, cache_file, description in dims:
        data = catalog.get(survey_code.lower(), dim_name)
        count = len(data)
        lines.append(f"  {dim_name:<12} ({cache_file:<28})  {description}")
        if (
            count
            and count
            != int(
                description.split("~")[-1].split(" ")[0].replace(",", "").rstrip(")")
            )
            if "~" in description
            else True
        ):
            lines[-1] += f"  [{count} codes loaded]"
    return lines


def _flagship_lines(survey_code: str, limit: int = 4) -> list[str]:
    """Return example series ID lines for a survey from the flagship table."""
    entries = [e for e in FLAGSHIP_SERIES if e.survey == survey_code.upper()][:limit]
    if not entries:
        return ["  (no flagship entries for this survey)"]
    lines = []
    for e in entries:
        lines.append(f"  {e.series_id}  —  {e.description}")
        if e.notes:
            lines.append(f"    Note: {e.notes}")
    return lines


# ---------------------------------------------------------------------------
# Resource content builders
# ---------------------------------------------------------------------------


def _build_overview() -> str:
    """Build the bls://surveys/overview resource content."""
    lines = [
        "BLS Time Series Surveys — Supported by this MCP Server",
        "=" * 57,
        "",
        "This server provides access to BLS Public Data API v1 and v2.",
        "Six survey families are fully supported for series ID decoding,",
        "validation, and live data retrieval.",
        "",
        "Supported Survey Prefixes",
        "-" * 25,
    ]

    for prefix, schema in SCHEMAS.items():
        meta = _SURVEY_META.get(prefix, {})
        update_freq = meta.get("update_frequency", "See BLS website")
        dims = meta.get("catalog_dimensions", [])
        dim_names = ", ".join(d[0] for d in dims)
        lines += [
            "",
            f"  {prefix}  —  {schema.survey_name}",
            f"       Series ID length : {schema.total_length} characters",
            f"       Update frequency : {update_freq}",
            f"       Catalog dimensions: {dim_names}",
            "       Supported tools  : lookup_area_code, lookup_industry_code,",
            "                          build_series_id, decode_series_id,",
            "                          validate_series_id, get_series_data",
        ]

    lines += [
        "",
        "",
        "How to Use This Server",
        "-" * 22,
        "",
        "Step 1 — Discover series IDs (no network call needed):",
        "  suggest_series(topic='unemployment rate')     → curated flagship IDs",
        "  search_series(query='Chicago employment')     → local catalog search",
        "  lookup_area_code(query='Chicago')             → area codes for SM/LA",
        "  lookup_industry_code(query='manufacturing')   → industry codes for CE/JT",
        "  build_series_id(survey='CE', ...)             → construct an ID from parts",
        "",
        "Step 2 — Validate and inspect (no network call needed):",
        "  validate_series_id(series_id='...')           → check format + catalog",
        "  decode_series_id(series_id='...')             → human-readable breakdown",
        "  get_series_metadata(series_id='...')          → full local metadata",
        "",
        "Step 3 — Fetch live data (network call to BLS API):",
        "  get_series_data(series_ids=['...'], start_year=2020, end_year=2024)",
        "  → Returns observations with provenance (api_version, as_of, footnotes)",
        "  → Values returned as strings to preserve published precision",
        "  → Footnote 'P' = preliminary estimate; 'R' = revised",
        "",
        "API Version Note",
        "-" * 16,
        "",
        "  v1 (no key): 25 series/request, 10-year range, 25 requests/day",
        "  v2 (BLS_API_KEY set): 50 series/request, 20-year range, 500 requests/day",
        "  v2 also enables: calculations (net/% change), annual averages",
        "  Register at: https://data.bls.gov/registrationEngine/",
        "",
        "For detail on a specific survey, read: bls://surveys/{survey_code}",
        "  e.g. bls://surveys/SM   bls://surveys/CE   bls://surveys/LA",
        "       bls://surveys/JT   bls://surveys/CU   bls://surveys/LN",
    ]
    return "\n".join(lines)


def _build_survey_detail(survey_code: str) -> str:
    """Build the bls://surveys/{survey_code} resource content."""
    sc = survey_code.strip().upper()
    schema = SCHEMAS.get(sc)
    if schema is None:
        supported = ", ".join(sorted(SCHEMAS.keys()))
        return (
            f"Survey '{survey_code}' is not supported by this server.\n"
            f"Supported survey codes: {supported}\n"
            f"Read bls://surveys/overview for the full index."
        )

    meta = _SURVEY_META[sc]
    lines = [
        f"BLS Survey Reference — {sc}: {schema.survey_name}",
        "=" * (24 + len(sc) + len(schema.survey_name)),
        "",
        f"Program      : {meta['program']}",
        f"Series prefix: {sc}",
        f"Series length: {schema.total_length} characters (including 2-char prefix)",
        f"Update freq  : {meta['update_frequency']}",
        "",
        "Series ID Segment Layout",
        "-" * 24,
        f"  Pos 0–1 : '{sc}' (survey prefix, always literal)",
    ]

    offset = 2  # after the prefix
    for seg in schema.segments:
        abs_start = offset + seg.start
        abs_end = abs_start + seg.length - 1
        catalog_note = ""
        if seg.catalog_key:
            data = catalog.get(*seg.catalog_key)
            catalog_note = f"  [{len(data)} codes in catalog]"
        lines.append(
            f"  Pos {abs_start}–{abs_end:<2} : {seg.name:<20} "
            f"({seg.length} char{'s' if seg.length > 1 else ''})  "
            f"— {seg.description}{catalog_note}"
        )

    lines += [
        "",
        "Catalog Dimensions (use lookup tools to find codes)",
        "-" * 51,
    ]
    for dim_name, cache_file, description in meta.get("catalog_dimensions", []):
        data = catalog.get(sc.lower(), dim_name)
        count = len(data)
        lines.append(f"  {dim_name:<12}  {cache_file:<30}  {count} codes")
        lines.append(f"               {description}")
        # Show up to 4 example entries
        sample = list(data.items())[:4]
        if sample:
            lines.append(
                "               Examples: " + ", ".join(f"{k}={v!r}" for k, v in sample)
            )

    # Survey-specific notes
    for note_key in (
        "seasonal_note",
        "unit_note",
        "area_type_note",
        "dataelement_note",
        "periodicity_note",
        "data_api_note",
    ):
        note = meta.get(note_key)
        if note:
            label = note_key.replace("_note", "").replace("_", " ").title()
            lines += ["", f"{label}", "-" * len(label), f"  {note}"]

    lines += [
        "",
        "Example Flagship Series IDs",
        "-" * 28,
    ]
    lines += _flagship_lines(sc, limit=5)

    lines += [
        "",
        "Step-by-Step Usage",
        "-" * 18,
        "",
    ]
    lines += [f"  {line}" for line in meta.get("tool_guidance", "").split("\n")]

    lines += [
        "",
        "For the full survey index: bls://surveys/overview",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP resource registration
# ---------------------------------------------------------------------------


def register(mcp: FastMCP) -> None:
    """Register BLS survey reference resources with the MCP server."""

    @mcp.resource("bls://surveys/overview")
    def surveys_overview() -> str:
        """Index of all BLS surveys supported by this server.

        Returns a structured reference covering every supported survey prefix
        (SM, CE, LA, JT, CU): full name, series ID length, update frequency,
        available catalog dimensions, and the tools used to work with each.

        Read this resource BEFORE calling suggest_series, search_series,
        build_series_id, or get_series_data to understand what surveys exist,
        what dimensions are available locally, and which tools to use.

        For per-survey detail (segment layout, code tables, examples):
          Read bls://surveys/{survey_code}  e.g. bls://surveys/CU
        """
        return _build_overview()

    @mcp.resource("bls://surveys/{survey_code}")
    def survey_detail(survey_code: str) -> str:
        """Detailed reference for one BLS survey.

        Returns the series ID segment layout, all catalog dimensions with
        entry counts and examples, update frequency, seasonal adjustment notes,
        example flagship series IDs, and step-by-step tool usage guidance.

        Args:
            survey_code: Two-letter survey prefix. Supported values:
                SM  — State and Metro Area Employment, Hours, and Earnings
                CE  — Current Employment Statistics (National)
                LA  — Local Area Unemployment Statistics
                JT  — Job Openings and Labor Turnover Survey
                CU  — Consumer Price Index, All Urban Consumers
                LN  — Labor Force Statistics from the Current Population Survey

        For the full survey index: read bls://surveys/overview
        """
        return _build_survey_detail(survey_code)
