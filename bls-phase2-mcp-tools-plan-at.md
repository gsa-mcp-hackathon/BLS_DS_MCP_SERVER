# BLS Phase 2 — MCP Tools Plan

## Top-Level Overview

**Goal:** Build the core set of BLS MCP tools — lookup helpers, series ID build/decode/validate,
search/suggest, metadata, and live data fetch — grounded in the local-cache reference files
and the BLS Public Data API (already wired in Phase 1).

**Scope (this phase):** Sub-Tasks 1–12 below. The `answer_bls_question` orchestrator tool
is explicitly **out of scope for this phase** and will be planned separately.

**Approach:**
1. Build a shared `catalog.py` helper that reads the local-cache TSV/fixed-width files
   once at startup and serves them to all tools.
2. Add a `bls_series_schema.py` module that maps every supported survey prefix to its
   series ID segment layout (positions, lengths, field names).
3. Add a `bls_flagship_series.py` module with a curated table of canonical BLS series.
4. Implement each tool as a one-file-per-tool module under `src/example_server/tools/`.
5. Wire all new tools into `tools/__init__.py`.
6. Add comprehensive mocked unit tests for every tool.
7. Add a BLS-focused MCP prompt to `prompts/`.

**Non-goals:**
- No `answer_bls_question` tool (deferred to Phase 3).
- No UI or front-end.
- No changes to `config.py`, `utils.py`, `models.py`, `app.py`, or `routes.py`.
- No Docker or deployment work.
- No package rename (stays `example_server`).

---

## Existing Infrastructure (Phase 1 — fully implemented)

| Symbol | Location | Used by |
|---|---|---|
| `fetch_bls(payload)` | `utils.py` | `get_series_data` tool |
| `unwrap_bls_response(payload)` | `utils.py` | `get_series_data` tool |
| `validate_series_request(request)` | `utils.py` | `get_series_data` tool |
| `BLSSeriesRequest` | `models.py` | `get_series_data` tool |
| `BLSAPIError`, `UpstreamServiceError` | `utils.py` | all tools |
| `get_bls_api_version()` | `config.py` | `get_series_data` tool |
| `paginate()` | `utils.py` | `search_series` tool |

---

## Local-Cache Files Reference

All files live under `src/example_server/local-cache/`. Two formats:

| Format | Files | Delimiter | Notes |
|---|---|---|---|
| TSV (tab-separated) | `sm.*`, `ce.*`, `la.*`, `jt.*`, `bd.*`, `ap.*`, `cu.*`, `cw.*`, `su.*`, `wp.*`, `nb.*`, `pc.*` | `\t` | First row is header |
| Fixed-width | `qcew-*.txt` | None | First 5 chars = code, rest (stripped) = description |

Key files used by the tools in this plan:

| File | Key columns | Used by |
|---|---|---|
| `sm.area` | `area_code`, `area_name` | `lookup_area_code`, `build_series_id`, `decode_series_id` |
| `sm.industry` | `industry_code`, `industry_name` | `lookup_industry_code`, `build_series_id`, `decode_series_id` |
| `sm.supersector` | `supersector_code`, `supersector_name` | decode only |
| `sm.state` | `state_code`, `state_name` | decode only |
| `sm.data_type` | `data_type_code`, `data_type_text` | decode only |
| `ce.industry` | `industry_code`, `industry_name` | `lookup_industry_code` |
| `ce.datatype` | `data_type_code`, `data_type_text` | decode only |
| `ce.seasonal` | `seasonal_code`, `seasonal_text` | decode only |
| `la.area` | `area_code`, `area_text` | `lookup_area_code` |
| `la.measure` | `measure_code`, `measure_text` | decode only |
| `jt.area` | `area_code`, `area_text` | decode only |
| `jt.industry` | `industry_code`, `industry_text` | `lookup_industry_code` |
| `qcew-area-titles-txt.txt` | fixed-width: code / name | `lookup_area_code` |
| `qcew-industry-titles.txt` | fixed-width: code / name | `lookup_industry_code` |

---

## Sub-Tasks

---

### Sub-Task 1 — `catalog.py`: Shared Local-Cache Loader

