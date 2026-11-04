# BLS Phase 2 — MCP Tools Plan

## Top-Level Overview

**Goal:** Build the core set of BLS MCP tools — lookup helpers, series ID build/decode/validate,
search/suggest, metadata, live data fetch, and a full mocked test suite — grounded in the
local-cache reference files and the BLS Public Data API (Phase 1 infrastructure already done).

**Scope (this phase):** Sub-Tasks 1–14 below.
The `answer_bls_question` orchestrator tool is **explicitly deferred to Phase 3**.

**Non-goals:**
- No `answer_bls_question` tool.
- No changes to `config.py`, `utils.py`, `models.py`, `app.py`, or `routes.py`.
- No Docker or deployment work. No package rename.

---

## Existing Infrastructure (Phase 1 — complete, do not modify)

| Symbol | File | Notes |
|---|---|---|
| `fetch_bls(payload)` | `utils.py` | Used by `get_series_data` |
| `unwrap_bls_response(payload)` | `utils.py` | Used by `get_series_data` |
| `validate_series_request(request)` | `utils.py` | Used by `get_series_data` |
| `BLSSeriesRequest` | `models.py` | Used by `get_series_data` |
| `BLSAPIError`, `UpstreamServiceError` | `utils.py` | Used by all tools |
| `get_bls_api_version()` | `config.py` | Used by `get_series_data` |
| `paginate()` | `utils.py` | Used by `search_series` |

---

## Local-Cache File Formats

All files under `src/example_server/local-cache/`:

| Format | Files | Delimiter | Notes |
|---|---|---|---|
| TSV | `sm.*`, `ce.*`, `la.*`, `jt.*`, `bd.*`, `ap.*`, `cu.*`, `cw.*`, `su.*`, `wp.*`, `nb.*`, `pc.*` | `\t` | First row is header |
| Fixed-width | `qcew-*.txt` | None | First 5 chars = code, rest (stripped) = description |

---

## Series ID Formats (from https://www.bls.gov/help/hlpforma.htm)

| Survey | Format | Length | Key segments |
|---|---|---|---|
| SM | `SM` + seasonal(1) + state(2) + area(5) + supersector(2) + industry(6) + data_type(2) | 20 | |
| CE | `CE` + seasonal(1) + supersector(2) + industry(6) + data_type(2) | 13 | |
| LA | `LA` + seasonal(1) + area_type(1) + area_code(variable) + measure(2) | variable | area_type at pos 3 determines area_code length |
| JT | `JT` + seasonal(1) + area(2) + industry(6) + size_class(1) + data_element(2) + rate_level(1) | 18 | |
| CU | `CU` + seasonal(1) + periodicity(1) + area(4) + item(8) | 16 | |

---

## Sub-Tasks

---

### Sub-Task 1 — `catalog.py`: Local-Cache Loader Singleton

**Intent:** Centralize all local-cache file parsing so every tool reads from the same
pre-loaded data without re-parsing files on each call.

**Expected Outcomes:**
- New file `src/example_server/catalog.py`
- `Catalog` class with:
  - `load_tsv(path) -> dict[str, str]`: reads TSV, returns `{first_col: second_col}`
  - `load_fixed_width(path) -> dict[str, str]`: reads QCEW files (first 5 chars = code, rest = name)
  - `get(survey: str, dimension: str) -> dict[str, str]`: returns code→name dict for a known pair; `{}` for unknown
  - `search(survey: str, dimension: str, query: str, max_results: int = 20) -> list[dict]`:
    case-insensitive substring match on code and name; returns `[{"code", "name", "survey", "dimension"}]`
- Module-level `catalog = Catalog()` singleton pre-loaded at import time
- Covers all survey+dimension pairs from the local-cache files
- Missing files handled gracefully (warn, return `{}`)

**Files:** `src/example_server/catalog.py`

**Status:** [ ] pending

---

### Sub-Task 2 — `bls_series_schema.py`: Series ID Segment Layouts

**Intent:** Define the structural grammar of BLS series IDs for SM, CE, LA, JT, and CU surveys
so build/decode/validate tools have a single authoritative source of truth.

**Expected Outcomes:**
- New file `src/example_server/bls_series_schema.py`
- `SeriesSegment` dataclass: `name`, `start`, `length`, `description`, `catalog_key: tuple[str,str] | None`
- `SeriesSchema` dataclass: `prefix`, `survey_name`, `total_length: int | None` (None = variable),
  `segments: list[SeriesSegment]`
