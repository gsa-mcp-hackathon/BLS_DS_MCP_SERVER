"""Curated flagship BLS series table.

Provides a shared list of well-known BLS series covering all five supported
surveys (SM, CE, LA, JT, CU).  Used by suggest_series and get_series_metadata.

Usage::

    from example_server.bls_flagship_series import get_flagship, search_flagship

    entry = get_flagship("CUUR0000SA0")   # exact match or None
    hits  = search_flagship("unemployment rate national", limit=5)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FlagshipEntry:
    """A curated BLS series with discovery metadata.

    Attributes:
        series_id:    Exact BLS series ID string.
        survey:       2-char survey prefix ("SM", "CE", "LA", "JT", "CU").
        survey_name:  Human-readable survey name.
        description:  One-line description of the series.
        keywords:     Lowercase strings used for topic matching.
        notes:        Publication notes (frequency, SA status, revisions).
        concept:      Short snake_case label for the economic concept
                      (e.g. "unemployment_rate", "nonfarm_payrolls").
        measure_type: One of "level", "rate", "index", "dollar_amount".
        unit:         BLS publication unit (e.g. "percent",
                      "thousands of persons", "index 1982-84=100").
    """

    series_id: str
    survey: str
    survey_name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    notes: str = ""
    concept: str = ""
    measure_type: str = ""
    unit: str = ""


# ---------------------------------------------------------------------------
# SM — State and Metro Area Employment, Hours, and Earnings
# Format: SM(2)+seasonal(1)+state(2)+area(5)+supersector(2)+industry(6)+datatype(2)
# National total nonfarm: state=00, area=00000, supersector=00, industry=000000
# ---------------------------------------------------------------------------
_SM_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="SMU00000000000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description=(
            "Total Nonfarm Employment — All States, All Areas (Not Seasonally Adjusted)"
        ),
        keywords=["employment", "nonfarm", "total", "national", "sm", "state metro"],
        notes=(
            "Monthly. Not seasonally adjusted. Preliminary estimates revised monthly."
        ),
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="SMU36356200000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description="Total Nonfarm Employment — New York-Newark-Jersey City, NY-NJ-PA",
        keywords=["employment", "nonfarm", "new york", "nyc", "metro", "sm"],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="SMU06310800000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description="Total Nonfarm Employment — Los Angeles-Long Beach-Anaheim, CA",
        keywords=[
            "employment",
            "nonfarm",
            "los angeles",
            "la",
            "california",
            "metro",
            "sm",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="SMU17169800000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description="Total Nonfarm Employment — Chicago-Naperville-Elgin, IL-IN-WI",
        keywords=["employment", "nonfarm", "chicago", "illinois", "metro", "sm"],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="SMU48264200000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description="Total Nonfarm Employment — Houston-The Woodlands-Sugar Land, TX",
        keywords=["employment", "nonfarm", "houston", "texas", "metro", "sm"],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="SMU04380600000000001",
        survey="SM",
        survey_name="State and Metro Area Employment, Hours, and Earnings",
        description="Total Nonfarm Employment — Phoenix-Mesa-Chandler, AZ",
        keywords=["employment", "nonfarm", "phoenix", "arizona", "metro", "sm"],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
]

# ---------------------------------------------------------------------------
# CE — Current Employment Statistics (national payroll survey)
# Format: CE(2)+seasonal(1)+supersector(2)+industry(6)+datatype(2)
# ---------------------------------------------------------------------------
_CE_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="CES0000000001",
        survey="CE",
        survey_name="Current Employment Statistics",
        description="Total Nonfarm Payrolls — Seasonally Adjusted (Thousands)",
        keywords=[
            "employment",
            "nonfarm",
            "payrolls",
            "total",
            "seasonally adjusted",
            "national",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted. Subject to annual benchmark revision.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="CEU0000000001",
        survey="CE",
        survey_name="Current Employment Statistics",
        description="Total Nonfarm Payrolls — Not Seasonally Adjusted (Thousands)",
        keywords=[
            "employment",
            "nonfarm",
            "payrolls",
            "total",
            "not seasonally adjusted",
            "national",
            "ce",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="nonfarm_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="CES0500000001",
        survey="CE",
        survey_name="Current Employment Statistics",
        description="Total Private Payrolls — Seasonally Adjusted (Thousands)",
        keywords=[
            "employment",
            "private",
            "payrolls",
            "seasonally adjusted",
            "national",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="private_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="CES0600000001",
        survey="CE",
        survey_name="Current Employment Statistics",
        description="Goods-Producing Payrolls — Seasonally Adjusted (Thousands)",
        keywords=[
            "employment",
            "goods",
            "goods-producing",
            "manufacturing",
            "seasonally adjusted",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="goods_producing_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="CES0700000001",
        survey="CE",
        survey_name="Current Employment Statistics",
        description="Service-Providing Payrolls — Seasonally Adjusted (Thousands)",
        keywords=[
            "employment",
            "services",
            "service-providing",
            "seasonally adjusted",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="service_payrolls",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="CES0500000003",
        survey="CE",
        survey_name="Current Employment Statistics",
        description=(
            "Average Hourly Earnings of All Employees, Total Private"
            " — Seasonally Adjusted"
        ),
        keywords=[
            "earnings",
            "wages",
            "hourly",
            "average hourly earnings",
            "ahe",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted. One of the Fed's key wage indicators.",
        concept="average_hourly_earnings",
        measure_type="dollar_amount",
        unit="dollars per hour",
    ),
]

# ---------------------------------------------------------------------------
# LA — Local Area Unemployment Statistics
# Format: LA(2)+seasonal(1)+area_code(15)+measure(2)
# area_code for states: ST + 2-digit FIPS + 11 zeros  (e.g. ST0100000000000 = Alabama)
# national: ST0000000000000 ... actually BLS uses "US000000000000" (14 chars) —
# BLS national rate series is "LAUST000000000000003" (seasonal)
# / "LAONST000000000000003" —
# Verified known IDs:
#   LAUST000000000000003 = national unemployment rate SA (U-3)
#   LAUNT000000000000003 = national unemployment rate NSA
# ---------------------------------------------------------------------------
_LA_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="LAUST000000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="National Unemployment Rate — Seasonally Adjusted (U-3)",
        keywords=[
            "unemployment",
            "rate",
            "national",
            "seasonally adjusted",
            "u-3",
            "la",
            "laus",
        ],
        notes="Monthly. Seasonally adjusted. The headline U-3 unemployment rate.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUNT000000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="National Unemployment Rate — Not Seasonally Adjusted (U-3)",
        keywords=[
            "unemployment",
            "rate",
            "national",
            "not seasonally adjusted",
            "u-3",
            "la",
            "laus",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUST060000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="California Unemployment Rate — Seasonally Adjusted",
        keywords=["unemployment", "rate", "california", "ca", "state", "la", "laus"],
        notes="Monthly. Seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUST480000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="Texas Unemployment Rate — Seasonally Adjusted",
        keywords=["unemployment", "rate", "texas", "tx", "state", "la", "laus"],
        notes="Monthly. Seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUST360000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="New York Unemployment Rate — Seasonally Adjusted",
        keywords=["unemployment", "rate", "new york", "ny", "state", "la", "laus"],
        notes="Monthly. Seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUST170000000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description="Illinois Unemployment Rate — Seasonally Adjusted",
        keywords=["unemployment", "rate", "illinois", "il", "state", "la", "laus"],
        notes="Monthly. Seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LAUMT171698000000003",
        survey="LA",
        survey_name="Local Area Unemployment Statistics",
        description=(
            "Chicago-Naperville-Elgin, IL-IN-WI Metro Unemployment Rate"
            " (Not Seasonally Adjusted)"
        ),
        keywords=["unemployment", "rate", "chicago", "illinois", "metro", "la", "laus"],
        notes="Monthly. Not seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
]

# ---------------------------------------------------------------------------
# JT — Job Openings and Labor Turnover Survey (JOLTS)
# Format: JT(2)+seasonal(1)+state(2)+industry(6)+sizeclass(2)
#         +dataelement(2)+ratelevel(1)
# National, all industries: state=00, industry=000000, sizeclass=00
# ---------------------------------------------------------------------------
_JT_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="JTS000000000000001",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Total Job Openings — All Industries, All Areas"
            " (Level, Thousands, Seasonally Adjusted)"
        ),
        keywords=[
            "job openings",
            "openings",
            "jolts",
            "total",
            "seasonally adjusted",
            "jt",
        ],
        notes="Monthly. Seasonally adjusted. Released ~5 weeks after reference month.",
        concept="job_openings",
        measure_type="level",
        unit="thousands of jobs",
    ),
    FlagshipEntry(
        series_id="JTS000000000000HIL",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Total Hires — All Industries, All Areas"
            " (Level, Thousands, Seasonally Adjusted)"
        ),
        keywords=["hires", "hiring", "jolts", "total", "seasonally adjusted", "jt"],
        notes="Monthly. Seasonally adjusted.",
        concept="hires",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="JTS000000000000QUL",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Total Quits — All Industries, All Areas"
            " (Level, Thousands, Seasonally Adjusted)"
        ),
        keywords=[
            "quits",
            "quit rate",
            "jolts",
            "total",
            "voluntary separations",
            "jt",
        ],
        notes="Monthly. Seasonally adjusted. Key measure of voluntary turnover.",
        concept="quits",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="JTS000000000000LDL",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Total Layoffs and Discharges — All Industries"
            " (Level, Thousands, Seasonally Adjusted)"
        ),
        keywords=["layoffs", "discharges", "separations", "jolts", "jt"],
        notes="Monthly. Seasonally adjusted.",
        concept="layoffs_and_discharges",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="JTS000000000000OSL",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Total Other Separations — All Industries"
            " (Level, Thousands, Seasonally Adjusted)"
        ),
        keywords=["separations", "other separations", "jolts", "jt"],
        notes="Monthly. Seasonally adjusted.",
        concept="other_separations",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="JTS000000000000JOR",
        survey="JT",
        survey_name="Job Openings and Labor Turnover Survey",
        description=(
            "Job Openings Rate — All Industries, All Areas (Seasonally Adjusted)"
        ),
        keywords=["job openings rate", "openings rate", "jolts", "rate", "jt"],
        notes=(
            "Monthly. Seasonally adjusted."
            " Rate = job openings / (employment + openings)."
        ),
        concept="job_openings_rate",
        measure_type="rate",
        unit="percent",
    ),
]

# ---------------------------------------------------------------------------
# CU — Consumer Price Index — All Urban Consumers
# Format: CU(2)+seasonal(1)+periodicity(1)+area(4)+item(8)
# U.S. city average: area=0000, periodicity=R (monthly)
# ---------------------------------------------------------------------------
_CU_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="CUUR0000SA0",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description="CPI-U All Items — U.S. City Average (Not Seasonally Adjusted)",
        keywords=[
            "cpi",
            "inflation",
            "consumer price",
            "all items",
            "not seasonally adjusted",
            "cu",
            "cpi-u",
        ],
        notes="Monthly. Not seasonally adjusted. Primary reference series for CPI.",
        concept="cpi_all_items",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CUSR0000SA0",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description="CPI-U All Items — U.S. City Average (Seasonally Adjusted)",
        keywords=[
            "cpi",
            "inflation",
            "consumer price",
            "all items",
            "seasonally adjusted",
            "cu",
            "cpi-u",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="cpi_all_items",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CUUR0000SAF1",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description="CPI-U Food — U.S. City Average (Not Seasonally Adjusted)",
        keywords=["cpi", "food", "grocery", "consumer price", "inflation", "cu"],
        notes="Monthly. Not seasonally adjusted.",
        concept="cpi_food",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CUUR0000SA0E",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description="CPI-U Energy — U.S. City Average (Not Seasonally Adjusted)",
        keywords=[
            "cpi",
            "energy",
            "gas",
            "electricity",
            "consumer price",
            "inflation",
            "cu",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="cpi_energy",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CUUR0000SA0L1E",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description=(
            "CPI-U All Items Less Food and Energy (Core CPI)"
            " — U.S. City Average (Not Seasonally Adjusted)"
        ),
        keywords=[
            "cpi",
            "core cpi",
            "core inflation",
            "less food energy",
            "consumer price",
            "cu",
        ],
        notes=(
            "Monthly. Not seasonally adjusted."
            " Core CPI excludes volatile food and energy."
        ),
        concept="cpi_core",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWUR0000SA0",
        survey="CU",
        survey_name="Consumer Price Index — Urban Wage Earners and Clerical Workers",
        description="CPI-W All Items — U.S. City Average (Not Seasonally Adjusted)",
        keywords=["cpi-w", "cpi", "wage earners", "urban wage", "consumer price", "cu"],
        notes="Monthly. Not seasonally adjusted. Used to adjust Social Security COLA.",
        concept="cpi_all_items",
        measure_type="index",
        unit="index 1982-84=100",
    ),
]

# Master list — all entries across all five surveys.
FLAGSHIP_SERIES: list[FlagshipEntry] = (
    _SM_ENTRIES + _CE_ENTRIES + _LA_ENTRIES + _JT_ENTRIES + _CU_ENTRIES
)

# Quick lookup index by series ID.
_BY_ID: dict[str, FlagshipEntry] = {e.series_id: e for e in FLAGSHIP_SERIES}


def get_flagship(series_id: str) -> FlagshipEntry | None:
    """Return the flagship entry for an exact series ID match, or None."""
    return _BY_ID.get(series_id.strip().upper())


def search_flagship(topic: str, limit: int = 10) -> list[FlagshipEntry]:
    """Case-insensitive keyword search across description, keywords, and survey_name.

    Results are ranked by number of matched topic words (descending).
    """
    words = topic.lower().split()
    if not words:
        return FLAGSHIP_SERIES[:limit]

    scored: list[tuple[int, FlagshipEntry]] = []
    for entry in FLAGSHIP_SERIES:
        haystack = (
            " ".join(entry.keywords)
            + " "
            + entry.description.lower()
            + " "
            + entry.survey_name.lower()
        )
        score = sum(1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:limit]]