**Intent:** Centralize all local-cache file parsing in one module so every tool reads the
same data without re-parsing files on each call. A single module-level `Catalog` singleton
is loaded once at import time and exposed as a simple API (`Catalog.lookup(survey, file_type, code)`).

**Expected Outcomes:**
- New file `src/example_server/catalog.py`
- `Catalog` class with:
  - `load_tsv(path) -> dict[str, str]`: reads a tab-separated file, returns `{code: name}`
    from its first two columns (ignores extra columns)
  - `load_fixed_width(path) -> dict[str, str]`: reads QCEW-style fixed-width files where
    first 5 chars are the code and the rest (stripped) is the description
  - `get(survey_prefix: str, dimension: str) -> dict[str, str]`: returns a code→name dict
    for any known `(survey_prefix, dimension)` pair; returns `{}` for unknown pairs
  - `search(survey_prefix: str, dimension: str, query: str, max_results: int = 20) -> list[dict]`:
    case-insensitive substring search across both codes and names; returns
    `[{"code": ..., "name": ..., "survey": ..., "dimension": ...}]`
- A module-level `catalog = Catalog()` singleton that pre-loads all files at startup
- Graceful handling of missing files (log warning, return `{}` for that entry)
- All paths resolved relative to the `local-cache/` directory alongside `catalog.py`

**Relevant Context:**
- `src/example_server/local-cache/sm.area` — TSV, columns: `area_code`, `area_name`
- `src/example_server/local-cache/qcew-area-titles-txt.txt` — fixed-width, code=first 5 chars
- `src/example_server/local-cache/ce.industry` — TSV, 7 columns; only first two used
- Pattern: similar to how `config.py` exposes a `settings` singleton

**Status:** [ ] pending

---

### Sub-Task 2 — `bls_series_schema.py`: Series ID Segment Layouts

**Intent:** Define the structural grammar of BLS series IDs so the `build_series_id`,
`decode_series_id`, and `validate_series_id` tools have a single authoritative source of
truth. Each survey prefix has a fixed layout of named segments at specific character
positions.

**Expected Outcomes:**
- New file `src/example_server/bls_series_schema.py`
- A `SeriesSegment` dataclass: `name: str`, `start: int`, `length: int`, `description: str`,
  `catalog_key: tuple[str, str] | None` (points to a `(survey_prefix, dimension)` in Catalog
  for decoding)
- A `SeriesSchema` dataclass: `prefix: str`, `name: str`, `total_length: int`,
  `segments: list[SeriesSegment]`
- `SCHEMAS: dict[str, SeriesSchema]` covering at minimum these prefixes, based on
  `https://www.bls.gov/help/hlpforma.htm`:
    - `SM` — State & Metro Employment (20 chars)
    - `CE` — Current Employment Statistics (13 chars)
    - `LA` — Local Area Unemployment Statistics (**variable length**, see note below)
    - `JT` — Job Openings & Labor Turnover (18 chars)
    - `CU` — Consumer Price Index (16 chars)
- `get_schema(series_id: str) -> SeriesSchema | None`: matches prefix (first 2 chars) to schema
- `decode_id(series_id: str) -> dict[str, Any]`: splits the ID into named segments and
  resolves each `catalog_key` entry to a human-readable name from the `catalog` singleton;
  returns `{"prefix": "SM", "survey": "...", "segments": [{"name": ..., "value": ..., "label": ...}]}`
- `build_id(**kwargs) -> str | dict`: assembles a series ID from named keyword arguments
  for a given survey prefix; returns the assembled ID on success, or an error dict describing
  which required fields are missing/invalid

**Relevant Context:**
- BLS series ID format reference: `https://www.bls.gov/help/hlpforma.htm`
- SM series format: `SM` (2) + seasonal (1) + state (2) + area (5) + supersector (2) +
  industry (6) + data_type (2) = 20 chars total
- CE series format: `CE` (2) + seasonal (1) + supersector (2) + industry (6) + data_type (2) = 13 chars
- LA series format: `LA` (2) + seasonal (1) + area_type (1) + area_code (variable, driven by
  `area_type_code` in `la.area`) + measure (2). **Total length varies by area type** (state IDs
  are shorter than metro/county IDs). The schema must store the area_type→length mapping and
  document that `decode_id` reads `area_type_code` at position 3 to determine the area_code
  field length before splitting the remainder.