- `SCHEMAS: dict[str, SeriesSchema]` for SM, CE, LA, JT, CU
- LA schema: stores `area_type_lengths: dict[str, int]` mapping area_type_code → area_code field length;
  `decode_id` reads `area_type` at position 3 to determine how to split the remainder
- `get_schema(series_id: str) -> SeriesSchema | None`: matches on first 2 chars
- `decode_id(series_id: str) -> dict`: returns
  `{"prefix", "survey", "segments": [{"name", "value", "label"}]}`;
  `label` is `null` when code not in catalog; error dict for unknown prefix
- `build_id(survey: str, **kwargs) -> str | dict`: assembles ID from named kwargs;
  returns error dict with `missing_fields` if required segments absent

**Files:** `src/example_server/bls_series_schema.py`

**Status:** [ ] pending

---

### Sub-Task 3 — `bls_flagship_series.py`: Shared Flagship Series Table

**Intent:** Provide a single shared module of curated BLS series entries covering all 5 surveys
so `suggest_series` and `get_series_metadata` both read from one source of truth.

**Expected Outcomes:**
- New file `src/example_server/bls_flagship_series.py`
- `FlagshipEntry` dataclass: `series_id`, `survey`, `survey_name`, `description`, `keywords: list[str]`, `notes`
- `FLAGSHIP_SERIES: list[FlagshipEntry]` with ≥6 entries per survey:
  - **SM**: nonfarm employment national + major metros (NY, LA, Chicago, Houston, Phoenix)
  - **CE**: total nonfarm SA, total nonfarm NSA, total private SA, goods-producing SA, service-providing SA, avg hourly earnings SA
  - **LA**: national U-3 SA, national U-3 NSA, state rates for CA/TX/NY/FL/IL, Chicago metro
  - **JT**: total openings, hires, quits, layoffs & discharges, other separations, openings rate
  - **CU**: CPI-U All Items SA, CPI-U All Items NSA, CPI-U Food, CPI-U Energy, Core CPI, CPI-W All Items
- `get_flagship(series_id: str) -> FlagshipEntry | None`: exact match by series ID
- `search_flagship(topic: str, limit: int = 10) -> list[FlagshipEntry]`: case-insensitive keyword
  search across `keywords + description + survey_name`; ranked by matched keyword count

**Files:** `src/example_server/bls_flagship_series.py`

**Status:** [ ] pending

---

### Sub-Task 4 — Tool: `lookup_area_code`

**Intent:** Translate a natural-language place name into BLS area codes used across SM, LA, and QCEW surveys.

**Expected Outcomes:**
- New file `src/example_server/tools/lookup_area_code.py`
- Tool name: `lookup_area_code`
- Parameters: `query: str`, `survey: str | None` (filter to SM/LA/QCEW), `limit: int` (default 20, max 50)
- Calls `catalog.search()` across area dimensions for all surveys (or filtered survey)
- Returns `{"query", "results": [{"code", "name", "survey", "dimension"}], "count"}`
- Sorted: exact code match first, starts-with second, contains third

**Files:** `src/example_server/tools/lookup_area_code.py`

**Status:** [ ] pending

---

### Sub-Task 5 — Tool: `lookup_industry_code`

**Intent:** Translate an industry description or NAICS code fragment into BLS industry codes.

**Expected Outcomes:**
- New file `src/example_server/tools/lookup_industry_code.py`
- Tool name: `lookup_industry_code`
- Parameters: `query: str`, `survey: str | None`, `limit: int` (default 20, max 50)
- Covers CE, SM, JT, QCEW industry catalogs
- Returns `{"query", "results": [{"code", "name", "survey"}], "count"}`

**Files:** `src/example_server/tools/lookup_industry_code.py`

**Status:** [ ] pending

---

### Sub-Task 6 — Tool: `build_series_id`

**Intent:** Assemble a valid BLS series ID from human-readable named parts.

**Expected Outcomes:**
- New file `src/example_server/tools/build_series_id.py`
- Tool name: `build_series_id`
- Parameters: `survey: str`, `seasonal_adjustment: str` ("S"/"U"), `**dimensions: dict[str, str]`
  (e.g. `state_code`, `area_code`, `industry_code`, `data_type_code`)
