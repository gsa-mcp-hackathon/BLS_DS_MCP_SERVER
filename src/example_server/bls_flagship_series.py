"""Curated flagship BLS series table.

Provides a shared list of well-known BLS series covering all twelve supported
surveys (SM, CE, LA, JT, CU, LN, PR, MP, CW, WP, EI, CI).
Used by suggest_series and get_series_metadata.

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
        survey:       2-char survey prefix
                      ("SM", "CE", "LA", "JT", "CU", "LN",
                       "PR", "MP", "CW", "WP", "EI", "CI").
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
    FlagshipEntry(
        series_id="CES0500000002",
        survey="CE",
        survey_name="Current Employment Statistics",
        description=(
            "Average Weekly Hours of All Employees, Total Private — Seasonally Adjusted"
        ),
        keywords=[
            "weekly hours",
            "hours worked",
            "average weekly hours",
            "awh",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="avg_weekly_hours_all_employees",
        measure_type="level",
        unit="hours",
    ),
    FlagshipEntry(
        series_id="CES0500000007",
        survey="CE",
        survey_name="Current Employment Statistics",
        description=(
            "Average Weekly Hours of Production and Nonsupervisory Employees,"
            " Total Private — Seasonally Adjusted"
        ),
        keywords=[
            "weekly hours",
            "production workers",
            "nonsupervisory",
            "average weekly hours",
            "awh",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="avg_weekly_hours_prod_nonsup",
        measure_type="level",
        unit="hours",
    ),
    FlagshipEntry(
        series_id="CES0500000008",
        survey="CE",
        survey_name="Current Employment Statistics",
        description=(
            "Average Hourly Earnings of Production and Nonsupervisory Employees,"
            " Total Private — Seasonally Adjusted"
        ),
        keywords=[
            "earnings",
            "wages",
            "production workers",
            "nonsupervisory",
            "average hourly earnings",
            "ce",
        ],
        notes="Monthly. Seasonally adjusted.",
        concept="avg_hourly_earnings_prod_nonsup",
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
        series_id="CUUR0000AA0",
        survey="CU",
        survey_name="Consumer Price Index — All Urban Consumers",
        description=(
            "CPI-U All Items — U.S. City Average, 1967=100 (Not Seasonally Adjusted)"
        ),
        keywords=[
            "cpi",
            "cpi-u",
            "inflation",
            "consumer price",
            "all items",
            "1967 base",
            "cu",
        ],
        notes=(
            "Monthly. Not seasonally adjusted. Alternate base period series (1967=100)."
        ),
        concept="cpi_all_items_1967base",
        measure_type="index",
        unit="index 1967=100",
    ),
]

# ---------------------------------------------------------------------------
# LN — Labor Force Statistics from the Current Population Survey (CPS)
# Series IDs are opaque; only LNS (SA) / LNU (NSA) prefix is structural.
# ---------------------------------------------------------------------------
_LN_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="LNS11300000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Labor Force Participation Rate — Seasonally Adjusted",
        keywords=[
            "labor force participation rate",
            "participation rate",
            "labor force",
            "lfpr",
            "cps",
            "ln",
        ],
        notes=(
            "Monthly. Seasonally adjusted."
            " Percent of civilian noninstitutional population 16+ in the labor force."
        ),
        concept="labor_force_participation_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LNU01300000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Labor Force Participation Rate — Not Seasonally Adjusted",
        keywords=[
            "labor force participation rate",
            "participation rate",
            "labor force",
            "lfpr",
            "not seasonally adjusted",
            "cps",
            "ln",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="labor_force_participation_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LNS14000000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description=(
            "Unemployment Rate (U-3) — Seasonally Adjusted (CPS Household Survey)"
        ),
        keywords=[
            "unemployment rate",
            "u-3",
            "cps",
            "household survey",
            "seasonally adjusted",
            "ln",
        ],
        notes=(
            "Monthly. Seasonally adjusted. CPS-based U-3 unemployment rate."
            " Published alongside the payroll survey in the Employment Situation"
            " release."
        ),
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LNU04000000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description=(
            "Unemployment Rate (U-3) — Not Seasonally Adjusted (CPS Household Survey)"
        ),
        keywords=[
            "unemployment rate",
            "u-3",
            "cps",
            "household survey",
            "not seasonally adjusted",
            "ln",
        ],
        notes="Monthly. Not seasonally adjusted.",
        concept="unemployment_rate",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LNS12300000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Employment-Population Ratio — Seasonally Adjusted",
        keywords=[
            "employment population ratio",
            "employment rate",
            "epop",
            "e-pop",
            "cps",
            "ln",
        ],
        notes=(
            "Monthly. Seasonally adjusted."
            " Employed persons as percent of civilian noninstitutional population 16+."
        ),
        concept="employment_population_ratio",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="LNS12000000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Civilian Employment Level — Seasonally Adjusted",
        keywords=[
            "civilian employment",
            "employment level",
            "employed",
            "cps",
            "household survey",
            "ln",
        ],
        notes=(
            "Monthly. Seasonally adjusted."
            " Number of employed persons from the household survey (thousands)."
        ),
        concept="civilian_employment",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="LNS11000000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Civilian Labor Force Level — Seasonally Adjusted",
        keywords=[
            "civilian labor force",
            "labor force level",
            "labor force size",
            "cps",
            "ln",
        ],
        notes="Monthly. Seasonally adjusted. Total civilian labor force (thousands).",
        concept="civilian_labor_force",
        measure_type="level",
        unit="thousands of persons",
    ),
    FlagshipEntry(
        series_id="LNS13000000",
        survey="LN",
        survey_name="Labor Force Statistics from the Current Population Survey",
        description="Civilian Unemployment Level — Seasonally Adjusted",
        keywords=[
            "civilian unemployment",
            "unemployment level",
            "unemployed persons",
            "cps",
            "household survey",
            "ln",
        ],
        notes=(
            "Monthly. Seasonally adjusted."
            " Number of unemployed persons from the household survey (thousands)."
        ),
        concept="civilian_unemployment",
        measure_type="level",
        unit="thousands of persons",
    ),
]

# ---------------------------------------------------------------------------
# PR — Productivity and Costs
# Format: PR(2)+seasonal(1)+sector(4)+class(1)+measure(2)+duration(1) = 11 chars
# Nonfarm business: sector=8500; Manufacturing: sector=3000; class=6 (index series)
# ---------------------------------------------------------------------------

_PR_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="PRS30006013",
        survey="PR",
        survey_name="Productivity and Costs",
        description="Employment for the Manufacturing sector, Index (2017=100)",
        keywords=[
            "manufacturing",
            "employment",
            "productivity",
            "index",
            "labor",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 3000 = Manufacturing. "
            "Base year 2017=100."
        ),
        concept="manufacturing_employment_index",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="PRS30006014",
        survey="PR",
        survey_name="Productivity and Costs",
        description="Employment for the Manufacturing sector, Level (Millions of jobs)",
        keywords=[
            "manufacturing",
            "employment",
            "level",
            "jobs",
            "labor",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 3000 = Manufacturing. "
            "Unit: millions of jobs."
        ),
        concept="manufacturing_employment_level",
        measure_type="level",
        unit="millions of jobs",
    ),
    FlagshipEntry(
        series_id="PRS85006093",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Labor productivity for the Nonfarm business sector, Index (2017=100)"
        ),
        keywords=[
            "nonfarm business",
            "labor productivity",
            "productivity",
            "output per hour",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business. "
            "Base year 2017=100. Key headline productivity measure."
        ),
        concept="nonfarm_business_labor_productivity_index",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="PRS85006014",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Employment for the Nonfarm business sector, Level (Millions of jobs)"
        ),
        keywords=[
            "nonfarm business",
            "employment",
            "level",
            "jobs",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business. "
            "Unit: millions of jobs."
        ),
        concept="nonfarm_business_employment_level",
        measure_type="level",
        unit="millions of jobs",
    ),
    FlagshipEntry(
        series_id="PRS85006113",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Unit labor costs for the Nonfarm business sector, Index (2017=100)"
        ),
        keywords=[
            "nonfarm business",
            "unit labor costs",
            "ulc",
            "labor costs",
            "index",
            "inflation",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business. "
            "Base year 2017=100. Key indicator of cost-push inflation."
        ),
        concept="nonfarm_business_unit_labor_costs",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="PRS85006104",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Hourly compensation for the Nonfarm business sector, "
            "Level (Current dollars per hour worked)"
        ),
        keywords=[
            "nonfarm business",
            "hourly compensation",
            "compensation per hour",
            "wages",
            "dollars",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business. "
            "Unit: current dollars per hour worked."
        ),
        concept="nonfarm_business_hourly_compensation",
        measure_type="dollar_amount",
        unit="dollars per hour",
    ),
    FlagshipEntry(
        series_id="PRS30006093",
        survey="PR",
        survey_name="Productivity and Costs",
        description="Labor productivity for the Manufacturing sector, Index (2017=100)",
        keywords=[
            "manufacturing",
            "labor productivity",
            "productivity",
            "output per hour",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 3000 = Manufacturing. "
            "Base year 2017=100."
        ),
        concept="manufacturing_labor_productivity_index",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="PRS30006113",
        survey="PR",
        survey_name="Productivity and Costs",
        description="Unit labor costs for the Manufacturing sector, Index (2017=100)",
        keywords=[
            "manufacturing",
            "unit labor costs",
            "ulc",
            "labor costs",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 3000 = Manufacturing. "
            "Base year 2017=100."
        ),
        concept="manufacturing_unit_labor_costs",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="PRS85006092",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Labor productivity for the Nonfarm business sector,"
            " Percent change from previous quarter"
        ),
        keywords=[
            "nonfarm business",
            "labor productivity",
            "output per hour",
            "percent change",
            "productivity",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business."
            " Measure 09 = labor productivity. Duration 2 = % chg from prev quarter."
        ),
        concept="nonfarm_business_labor_productivity_pct_change",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="PRS85006112",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Unit labor costs for the Nonfarm business sector,"
            " Percent change from previous quarter"
        ),
        keywords=[
            "nonfarm business",
            "unit labor costs",
            "ulc",
            "percent change",
            "inflation",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business."
            " Measure 11 = unit labor costs. Duration 2 = % chg from prev quarter."
        ),
        concept="nonfarm_business_unit_labor_costs_pct_change",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="PRS85006152",
        survey="PR",
        survey_name="Productivity and Costs",
        description=(
            "Real hourly compensation for the Nonfarm business sector,"
            " Percent change from previous quarter"
        ),
        keywords=[
            "nonfarm business",
            "real hourly compensation",
            "compensation",
            "percent change",
        ],
        notes=(
            "Quarterly, seasonally adjusted. Sector 8500 = Nonfarm business."
            " Measure 15 = real hourly compensation."
            " Duration 2 = % chg from prev quarter."
        ),
        concept="nonfarm_business_real_hourly_compensation_pct_change",
        measure_type="rate",
        unit="percent",
    ),
]

# ---------------------------------------------------------------------------
# MP — Multifactor Productivity
# Format: MP(2)+seasonal(1)+sector(4)+measure(2)+duration(1) = 10 chars
# All TFP index series use measure=01, duration=2, seasonal=U, base year 2017
# ---------------------------------------------------------------------------

_MP_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="MPU0011012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=(
            "Total factor productivity for Agriculture, forestry, fishing, "
            "and hunting (NAICS 11), Indexes"
        ),
        keywords=[
            "agriculture",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=(
            "Annual, not seasonally adjusted. NAICS 11. Base year 2017=100. "
            "Covers capital, labor, energy, materials, and services inputs."
        ),
        concept="tfp_agriculture",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU0021012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=("Total factor productivity for Mining (NAICS 21), Indexes"),
        keywords=[
            "mining",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=("Annual, not seasonally adjusted. NAICS 21. Base year 2017=100."),
        concept="tfp_mining",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU0022012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description="Total factor productivity for Utilities (NAICS 22), Indexes",
        keywords=[
            "utilities",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=("Annual, not seasonally adjusted. NAICS 22. Base year 2017=100."),
        concept="tfp_utilities",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU0023012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description="Total factor productivity for Construction (NAICS 23), Indexes",
        keywords=[
            "construction",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=("Annual, not seasonally adjusted. NAICS 23. Base year 2017=100."),
        concept="tfp_construction",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU9920012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=(
            "Total factor productivity for Durable Manufacturing Sector "
            "(NAICS 321 327 331-337 339), Indexes"
        ),
        keywords=[
            "durable manufacturing",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
            "durable goods",
        ],
        notes=("Annual, not seasonally adjusted. Durable mfg. Base year 2017=100."),
        concept="tfp_durable_manufacturing",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU9910012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=(
            "Total factor productivity for Nondurable Manufacturing Sector "
            "(NAICS 311-316 322-326), Indexes"
        ),
        keywords=[
            "nondurable manufacturing",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
            "nondurable goods",
        ],
        notes=("Annual, not seasonally adjusted. Nondurable mfg. Base year 2017=100."),
        concept="tfp_nondurable_manufacturing",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU4910012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=(
            "Total factor productivity for Private Nonfarm Business Sector"
            " (NAICS 113-81), annual index"
        ),
        keywords=[
            "private nonfarm business",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=(
            "Annual, not seasonally adjusted. Sector 4910 = Private Nonfarm Business"
            " (NAICS XG). Base year 2017=100."
        ),
        concept="tfp_private_nonfarm_business",
        measure_type="index",
        unit="index 2017=100",
    ),
    FlagshipEntry(
        series_id="MPU4900012",
        survey="MP",
        survey_name="Multifactor Productivity",
        description=(
            "Total factor productivity for Private Business Sector"
            " (NAICS 11-81), annual index"
        ),
        keywords=[
            "private business",
            "total factor productivity",
            "tfp",
            "multifactor productivity",
            "mfp",
            "index",
        ],
        notes=(
            "Annual, not seasonally adjusted. Sector 4900 = Private Business"
            " (NAICS PG). Base year 2017=100."
        ),
        concept="tfp_private_business",
        measure_type="index",
        unit="index 2017=100",
    ),
]

# ---------------------------------------------------------------------------
# CW — Consumer Price Index — Urban Wage Earners and Clerical Workers (CPI-W)
# Format: CW(2)+seasonal(1)+periodicity(1)+area(4)+item(variable) = variable length
# U.S. city average: area=0000; seasonally adjusted: seasonal=S, periodicity=R
# ---------------------------------------------------------------------------

_CW_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="CWSR0000SA0",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "All items in U.S. city average, urban wage earners and clerical "
            "workers, seasonally adjusted"
        ),
        keywords=[
            "cpi-w",
            "cpi w",
            "all items",
            "urban wage earners",
            "clerical workers",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average (area 0000). "
            "Base period 1982-84=100. Used for Social Security COLA adjustments."
        ),
        concept="cpiw_all_items_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWSR0000SAF1",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "Food at home in U.S. city average, urban wage earners and "
            "clerical workers, seasonally adjusted"
        ),
        keywords=[
            "cpi-w",
            "food at home",
            "groceries",
            "urban wage earners",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average. Base period 1982-84=100."
        ),
        concept="cpiw_food_at_home_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWSR0000SA0E",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "Energy in U.S. city average, urban wage earners and clerical "
            "workers, seasonally adjusted"
        ),
        keywords=[
            "cpi-w",
            "energy",
            "urban wage earners",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average. Base period 1982-84=100."
        ),
        concept="cpiw_energy_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWSR0000SAF",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "Food and beverages in U.S. city average, urban wage earners "
            "and clerical workers, seasonally adjusted"
        ),
        keywords=[
            "cpi-w",
            "food",
            "food and beverages",
            "urban wage earners",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average. Base period 1982-84=100."
        ),
        concept="cpiw_food_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWSR0000SA0L1E",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "All items less food and energy in U.S. city average, urban wage "
            "earners and clerical workers, seasonally adjusted (core CPI-W)"
        ),
        keywords=[
            "cpi-w",
            "core",
            "less food and energy",
            "urban wage earners",
            "inflation",
            "seasonally adjusted",
            "core inflation",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average. "
            "Base period 1982-84=100. Core CPI-W excluding food and energy."
        ),
        concept="cpiw_core_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWSR0000SAH1",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "Shelter in U.S. city average, urban wage earners and clerical "
            "workers, seasonally adjusted"
        ),
        keywords=[
            "cpi-w",
            "shelter",
            "housing",
            "rent",
            "urban wage earners",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. U.S. city average. Base period 1982-84=100."
        ),
        concept="cpiw_shelter_sa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWUR0000SA0",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description="CPI-W All Items — U.S. City Average (Not Seasonally Adjusted)",
        keywords=[
            "cpi-w",
            "cpi",
            "wage earners",
            "urban wage",
            "consumer price",
            "cw",
        ],
        notes=(
            "Monthly. Not seasonally adjusted. Used to adjust Social Security COLA."
        ),
        concept="cpiw_all_items_nsa",
        measure_type="index",
        unit="index 1982-84=100",
    ),
    FlagshipEntry(
        series_id="CWUR0000SA0L1E",
        survey="CW",
        survey_name=(
            "Consumer Price Index \u2014 Urban Wage Earners and Clerical Workers"
        ),
        description=(
            "CPI-W All Items Less Food and Energy (Core CPI-W)"
            " — U.S. City Average (Not Seasonally Adjusted)"
        ),
        keywords=[
            "cpi-w",
            "core",
            "core cpi-w",
            "less food and energy",
            "urban wage earners",
            "inflation",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly. Not seasonally adjusted. U.S. city average."
            " Base period 1982-84=100. Core CPI-W excluding food and energy."
        ),
        concept="cpiw_core",
        measure_type="index",
        unit="index 1982-84=100",
    ),
]

# ---------------------------------------------------------------------------
# WP — PPI Commodity Data
# Format: WP(2)+seasonal(1)+series_code(variable) = variable length
# Seasonally adjusted prefix: WPS; not seasonally adjusted: WPU
# ---------------------------------------------------------------------------

_WP_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="WPS00000000",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Commodity data for All commodities, seasonally adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "all commodities",
            "commodity",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. All commodities aggregate. "
            "Base period 1982=100. Headline commodity PPI."
        ),
        concept="ppi_all_commodities_sa",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPU00000000",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Commodity data for All commodities, not seasonally adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "all commodities",
            "commodity",
            "inflation",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. All commodities aggregate. "
            "Base period 1982=100. Goes back to 1913."
        ),
        concept="ppi_all_commodities_nsa",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPU01",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Commodity data for Farm products, not seasonally adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "farm products",
            "agriculture",
            "commodity",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Farm products group. "
            "Base period 1982=100."
        ),
        concept="ppi_farm_products",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPS029",
        survey="WP",
        survey_name="PPI Commodity Data",
        description=(
            "PPI Commodity data for Processed foods and feeds — "
            "Prepared animal feeds, seasonally adjusted"
        ),
        keywords=[
            "ppi",
            "processed foods",
            "feeds",
            "food",
            "commodity",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. Processed foods and feeds group. "
            "Base period 1982=100."
        ),
        concept="ppi_processed_foods_feeds",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPS05",
        survey="WP",
        survey_name="PPI Commodity Data",
        description=(
            "PPI Commodity data for Fuels and related products and power, "
            "seasonally adjusted"
        ),
        keywords=[
            "ppi",
            "fuels",
            "energy",
            "power",
            "petroleum",
            "commodity",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. Fuels and related products group. "
            "Base period 1982=100."
        ),
        concept="ppi_fuels_and_power",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPS101",
        survey="WP",
        survey_name="PPI Commodity Data",
        description=(
            "PPI Commodity data for Metals and metal products — "
            "Iron and steel, seasonally adjusted"
        ),
        keywords=[
            "ppi",
            "metals",
            "iron",
            "steel",
            "metal products",
            "commodity",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. Iron and steel sub-group of metals. "
            "Base period 1982=100."
        ),
        concept="ppi_iron_and_steel",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPS102",
        survey="WP",
        survey_name="PPI Commodity Data",
        description=(
            "PPI Commodity data for Metals and metal products — "
            "Nonferrous metals, seasonally adjusted"
        ),
        keywords=[
            "ppi",
            "metals",
            "nonferrous",
            "aluminum",
            "copper",
            "metal products",
            "commodity",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. Nonferrous metals sub-group. "
            "Base period 1982=100."
        ),
        concept="ppi_nonferrous_metals",
        measure_type="index",
        unit="index 1982=100",
    ),
    FlagshipEntry(
        series_id="WPSFD4",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Final Demand — Seasonally Adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "final demand",
            "inflation",
            "seasonally adjusted",
        ],
        notes=(
            "Monthly, seasonally adjusted. BLS Final Demand-Intermediate Demand"
            " system (introduced 2014). Base period November 2009=100."
        ),
        concept="ppi_final_demand_sa",
        measure_type="index",
        unit="index 2009=100",
    ),
    FlagshipEntry(
        series_id="WPUFD4",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Final Demand — Not Seasonally Adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "final demand",
            "inflation",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. BLS Final Demand-Intermediate"
            " Demand system. Base period November 2009=100."
        ),
        concept="ppi_final_demand_nsa",
        measure_type="index",
        unit="index 2009=100",
    ),
    FlagshipEntry(
        series_id="WPUFD49104",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Final Demand Less Foods and Energy — Not Seasonally Adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "final demand",
            "core ppi",
            "less food",
            "less energy",
            "inflation",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Final demand ex-food and energy."
            " Base period November 2009=100."
        ),
        concept="ppi_final_demand_less_food_energy",
        measure_type="index",
        unit="index 2009=100",
    ),
    FlagshipEntry(
        series_id="WPUFD49116",
        survey="WP",
        survey_name="PPI Commodity Data",
        description=(
            "PPI Final Demand Less Foods, Energy, and Trade Services"
            " — Not Seasonally Adjusted"
        ),
        keywords=[
            "ppi",
            "producer price index",
            "final demand",
            "core ppi",
            "less food energy trade",
            "inflation",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Final demand ex-food, energy, and"
            " trade services. Base period November 2009=100."
        ),
        concept="ppi_final_demand_less_food_energy_trade",
        measure_type="index",
        unit="index 2009=100",
    ),
    FlagshipEntry(
        series_id="WPUFD49207",
        survey="WP",
        survey_name="PPI Commodity Data",
        description="PPI Finished Goods, 1982=100 — Not Seasonally Adjusted",
        keywords=[
            "ppi",
            "producer price index",
            "finished goods",
            "commodity",
            "inflation",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Traditional finished goods PPI."
            " Base period 1982=100."
        ),
        concept="ppi_finished_goods",
        measure_type="index",
        unit="index 1982=100",
    ),
]

# ---------------------------------------------------------------------------
# EI — International Price Program
# Format: EI(2)+seasonal(1)+index_code(2)+series_code(variable) = variable length
# All series are not seasonally adjusted (seasonal=U).
# IR = import prices by BEA end use; IQ = export prices by BEA end use
# CO = import prices by country of origin; CD = export prices by destination
# ---------------------------------------------------------------------------

_EI_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="EIUIR",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly import price index for BEA End Use, All commodities, "
            "not seasonally adjusted"
        ),
        keywords=[
            "import price",
            "import prices",
            "international price",
            "all commodities",
            "trade",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Total import price index. "
            "Base period 2000=100. Goes back to September 1982."
        ),
        concept="total_import_price_index",
        measure_type="index",
        unit="index 2000=100",
    ),
    FlagshipEntry(
        series_id="EIUIQ",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly export price index for BEA End Use, All commodities, "
            "not seasonally adjusted"
        ),
        keywords=[
            "export price",
            "export prices",
            "international price",
            "all commodities",
            "trade",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Total export price index. "
            "Base period 2000=100. Goes back to September 1983."
        ),
        concept="total_export_price_index",
        measure_type="index",
        unit="index 2000=100",
    ),
    FlagshipEntry(
        series_id="EIUIR1",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly import price index for BEA End Use 1, "
            "Industrial supplies and materials, not seasonally adjusted"
        ),
        keywords=[
            "import price",
            "industrial supplies",
            "materials",
            "international price",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Import prices for industrial "
            "supplies and materials. Base period 2000=100."
        ),
        concept="import_price_industrial_supplies",
        measure_type="index",
        unit="index 2000=100",
    ),
    FlagshipEntry(
        series_id="EIUIR2",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly import price index for BEA End Use 2, "
            "Capital goods, except automotive, not seasonally adjusted"
        ),
        keywords=[
            "import price",
            "capital goods",
            "machinery",
            "international price",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Import prices for capital goods "
            "excluding automotive. Base period 2000=100."
        ),
        concept="import_price_capital_goods",
        measure_type="index",
        unit="index 2000=100",
    ),
    FlagshipEntry(
        series_id="EIUIQ1",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly export price index for BEA End Use 1, "
            "Industrial supplies and materials, not seasonally adjusted"
        ),
        keywords=[
            "export price",
            "industrial supplies",
            "materials",
            "international price",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Export prices for industrial "
            "supplies and materials. Base period 2000=100."
        ),
        concept="export_price_industrial_supplies",
        measure_type="index",
        unit="index 2000=100",
    ),
    FlagshipEntry(
        series_id="EIUIQ2",
        survey="EI",
        survey_name="International Price Program",
        description=(
            "Monthly export price index for BEA End Use 2, "
            "Capital goods, except automotive, not seasonally adjusted"
        ),
        keywords=[
            "export price",
            "capital goods",
            "machinery",
            "international price",
            "not seasonally adjusted",
        ],
        notes=(
            "Monthly, not seasonally adjusted. Export prices for capital goods "
            "excluding automotive. Base period 2000=100."
        ),
        concept="export_price_capital_goods",
        measure_type="index",
        unit="index 2000=100",
    ),
]

# ---------------------------------------------------------------------------
# CI — Employer Costs for Employee Compensation (ECEC)
# Format: CI(2)+seasonal(1)+owner(1)+industry(6)+occupation(6)+subcell(2)+
#         periodicity(1) = 17 chars
# Civilian workers: owner=1; Private industry: owner=2; State/local govt: owner=3
# All industries/occupations: 000000; periodicity I=index, Q=3-month % change
# ---------------------------------------------------------------------------

_CI_ENTRIES: list[FlagshipEntry] = [
    FlagshipEntry(
        series_id="CIS1010000000000I",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "Total compensation for all civilian workers, current dollar index"
        ),
        keywords=[
            "total compensation",
            "civilian workers",
            "employer costs",
            "ecec",
            "compensation",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All civilian workers, all "
            "industries, all occupations. Current dollar index. "
            "Owner=1 (civilian)."
        ),
        concept="total_compensation_civilian_index",
        measure_type="index",
        unit="index",
    ),
    FlagshipEntry(
        series_id="CIS1010000000000Q",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "Total compensation for all civilian workers, "
            "3-month percent change, current dollars"
        ),
        keywords=[
            "total compensation",
            "civilian workers",
            "employer costs",
            "ecec",
            "compensation",
            "percent change",
            "rate",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All civilian workers. "
            "3-month percent change. Owner=1 (civilian)."
        ),
        concept="total_compensation_civilian_pct_change",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="CIS1020000000000I",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "Wages and salaries for all civilian workers, current dollar index"
        ),
        keywords=[
            "wages",
            "salaries",
            "civilian workers",
            "employer costs",
            "ecec",
            "compensation",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All civilian workers. "
            "Wages and salaries component. Current dollar index."
        ),
        concept="wages_salaries_civilian_index",
        measure_type="index",
        unit="index",
    ),
    FlagshipEntry(
        series_id="CIS1030000000000I",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=("Total benefits for all civilian workers, current dollar index"),
        keywords=[
            "benefits",
            "total benefits",
            "civilian workers",
            "employer costs",
            "ecec",
            "compensation",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All civilian workers. "
            "Total benefits component (health, retirement, etc.)."
        ),
        concept="total_benefits_civilian_index",
        measure_type="index",
        unit="index",
    ),
    FlagshipEntry(
        series_id="CIS2010000000000I",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "Total compensation for all private industry workers, current dollar index"
        ),
        keywords=[
            "total compensation",
            "private industry",
            "private sector",
            "employer costs",
            "ecec",
            "compensation",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All private industry workers. "
            "Current dollar index. Owner=2 (private industry)."
        ),
        concept="total_compensation_private_index",
        measure_type="index",
        unit="index",
    ),
    FlagshipEntry(
        series_id="CIS3010000000000I",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "Total compensation for all state and local government workers, "
            "current dollar index"
        ),
        keywords=[
            "total compensation",
            "state and local government",
            "government workers",
            "employer costs",
            "ecec",
            "compensation",
            "index",
        ],
        notes=(
            "Quarterly, seasonally adjusted. All state and local government "
            "workers. Current dollar index. Owner=3 (state/local govt)."
        ),
        concept="total_compensation_state_local_index",
        measure_type="index",
        unit="index",
    ),
    FlagshipEntry(
        series_id="CIU1010000000000A",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "ECI Total Compensation, All Civilian Workers"
            " — 12-month percent change (Unadjusted)"
        ),
        keywords=[
            "eci",
            "employment cost index",
            "total compensation",
            "civilian workers",
            "12-month percent change",
            "compensation",
        ],
        notes=(
            "Quarterly, not seasonally adjusted. All civilian workers,"
            " all industries, all occupations. 12-month percent change."
            " Owner=1 (civilian), periodicity=A."
        ),
        concept="eci_total_compensation_civilian_12mo_pct_change",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="CIU2010000000000A",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "ECI Total Compensation, All Private Industry Workers"
            " — 12-month percent change (Unadjusted)"
        ),
        keywords=[
            "eci",
            "employment cost index",
            "total compensation",
            "private industry",
            "12-month percent change",
            "compensation",
        ],
        notes=(
            "Quarterly, not seasonally adjusted. All private industry workers."
            " 12-month percent change. Owner=2 (private industry), periodicity=A."
        ),
        concept="eci_total_compensation_private_12mo_pct_change",
        measure_type="rate",
        unit="percent",
    ),
    FlagshipEntry(
        series_id="CIU2020000000000A",
        survey="CI",
        survey_name="Employer Costs for Employee Compensation",
        description=(
            "ECI Wages and Salaries, All Private Industry Workers"
            " — 12-month percent change (Unadjusted)"
        ),
        keywords=[
            "eci",
            "employment cost index",
            "wages and salaries",
            "private industry",
            "12-month percent change",
            "compensation",
        ],
        notes=(
            "Quarterly, not seasonally adjusted. All private industry workers."
            " Wages and salaries component. 12-month percent change."
            " Owner=2, estimate=02, periodicity=A."
        ),
        concept="eci_wages_salaries_private_12mo_pct_change",
        measure_type="rate",
        unit="percent",
    ),
]

# Master list — all entries across all surveys.
FLAGSHIP_SERIES: list[FlagshipEntry] = (
    _SM_ENTRIES
    + _CE_ENTRIES
    + _LA_ENTRIES
    + _JT_ENTRIES
    + _CU_ENTRIES
    + _LN_ENTRIES
    + _PR_ENTRIES
    + _MP_ENTRIES
    + _CW_ENTRIES
    + _WP_ENTRIES
    + _EI_ENTRIES
    + _CI_ENTRIES
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