- JT series format: `JT` (2) + seasonal (1) + area (2) + industry (6) + size_class (1) +
  data_element (2) + rate_level (1) = 18 chars
- CU series format: `CU` (2) + seasonal (1) + periodicity (1) + area (4) + item (8) = 16 chars

**Status:** [ ] pending

---

### Sub-Task 3 — Tool: `lookup_area_code`

**Intent:** Give the AI agent a way to translate a natural-language place name ("Chicago",
"Alabama", "Travis County") into the BLS area codes used across multiple survey prefixes.
Searches across all loaded area catalogs (SM, LA, QCEW) and returns ranked matches.

**Expected Outcomes:**
- New file `src/example_server/tools/lookup_area_code.py`
- Tool name: `lookup_area_code`
- Parameters:
  - `query: str` — place name or partial name to search (e.g., `"Chicago"`, `"AL"`, `"01001"`)
  - `survey: str | None` — optional filter to a specific survey prefix (e.g., `"SM"`, `"LA"`)
  - `limit: int` — max results to return (default 20, max 50)
- Returns a list of matches: `[{"code": str, "name": str, "survey": str, "dimension": str}]`
- Searches case-insensitively across both code and name fields
- When `survey` is provided, restricts results to that survey's area catalog
- Sorted: exact code match first, then starts-with, then contains
- Returns `{"results": [...], "count": int, "query": str}`

**Relevant Context:**
- Uses `catalog.search(survey_prefix, "area", query)` from Sub-Task 1
- Survey→dimension pairs for areas: `("sm", "area")`, `("la", "area")`, `("qcew", "area")`
- `src/example_server/tools/example_tool.py` — follow this file's `register(mcp)` pattern

**Status:** [ ] pending

---

### Sub-Task 4 — Tool: `lookup_industry_code`

**Intent:** Translate a natural-language industry description ("healthcare", "manufacturing",
"NAICS 622") into the numeric codes used in BLS series IDs. Different surveys use different
industry taxonomies (CE uses 8-digit codes, JT has its own hierarchy, QCEW uses NAICS).

**Expected Outcomes:**
- New file `src/example_server/tools/lookup_industry_code.py`
- Tool name: `lookup_industry_code`
- Parameters:
  - `query: str` — industry name or partial NAICS code (e.g., `"healthcare"`, `"622"`)
  - `survey: str | None` — optional filter to a specific survey prefix (e.g., `"CE"`, `"JT"`)
  - `limit: int` — max results (default 20, max 50)
- Returns `{"results": [{"code": str, "name": str, "survey": str}], "count": int, "query": str}`
- Covers `("ce", "industry")`, `("sm", "industry")`, `("jt", "industry")`, `("qcew", "industry")`
- Hierarchical display: includes `display_level` when available so the agent can understand
  parent/child relationships

**Relevant Context:**
- Uses `catalog.search(survey_prefix, "industry", query)` from Sub-Task 1
- `ce.industry` has a `display_level` column; include it in results when present

**Status:** [ ] pending

---

### Sub-Task 5 — Tool: `build_series_id`

**Intent:** Let the agent construct a valid BLS series ID from human-readable parts without
knowing the exact byte positions. The agent says "give me seasonally adjusted total
nonfarm employment for Chicago" and the tool returns the correct series ID string.

**Expected Outcomes:**
- New file `src/example_server/tools/build_series_id.py`
- Tool name: `build_series_id`
- Parameters:
  - `survey: str` — survey prefix (e.g., `"SM"`, `"CE"`, `"LA"`, `"JT"`, `"CU"`)
  - `seasonal_adjustment: str` — `"S"` (seasonally adjusted) or `"U"` (not adjusted)
  - `**dimensions: dict[str, str]` — named dimension values specific to the survey
    (e.g., `state_code="17"`, `area_code="16980"`, `industry_code="00000000"`, `data_type_code="01"`)