- On success: `{"series_id", "decoded": {...}}` (decoded via `decode_id`)
- On failure: `{"error", "missing_fields": [...], "schema": {...}}`
- Calls `bls_series_schema.build_id()`

**Files:** `src/example_server/tools/build_series_id.py`

**Status:** [ ] pending

---

### Sub-Task 7 — Tool: `decode_series_id`

**Intent:** Break an opaque BLS series ID into labeled segment fields.

**Expected Outcomes:**
- New file `src/example_server/tools/decode_series_id.py`
- Tool name: `decode_series_id`
- Parameters: `series_id: str`
- Returns:
  ```json
  {
    "series_id": "SMU17169800500000001",
    "survey": "State and Metro Area Employment, Hours, and Earnings",
    "prefix": "SM",
    "segments": [
      {"name": "seasonal", "value": "U", "label": "Not Seasonally Adjusted"},
      {"name": "state_code", "value": "17", "label": "Illinois"},
      {"name": "area_code", "value": "16980", "label": "Chicago-Naperville-Elgin, IL-IN-WI"}
    ]
  }
  ```
- Unrecognized prefix → `{"error": str, "series_id": str}`
- Missing catalog label → `label: null` (never fabricated)
- Calls `bls_series_schema.decode_id()`

**Files:** `src/example_server/tools/decode_series_id.py`

**Status:** [ ] pending

---

### Sub-Task 8 — Tool: `validate_series_id`

**Intent:** Check a series ID for structural validity and catalog membership without a network call.

**Expected Outcomes:**
- New file `src/example_server/tools/validate_series_id.py`
- Tool name: `validate_series_id`
- Parameters: `series_id: str`
- Returns `{"series_id", "valid": bool, "issues": [str, ...], "decoded": dict | null}`
- Checks: prefix in SCHEMAS, length matches schema, each code found in catalog
- Issues are descriptive strings for the agent to act on

**Files:** `src/example_server/tools/validate_series_id.py`

**Status:** [ ] pending

---

### Sub-Task 9 — Tool: `search_series`

**Intent:** Find BLS series IDs matching free-text criteria by searching catalog dimensions locally.

**Expected Outcomes:**
- New file `src/example_server/tools/search_series.py`
- Tool name: `search_series`
- Parameters: `query: str`, `survey: str | None`, `limit: int` (default 10, max 25)
- Strategy: parse query for area/industry/measure hints → look up codes → assemble candidate IDs
  via `build_id()` → decode for labels → rank by match score
- Returns `{"query", "results": [{"series_id", "label", "survey", "match_score"}], "count"}`
- No-match returns `{"results": [], "suggestion": "Try lookup_area_code or lookup_industry_code"}`
- Uses `paginate()` from `utils.py`

**Files:** `src/example_server/tools/search_series.py`

**Status:** [ ] pending

---

### Sub-Task 10 — Tool: `suggest_series`

**Intent:** Given a topic, suggest curated series IDs with rationales — for discovery, not precision search.

**Expected Outcomes:**
- New file `src/example_server/tools/suggest_series.py`
- Tool name: `suggest_series`
- Parameters: `topic: str`, `limit: int` (default 5, max 15)
- Calls `search_flagship(topic)` from `bls_flagship_series.py`; supplements with `search_series` for non-flagship queries
- Returns `{"topic", "suggestions": [{"series_id", "survey_name", "description", "rationale"}], "count"}`

**Files:** `src/example_server/tools/suggest_series.py`

**Status:** [ ] pending

---

### Sub-Task 11 — Tool: `get_series_metadata`

**Intent:** Return everything known about a series ID locally (decode + validate + flagship notes) without a network call.

**Expected Outcomes:**
- New file `src/example_server/tools/get_series_metadata.py`
- Tool name: `get_series_metadata`
- Parameters: `series_id: str`
- Returns `{"series_id", "valid": bool, "issues": [...], "survey", "prefix", "segments": [...], "notes"?}`
- `notes` present only when `get_flagship(series_id)` returns a match; omitted otherwise
- Calls validate + decode logic and `get_flagship()` from `bls_flagship_series.py`

**Files:** `src/example_server/tools/get_series_metadata.py`

**Status:** [ ] pending

---

### Sub-Task 12 — Tool: `get_series_data`

**Intent:** Fetch live time-series observations from the BLS Public Data API. This is the only
tool in this phase that makes a network call.