- Returns on success: `{"series_id": str, "decoded": dict}` where `decoded` is the result
  of calling `decode_id()` on the newly built ID
- Returns on failure: `{"error": str, "missing_fields": list[str], "schema": dict}` describing
  what is required for the chosen survey
- Validates each dimension value against the catalog (warns if code not found, but still builds)

**Relevant Context:**
- Calls `bls_series_schema.build_id()` from Sub-Task 2
- `decode_id()` called on the result for immediate human-readable confirmation

**Status:** [ ] pending

---

### Sub-Task 6 — Tool: `decode_series_id`

**Intent:** Take an opaque BLS series ID (e.g., `"SMU17169800500000001"`) and return a
fully human-readable breakdown showing what each segment means.

**Expected Outcomes:**
- New file `src/example_server/tools/decode_series_id.py`
- Tool name: `decode_series_id`
- Parameters:
  - `series_id: str` — the series ID to decode
- Returns:
  ```json
  {
    "series_id": "SMU17169800500000001",
    "survey": "State and Metro Area Employment, Hours, and Earnings",
    "prefix": "SM",
    "segments": [
      {"name": "seasonal", "value": "U", "label": "Not Seasonally Adjusted"},
      {"name": "state_code", "value": "17", "label": "Illinois"},
      {"name": "area_code", "value": "16980", "label": "Chicago-Naperville-Elgin, IL-IN-WI"},
      {"name": "supersector_code", "value": "05", "label": "Total private"},
      {"name": "industry_code", "value": "00000000", "label": "Total nonfarm"},
      {"name": "data_type_code", "value": "01", "label": "All Employees, In Thousands"}
    ]
  }
  ```
- When the prefix is unrecognized, returns `{"error": str, "series_id": str}`
- When a segment code is not found in the catalog, `label` is `null` (not fabricated)

**Relevant Context:**
- Calls `bls_series_schema.decode_id(series_id)` from Sub-Task 2
- Resolves codes via `catalog.get()` from Sub-Task 1

**Status:** [ ] pending

---

### Sub-Task 7 — Tool: `validate_series_id`

**Intent:** Check whether a series ID string is structurally valid before using it in an API
call. Catches typos, wrong lengths, unrecognized prefixes, and codes not in the catalog —
all locally without a network round-trip.

**Expected Outcomes:**
- New file `src/example_server/tools/validate_series_id.py`
- Tool name: `validate_series_id`
- Parameters:
  - `series_id: str` — the series ID to validate
- Returns:
  ```json
  {
    "series_id": "SMU17169800500000001",
    "valid": true,
    "issues": [],
    "decoded": { ... }
  }
  ```
  or on failure:
  ```json
  {
    "series_id": "SMxxx",
    "valid": false,
    "issues": [
      "Unrecognized survey prefix 'SM' — expected length 20, got 5",
      "state_code '99' not found in sm.state catalog"
    ],
    "decoded": null
  }
  ```
- Issues are descriptive strings, not codes — designed to be passed directly to the agent
- Checks: prefix exists, total length matches schema, each segment within valid character range,
  each code present in the corresponding catalog (warnings for unknown codes)

**Relevant Context:**
- Calls `bls_series_schema.get_schema()` and `bls_series_schema.decode_id()` from Sub-Task 2
- Catalog lookups via `catalog.get()` from Sub-Task 1

**Status:** [ ] pending

---

### Sub-Task 8 — Tool: `search_series`

**Intent:** Find BLS series IDs matching natural-language criteria (e.g., "unemployment rate
in Chicago" or "total nonfarm payrolls Illinois seasonally adjusted"). Performs a structured
search across the catalog dimension tables and assembles candidate series IDs. This is a
local-only, no-network tool.

**Expected Outcomes:**
- New file `src/example_server/tools/search_series.py`
- Tool name: `search_series`
- Parameters:
  - `query: str` — free-text description of what the user wants
  - `survey: str | None` — optional survey prefix filter (`"SM"`, `"CE"`, `"LA"`, etc.)
  - `limit: int` — max results (default 10, max 25)
- Strategy:
  1. Parse `query` for area hints (e.g., state names, metro names), industry hints, and
     measure hints (employment, unemployment, earnings, etc.)
  2. Look up matching codes in catalog for each hint
  3. For each (survey, area_code, industry_code) combination, call `build_id()` to assemble
     candidate IDs and `decode_id()` to produce a human-readable label
  4. Rank results by how many query terms matched
- Returns:
  ```json
  {
    "query": "unemployment rate Chicago",
    "results": [
      {
        "series_id": "LAUMT171698000000003",
        "label": "Unemployment Rate — Chicago-Naperville-Elgin, IL-IN-WI",
        "survey": "Local Area Unemployment Statistics",
        "match_score": 3
      }
    ],
    "count": 1
  }
  ```
- When no matches found, returns `{"results": [], "suggestion": "Try lookup_area_code or lookup_industry_code to find exact codes"}` 

**Relevant Context:**
- Calls `catalog.search()`, `build_id()`, `decode_id()` from Sub-Tasks 1 and 2
- Uses `paginate()` from `utils.py` for the result list

**Status:** [ ] pending

---

### Sub-Task 9 — Tool: `suggest_series`

**Intent:** Given a topic or question ("what data is available for retail trade in Texas?"),
suggest a curated list of series IDs with explanations. More opinionated than `search_series` —
meant for discovery when the user does not know what BLS surveys exist.

**Expected Outcomes:**
- New file `src/example_server/tools/suggest_series.py`
- Tool name: `suggest_series`
- Parameters:
  - `topic: str` — free-text topic or question
  - `limit: int` — max suggestions (default 5, max 15)
- Returns a ranked list of suggestions with:
  - `series_id: str`
  - `survey_name: str`
  - `description: str` — human-readable label from `decode_id()`
  - `rationale: str` — one sentence explaining why this series answers the topic
- Implementation: maps topic keywords to a hardcoded **flagship series table** covering all
  five supported surveys — at least 6 entries per survey:
  - **SM** — total nonfarm employment by state and metro (national, selected large metros)
  - **CE** — national total nonfarm payrolls (seasonally and not-seasonally adjusted),
    private-sector total, goods-producing, service-providing; split by supersector
  - **LA** — national unemployment rate (U-3), state-level unemployment rates for all 50 states
    and DC, metro-level unemployment for the 10 largest metros
  - **JT** — total job openings (all industries, all areas), total hires, total quits, total
    layoffs and discharges; national and selected industries
  - **CU** — CPI-U All Items (national), CPI-U Food, CPI-U Energy, CPI-U All Items Less Food
    and Energy (core CPI), CPI-W All Items, Chained CPI
  - Each entry has: `series_id`, `survey`, `description`, `rationale` (keywords that trigger it)
- Supplements flagship matches with `search_series` results for non-flagship queries
- Returns `{"topic": str, "suggestions": [...], "count": int}`

**Relevant Context:**
- Calls `decode_series_id` logic and `search_series` logic from Sub-Tasks 6 and 8
- Imports flagship table from Sub-Task 9 (`bls_flagship_series.py`) — no network call

**Status:** [ ] pending

---

### Sub-Task 9 — `bls_flagship_series.py`: Shared Flagship Series Table

**Intent:** Extract the curated "flagship series" reference data into its own module so
`suggest_series`, `get_series_metadata`, and the BLS assistant prompt all read from exactly
one source of truth. Defining it as a separate sub-task keeps the table explicit, versioned,
and independently testable.

**Expected Outcomes:**
- New file `src/example_server/bls_flagship_series.py`
- A `FlagshipEntry` dataclass or `TypedDict`:
  - `series_id: str` — the exact BLS series ID
  - `survey: str` — survey prefix (SM, CE, LA, JT, CU)
  - `survey_name: str` — human-readable survey name
  - `description: str` — one-line description of the series
  - `keywords: list[str]` — lowercase keywords used for topic matching (e.g., `["unemployment", "rate", "national"]`)
  - `notes: str` — publication notes (frequency, seasonality, preliminary/revised status)
- `FLAGSHIP_SERIES: list[FlagshipEntry]` — the complete table, covering all five surveys
  with at least 6 entries each:
  - **SM (6+)** — total nonfarm employment, national; nonfarm employment for NY, LA, Chicago,
    Houston, Phoenix metros; goods-producing; private service-providing
  - **CE (6+)** — total nonfarm payrolls SA; total nonfarm payrolls NSA; total private SA;
    goods-producing SA; service-providing SA; average hourly earnings all employees SA
  - **LA (6+)** — national unemployment rate (U-3) SA; national unemployment rate NSA;
    state unemployment rates for CA, TX, NY, FL, IL; Chicago metro unemployment rate
  - **JT (6+)** — total job openings all industries all areas; total hires; total quits;
    total layoffs and discharges; total other separations; job openings rate national
  - **CU (6+)** — CPI-U All Items U.S. City Average SA; CPI-U All Items NSA; CPI-U Food;
    CPI-U Energy; CPI-U All Items Less Food and Energy (Core CPI); CPI-W All Items
- `get_flagship(series_id: str) -> FlagshipEntry | None` — exact match by series ID
- `search_flagship(topic: str, limit: int = 10) -> list[FlagshipEntry]` — keyword match
  (case-insensitive substring search across `keywords`, `description`, `survey_name`);
  returns ranked results sorted by number of matched keywords descending

**Relevant Context:**
- Used by Sub-Task 10 (`suggest_series`) and Sub-Task 11 (`get_series_metadata`)
- No catalog or schema dependency — this module is standalone pure-Python data
- BLS series ID examples for the table can be verified against `https://www.bls.gov/help/hlpforma.htm`
  and the local-cache files; correctness of the IDs matters (they will be passed to the live API)

**Status:** [ ] pending

---

### Sub-Task 10 — Tool: `suggest_series`

**Intent:** Given a topic or question ("what data is available for retail trade in Texas?"),
suggest a curated list of series IDs with explanations. More opinionated than `search_series` —
meant for discovery when the user does not know what BLS surveys exist.

**Expected Outcomes:**
- New file `src/example_server/tools/suggest_series.py`
- Tool name: `suggest_series`
- Parameters:
  - `topic: str` — free-text topic or question
  - `limit: int` — max suggestions (default 5, max 15)
- Returns a ranked list of suggestions with:
  - `series_id: str`
  - `survey_name: str`
  - `description: str` — human-readable label from `decode_id()`
  - `rationale: str` — one sentence explaining why this series answers the topic
- Implementation: calls `search_flagship(topic)` from `bls_flagship_series.py` to find
  flagship matches; supplements with `search_series` results for non-flagship queries
- Returns `{"topic": str, "suggestions": [...], "count": int}`

**Relevant Context:**
- Calls `search_flagship()` from Sub-Task 9 (`bls_flagship_series.py`)
- Calls `decode_series_id` logic and `search_series` logic from Sub-Tasks 6 and 8

**Status:** [ ] pending

---

### Sub-Task 11 — Tool: `get_series_metadata`

**Intent:** Return everything the server knows about a series ID without making a BLS API
call: the decoded segment labels, the survey description, the catalog entries, and the
validation result. Useful for confirming a series is well-formed before calling the API.

**Expected Outcomes:**
- New file `src/example_server/tools/get_series_metadata.py`
- Tool name: `get_series_metadata`
- Parameters:
  - `series_id: str`
- Returns a combined dict:
  ```json
  {
    "series_id": "CUUR0000SA0",
    "valid": true,
    "issues": [],
    "survey": "Consumer Price Index — All Urban Consumers",
    "prefix": "CU",
    "segments": [ ... ],
    "notes": "This is a headline CPI series published monthly."
  }
  ```
- `notes` field: populated from `get_flagship(series_id).notes` when the series appears in
  the flagship table; omitted (not present in the dict) for non-flagship series
- Always local — no network call

**Relevant Context:**
- Calls `validate_series_id` logic and `decode_series_id` logic (Sub-Tasks 6 and 7)
- Calls `get_flagship()` from Sub-Task 9 (`bls_flagship_series.py`)

**Status:** [ ] pending

---

### Sub-Task 12 — Tool: `get_series_data`

**Intent:** Fetch actual time-series observations from the BLS Public Data API for one or
more series IDs. This is the only tool that makes a live network call. It wraps the Phase 1
`fetch_bls` + `unwrap_bls_response` + `validate_series_request` pipeline in an MCP-friendly
interface.

**Expected Outcomes:**
- New file `src/example_server/tools/get_series_data.py`
- Tool name: `get_series_data`
- Parameters:
  - `series_ids: list[str]` — one or more series IDs to fetch
  - `start_year: int | None` — start year (BLS default if omitted)
  - `end_year: int | None` — end year (BLS default if omitted)
  - `calculations: bool` — v2 only, include net/percent change (default `False`)
  - `annual_average: bool` — v2 only, include annual average (default `False`)
- Flow:
  1. Construct `BLSSeriesRequest` (Pydantic validation)
  2. Call `validate_series_request(request)` (limit enforcement)
  3. Build BLS POST payload
  4. `await fetch_bls(payload)` → `unwrap_bls_response()`
  5. For each series: decode segment labels via `decode_series_id` logic for context
  6. Return enriched response
- Returns:
  ```json
  {
    "api_version": "v2",
    "series": [
      {
        "series_id": "CUUR0000SA0",
        "label": "CPI-U, All Items, U.S. City Average",
        "observations": [
          {"year": "2024", "period": "M12", "period_name": "December",
           "value": "314.175", "footnotes": []}
        ]
      }
    ],
    "notes": "Data sourced from BLS Public Data API. Values are strings to preserve published precision."
  }
  ```
- On `BLSAPIError` or `UpstreamServiceError`: returns `{"error": str, "series_ids": list[str]}`
  (never re-raises — MCP tools must return, not throw)

**Relevant Context:**
- `fetch_bls`, `unwrap_bls_response`, `validate_series_request` in `utils.py` (Phase 1)
- `BLSSeriesRequest` in `models.py` (Phase 1)
- `decode_id()` from Sub-Task 2 for label enrichment
- `get_flagship()` from Sub-Task 9 for the `notes` field on known flagship series

**Status:** [ ] pending

---

### Sub-Task 13 — Wire Tools into `__init__.py` + Add BLS Prompt

**Intent:** Register all new tools with the MCP server aggregator and add a BLS-focused
system prompt that tells the AI client how to use the tools effectively.

**Expected Outcomes:**
- `src/example_server/tools/__init__.py` updated to import and call `register()` for all
  9 new tool modules (lookup_area_code, lookup_industry_code, build_series_id, decode_series_id,
  validate_series_id, search_series, suggest_series, get_series_metadata, get_series_data)
- New file `src/example_server/prompts/bls_assistant.py` with a `register(mcp)` function
  that adds a prompt named `bls_assistant` with:
  - Instructions on when to use `search_series` vs `suggest_series` vs `get_series_data` directly
  - Reminder that `get_series_data` is the only tool making live network calls (all others
    are local-only); batch multiple series IDs into one `get_series_data` call to stay within
    the daily API limit
  - Workflow tip: use `search_series` or `suggest_series` to find series IDs, then
    `validate_series_id` to confirm correctness before calling `get_series_data`
  - Note on data freshness and BLS publication lags (monthly releases, preliminary vs. revised)
- `src/example_server/prompts/__init__.py` updated to call `bls_assistant.register(mcp)`

**Relevant Context:**
- `src/example_server/tools/__init__.py` — current aggregator pattern
- `src/example_server/prompts/__init__.py` + `prompts/example.py` — prompt registration pattern

**Status:** [ ] pending

---

### Sub-Task 14 — Tests

**Intent:** Provide mocked unit tests for every new module. No real BLS API calls.
All tests must pass alongside the existing test suite.

**Expected Outcomes:**
- `tests/test_catalog.py` — tests for `CatalogLoader`: TSV parsing, fixed-width parsing,
  unknown file graceful handling, `search()` case-insensitivity, empty query, exact code match
- `tests/test_bls_series_schema.py` — tests for every `SCHEMAS` entry: known prefix returns
  schema, `decode_id` returns correct segment count and label resolution, `build_id` constructs
  correct string, unrecognized prefix returns `None`
- `tests/test_tools_lookup.py` — tests for `lookup_area_code` and `lookup_industry_code`:
  found/not-found cases, survey filter, result shape
- `tests/test_tools_build_decode_validate.py` — tests for `build_series_id`, `decode_series_id`,
  `validate_series_id`: valid input, missing field, wrong-length prefix, code not in catalog
- `tests/test_bls_flagship_series.py` — tests for `bls_flagship_series.py`:
  exact `get_flagship` hit/miss, `search_flagship` keyword match, case-insensitivity,
  all five surveys present, each entry has required fields, no duplicate series IDs
- `tests/test_tools_search_suggest.py` — tests for `search_series` and `suggest_series`:
  matching query, no-match fallback, limit enforcement, result shape
- `tests/test_tools_get_series.py` — tests for `get_series_data` and `get_series_metadata`:
  mock `fetch_bls` returns success envelope, mock returns error, `BLSAPIError` returns error dict
**Pattern:** Follow `_FakeBLSPost` mock class from `test_bls_utils.py` and `asyncio_mode = "auto"`
from `pyproject.toml`.

**Relevant Context:**
- `tests/test_bls_utils.py` — mock pattern to follow
- `tests/test_server.py` — smoke test pattern: import and registration assertions

**Status:** [ ] pending

---

## Implementation Order

The sub-tasks have clear dependencies. Implement in this sequence:

```
1 (catalog)
  └─ 2 (schema)
       ├─ 3 (lookup_area_code)
       ├─ 4 (lookup_industry_code)
       ├─ 5 (build_series_id)
       ├─ 6 (decode_series_id)
       ├─ 7 (validate_series_id)
       │
       ├─ 8 (search_series)
       │    └─ 10 (suggest_series) ──┐
       │                             │
       └─ 9 (bls_flagship_series)   │
            ├─ (feeds 10)  ──────────┘
            └─ 11 (get_series_metadata)
                   └─ 12 (get_series_data)
                          └─ 13 (wire + prompt)
                                 └─ 14 (tests)
```

---

## Files to Create

| File | Sub-Task | Purpose |
|---|---|---|
| `src/example_server/catalog.py` | 1 | Local-cache loader singleton |
| `src/example_server/bls_series_schema.py` | 2 | Series ID segment layout definitions |
| `src/example_server/bls_flagship_series.py` | 9 | Flagship series table (shared data) |
| `src/example_server/tools/lookup_area_code.py` | 3 | Area code lookup tool |
| `src/example_server/tools/lookup_industry_code.py` | 4 | Industry code lookup tool |
| `src/example_server/tools/build_series_id.py` | 5 | Series ID builder tool |
| `src/example_server/tools/decode_series_id.py` | 6 | Series ID decoder tool |
| `src/example_server/tools/validate_series_id.py` | 7 | Series ID validator tool |
| `src/example_server/tools/search_series.py` | 8 | Series search tool |
| `src/example_server/tools/suggest_series.py` | 10 | Series suggestion tool |
| `src/example_server/tools/get_series_metadata.py` | 11 | Metadata-only (no API) tool |
| `src/example_server/tools/get_series_data.py` | 12 | Live BLS API fetch tool |
| `src/example_server/prompts/bls_assistant.py` | 13 | BLS assistant system prompt |
| `tests/test_catalog.py` | 14 | Catalog unit tests |
| `tests/test_bls_series_schema.py` | 14 | Schema unit tests |
| `tests/test_bls_flagship_series.py` | 14 | Flagship series table unit tests |
| `tests/test_tools_lookup.py` | 14 | Lookup tool tests |
| `tests/test_tools_build_decode_validate.py` | 14 | Build/decode/validate tool tests |
| `tests/test_tools_search_suggest.py` | 14 | Search/suggest tool tests |
| `tests/test_tools_get_series.py` | 14 | Data fetch tool tests |

## Files to Modify

| File | Change |
|---|---|
| `src/example_server/tools/__init__.py` | Register all 9 new tools |
| `src/example_server/prompts/__init__.py` | Register `bls_assistant` prompt |