**Expected Outcomes:**
- New file `src/example_server/tools/get_series_data.py`
- Tool name: `get_series_data`
- Parameters: `series_ids: list[str]`, `start_year: int | None`, `end_year: int | None`,
  `calculations: bool = False`, `annual_average: bool = False`
- Flow: `BLSSeriesRequest` → `validate_series_request()` → build payload → `fetch_bls()` →
  `unwrap_bls_response()` → enrich each series with `decode_id()` label → return
- Returns:
  ```json
  {
    "api_version": "v1|v2",
    "series": [{"series_id", "label", "observations": [{"year","period","period_name","value","footnotes"}]}],
    "notes": "Values are strings to preserve published precision."
  }
  ```
- On `BLSAPIError`/`UpstreamServiceError`: returns `{"error": str, "series_ids": [...]}` — never re-raises
- Calls `get_flagship()` for `notes` enrichment on known flagship series

**Files:** `src/example_server/tools/get_series_data.py`

**Status:** [ ] pending

---

### Sub-Task 13 — Wire Tools + Add BLS Prompt

**Intent:** Register all 9 new tools and add a BLS-focused system prompt.

**Expected Outcomes:**
- `src/example_server/tools/__init__.py` updated to import and call `register()` for:
  `lookup_area_code`, `lookup_industry_code`, `build_series_id`, `decode_series_id`,
  `validate_series_id`, `search_series`, `suggest_series`, `get_series_metadata`, `get_series_data`
- New file `src/example_server/prompts/bls_assistant.py`:
  - Prompt named `bls_assistant`
  - Instructions: use `search_series`/`suggest_series` to discover IDs, `validate_series_id` to
    confirm, then `get_series_data` for observations
  - `get_series_data` is the only live-network tool; batch multiple IDs to conserve daily quota
  - Data freshness note: monthly BLS releases, preliminary vs. revised values
- `src/example_server/prompts/__init__.py` updated to call `bls_assistant.register(mcp)`

**Files:** modified `tools/__init__.py`, modified `prompts/__init__.py`, new `prompts/bls_assistant.py`

**Status:** [ ] pending

---

### Sub-Task 14 — Tests

**Intent:** Provide a complete mocked test suite for every new module. Zero real network calls.
All tests must pass alongside the existing suite (`test_server.py`, `test_http_security.py`, `test_bls_utils.py`).

**Test files and coverage:**

#### `tests/test_catalog.py`
- TSV file parsed correctly; code→name mapping returned
- Fixed-width QCEW file parsed correctly
- Unknown survey+dimension returns `{}`
- Missing file handled gracefully (no exception)
- `search()` case-insensitive substring match on code and name
- `search()` with empty query returns all entries up to `max_results`
- `search()` survey filter restricts results

#### `tests/test_bls_series_schema.py`
- `get_schema("SM...")` returns SM schema; same for CE, LA, JT, CU
- `get_schema("XX...")` returns `None` for unknown prefix
- `decode_id` for SM ID returns correct segment count and field values
- `decode_id` for CE ID returns correct segments
- `decode_id` for LA ID (variable-length area) splits correctly
- `decode_id` with unrecognized prefix returns error dict
- `decode_id` resolves catalog labels where available; `label: null` when missing
- `build_id` assembles correct SM ID from named kwargs
- `build_id` missing required field returns error dict with `missing_fields`

#### `tests/test_bls_flagship_series.py`
- All 5 surveys represented in `FLAGSHIP_SERIES`
- No duplicate `series_id` values
- Every entry has required fields (`series_id`, `survey`, `survey_name`, `description`, `keywords`, `notes`)
- `get_flagship` returns entry for known ID; `None` for unknown
- `search_flagship` returns matches for a keyword present in the table
- `search_flagship` is case-insensitive
- `search_flagship` respects `limit`

#### `tests/test_tools_lookup.py`
- `lookup_area_code`: query matching a known area returns result with correct shape
- `lookup_area_code`: no-match returns empty results list
- `lookup_area_code`: survey filter restricts to that survey
- `lookup_area_code`: limit enforced
- `lookup_industry_code`: query matching a known industry returns result
- `lookup_industry_code`: survey filter works

#### `tests/test_tools_build_decode_validate.py`
- `build_series_id`: valid SM kwargs → correct ID + decoded segments in response
- `build_series_id`: missing required field → error dict with `missing_fields`
- `build_series_id`: unknown survey → error dict
- `decode_series_id`: known SM ID → correct segments
- `decode_series_id`: unknown prefix → error dict
- `validate_series_id`: well-formed known ID → `valid: true`, empty issues
- `validate_series_id`: wrong length → `valid: false`, issue describes length mismatch
- `validate_series_id`: unknown prefix → `valid: false`
- `validate_series_id`: code not in catalog → `valid: false`, issue names the field

#### `tests/test_tools_search_suggest.py`
- `search_series`: query with a known area name returns candidate IDs
- `search_series`: no matching query returns empty results with suggestion
- `search_series`: survey filter restricts candidates
- `search_series`: limit enforced
- `suggest_series`: flagship topic keyword returns suggestions
- `suggest_series`: non-flagship topic falls back to `search_series` results
- `suggest_series`: limit enforced
- `suggest_series`: result shape has required fields (`series_id`, `survey_name`, `description`, `rationale`)

#### `tests/test_tools_get_series.py`
- `get_series_metadata`: known flagship series → `notes` field present
- `get_series_metadata`: non-flagship series → `notes` field absent
- `get_series_metadata`: invalid series ID → `valid: false` with issues
- `get_series_data`: mock `fetch_bls` returns success envelope → observations in response
- `get_series_data`: response has `api_version`, `series`, `notes` fields
- `get_series_data`: observations preserve string values (not floats)
- `get_series_data`: `BLSAPIError` raised by mock → returns `{"error": ..., "series_ids": [...]}`
- `get_series_data`: `UpstreamServiceError` raised by mock → returns error dict, does not re-raise
- `get_series_data`: Pydantic `ValidationError` on bad series ID format → returns error dict

**Mock pattern:** Follow `_FakeBLSPost` from `tests/test_bls_utils.py` (monkeypatch `utils.httpx.AsyncClient`).
`asyncio_mode = "auto"` is set in `pyproject.toml` — no `@pytest.mark.asyncio` needed.

**Files:** 7 new test files listed above

**Status:** [ ] pending

---

## Implementation Order

```
1 (catalog)
  └─ 2 (schema)
       ├─ 3 (bls_flagship_series)     [standalone, no catalog/schema dep]
       ├─ 4 (lookup_area_code)
       ├─ 5 (lookup_industry_code)
       ├─ 6 (build_series_id)
       ├─ 7 (decode_series_id)
       ├─ 8 (validate_series_id)
       ├─ 9 (search_series)
       │    └─ 10 (suggest_series) ───── uses 3 + 9
       ├─ 11 (get_series_metadata) ───── uses 3 + 7 + 8
       └─ 12 (get_series_data) ───────── uses Phase 1 utils + 7
            └─ 13 (wire + prompt)
                   └─ 14 (tests)
```

---

## Files to Create

| File | Sub-Task |
|---|---|
| `src/example_server/catalog.py` | 1 |
| `src/example_server/bls_series_schema.py` | 2 |
| `src/example_server/bls_flagship_series.py` | 3 |
| `src/example_server/tools/lookup_area_code.py` | 4 |
| `src/example_server/tools/lookup_industry_code.py` | 5 |
| `src/example_server/tools/build_series_id.py` | 6 |
| `src/example_server/tools/decode_series_id.py` | 7 |
| `src/example_server/tools/validate_series_id.py` | 8 |
| `src/example_server/tools/search_series.py` | 9 |
| `src/example_server/tools/suggest_series.py` | 10 |
| `src/example_server/tools/get_series_metadata.py` | 11 |
| `src/example_server/tools/get_series_data.py` | 12 |
| `src/example_server/prompts/bls_assistant.py` | 13 |
| `tests/test_catalog.py` | 14 |
| `tests/test_bls_series_schema.py` | 14 |
| `tests/test_bls_flagship_series.py` | 14 |
| `tests/test_tools_lookup.py` | 14 |
| `tests/test_tools_build_decode_validate.py` | 14 |
| `tests/test_tools_search_suggest.py` | 14 |
| `tests/test_tools_get_series.py` | 14 |

## Files to Modify

| File | Change |
|---|---|
| `src/example_server/tools/__init__.py` | Register 9 new tools |
| `src/example_server/prompts/__init__.py` | Register `bls_assistant` prompt |
