# Plan: Full Coverage for PR, MP, CW, WP, EI, and CI Series

## Overview

Six BLS survey series — **PR** (Productivity & Costs), **MP** (Multifactor Productivity),
**CW** (CPI-W / Urban Wage Earners), **WP** (PPI Commodity Data), **EI** (International
Price Program), and **CI** (Employer Costs for Employee Compensation) — have local-cache
reference files present but are not wired into the server's tooling. They are missing from
the series ID schema registry, the catalog registry (partially), the flagship series table,
the search tool, the surveys resource, and the assistant prompt.

This plan adds end-to-end coverage for all six surveys so they behave identically to the
fully-supported surveys (SM, CE, LA, JT, CU, LN): catalog lookups resolve, series IDs
decode and validate, the search tool surfaces them, flagship entries cover key series, the
surveys resource documents them, and the assistant prompt lists them.

All changes must pass `ruff check` (rules E, F, I; line-length 88) and the full existing
`pytest tests/` suite (excluding `--run-live`). New tests are added alongside each change.

---

## Series ID Format Reference

Derived by cross-referencing actual rows in each `.series` file against column values:

| Prefix | Example ID | Total Length | Notes |
|--------|-----------|-------------|-------|
| PR | `PRS30006011` | 11 | Fixed: seasonal(1)+sector(4)+class(1)+measure(2)+duration(1) |
| MP | `MPU0011012` | 10 | Fixed: seasonal(1)+sector(4)+measure(2)+duration(1) |
| CW | `CWSR0000SA0` | Variable (min 11) | CU-parallel; item code is variable-length |
| WP | `WPS00000000` | Variable | Hierarchical commodity codes; treat as opaque |
| EI | `EIUCDCANMANU` | Variable | Country+category suffix is opaque |
| CI | `CIS1010000000000I` | 17 | Fixed: seasonal(1)+owner(1)+industry(6)+occupation(6)+subcell(2)+periodicity(1) |

**Variable-length series (CW, WP, EI):** The `SeriesSchema.total_length` field must be
made `int | None`. When `None`, `decode_id` skips the length check, `build_id` returns
an error (cannot assemble variable-length IDs from segments), and `validate_series_id`
does not fail on length mismatch.

**CI segment layout verification:** Before coding, cross-reference `CIS1010000000000I`
against the column values `S, 1, 000000, 000000, 00, 99999, I, 01` from the ci.series
file. The `area_code` (`99999` = national) and `estimate_code` (`01`) appear in the series
file but do not have fixed positions in the series ID — exclude them from the schema
segments unless they can be confirmed at a specific character offset.

---

## Sub-Tasks

---

### Sub-Task 1 — Schema Infrastructure: `total_length: int | None`

**Status:** [ ] pending

**Intent:**
Three of the six new surveys (CW, WP, EI) have variable-length series IDs because their
item/commodity/country codes have no fixed width. The `SeriesSchema.total_length` field
is currently typed `int`, which forces every schema to declare a fixed ID length and causes
`decode_id` and `validate_series_id` to fail incorrectly on these series. Changing the
type to `int | None` and guarding the length-dependent code paths enables these surveys to
be added without breaking existing fixed-length schemas.

**Expected Outcomes:**
- `SeriesSchema.total_length` accepts `None`.
- `decode_id` does not raise or return an error for a series whose schema has `total_length=None`.
- `build_id` returns an informative error dict when called for a variable-length schema.
- `validate_series_id` tool does not emit a length-mismatch issue for variable-length series.
- All existing tests still pass (no change to SM, CE, LA, JT, CU, LN behaviour).

**Todo List:**
1. In `bls_series_schema.py`, change `SeriesSchema.total_length` from `int` to `int | None`.
2. In `decode_id`, wrap the length-check block: only check when `schema.total_length is not None`.
3. In `build_id`, add an early return error when `schema.total_length is None`:
   `{"error": "build_id is not supported for variable-length survey '{survey}'.", ...}`.
4. In `tools/validate_series_id.py`, find the length-mismatch check and skip it (or
   emit a non-blocking note rather than a `valid=False`) when `schema.total_length is None`.
5. Update the module docstring in `bls_series_schema.py` to list all 12 supported prefixes.
6. Run `ruff check src/` and fix any issues.
7. Run `pytest tests/test_bls_series_schema.py tests/test_tools_build_decode_validate.py`
   — all existing tests must still pass.

**Relevant Context:**
- [`src/example_server/bls_series_schema.py`](src/example_server/bls_series_schema.py) — `SeriesSchema` dataclass (line 42), `decode_id` (line 194), `build_id` (line 248)
- [`src/example_server/tools/validate_series_id.py`](src/example_server/tools/validate_series_id.py) — length check location TBD; read file before editing
- [`tests/test_bls_series_schema.py`](tests/test_bls_series_schema.py) — existing schema/build/decode tests
- [`tests/test_tools_build_decode_validate.py`](tests/test_tools_build_decode_validate.py) — existing tool tests

---

### Sub-Task 2 — Catalog Registry

**Status:** [ ] pending

**Intent:**
Add all new survey dimensions to `_REGISTRY` in `catalog.py` so code→name lookups work
for the six new surveys. The `bls_series_schema.py` segments reference catalog keys via
their `catalog_key` tuples; those tuples must resolve to loaded data.

**Expected Outcomes:**
- `catalog.get("pr", "sector")`, `catalog.get("mp", "measure")`, `catalog.get("cw", "seasonal")`, etc. all return non-empty dicts at runtime.
- No existing catalog entries are changed.
- New catalog smoke-test assertions pass.

**Todo List:**
1. Open `catalog.py` and add entries for every new dimension after the existing LN block:
   - **PR:** `("pr", "sector")`, `("pr", "class")`, `("pr", "measure")`, `("pr", "duration")`, `("pr", "seasonal")` — all `col0=code, col1=name`.
   - **MP:** `("mp", "sector")`, `("mp", "measure")`, `("mp", "duration")`, `("mp", "seasonal")` — all `col0=code, col1=name`.
   - **CW:** `("cw", "seasonal")`, `("cw", "periodicity")`, `("cw", "base")` — all `col0=code, col1=name`. (`cw.area` and `cw.item` are already registered; verify and leave them as-is.)
   - **WP:** `("wp", "seasonal")` — `col0=code, col1=name`. (`wp.group` and `wp.item` already registered; verify.)
   - **EI:** `("ei", "index")`, `("ei", "seasonal")` — both `col0=code, col1=name`.
   - **CI:** `("ci", "owner")`, `("ci", "industry")`, `("ci", "occupation")`, `("ci", "subcell")`, `("ci", "estimate")`, `("ci", "periodicity")`, `("ci", "seasonal")` — all `col0=code, col1=name`.
2. Verify `wp.item` registration uses `key_col=1, val_col=2` (the file has 3 columns: group_code, item_code, item_name). Correct if needed.
3. Run `ruff check src/example_server/catalog.py`.
4. Add smoke tests to `tests/test_catalog.py`:
   - `test_module_catalog_pr_sector_loaded` — `catalog.get("pr", "sector")` is non-empty
   - `test_module_catalog_mp_sector_loaded`
   - `test_module_catalog_cw_seasonal_loaded`
   - `test_module_catalog_wp_seasonal_loaded`
   - `test_module_catalog_ei_index_loaded`
   - `test_module_catalog_ci_owner_loaded`
   - `test_module_catalog_ci_industry_loaded`
5. Run `pytest tests/test_catalog.py` — all tests pass.

**Relevant Context:**
- [`src/example_server/catalog.py`](src/example_server/catalog.py) — `_REGISTRY` dict (line 28), existing survey blocks as pattern
- Local-cache files confirm column layout: all new attribute files are `col0=code, col1=name`.
- `wp.item` has 3 columns (group_code, item_code, item_name) — key is col1, value is col2.

---

### Sub-Task 3 — Series ID Schemas

**Status:** [ ] pending

**Intent:**
Add `SeriesSchema` definitions for all six new surveys and register them in `SCHEMAS`.
This enables `decode_id`, `build_id`, `validate_series_id`, and `get_schema` to handle
series IDs from these surveys.

**Expected Outcomes:**
- `get_schema("PRS30006013")` returns the PR schema with the correct prefix and segments.
- `decode_id("PRS30006013")` returns a dict with `prefix=="PR"` and a `segments` list where the `sector_code` value `"3000"` resolves to its catalog label.
- `decode_id("CIS1010000000000I")` returns `prefix=="CI"` with the owner segment resolving to `"Civilian workers"`.
- `build_id("PR", seasonal="S", sector_code="3000", class_code="6", measure_code="01", duration_code="3")` returns `"PRS30006013"`.
- `build_id("CW", ...)` returns an error dict (variable-length).
- All 12 prefixes appear in `SCHEMAS`.

**Todo List:**
1. Before writing schemas, manually verify CI segment positions by reading 5 rows from
   `ci.series` and aligning `CIS1010000000000I` against column values character by character.
   Confirm: `CI`(2) + `S`(seasonal,1) + `1`(owner,1) + `010000`? No — re-read and map carefully.
   Expected layout: `CI`+`S`(1)+`1`(owner,1)+`010000`(industry,6)+`000000`(occupation,6)+`00`(subcell,2)+`I`(periodicity,1) = 17 total. Verify `area_code` is absent from the ID itself (it's `99999` in the file column but may be implicit).
2. Add the following schemas to `bls_series_schema.py` (after `_LN`, before `SCHEMAS`):

   **`_PR`** — `total_length=11`
   - `seasonal` pos 0, len 1, catalog `("pr", "seasonal")`
   - `sector_code` pos 1, len 4, catalog `("pr", "sector")`
   - `class_code` pos 5, len 1, catalog `("pr", "class")`
   - `measure_code` pos 6, len 2, catalog `("pr", "measure")`
   - `duration_code` pos 8, len 1, catalog `("pr", "duration")`

   **`_MP`** — `total_length=10`
   - `seasonal` pos 0, len 1, catalog `("mp", "seasonal")`
   - `sector_code` pos 1, len 4, catalog `("mp", "sector")`
   - `measure_code` pos 5, len 2, catalog `("mp", "measure")`
   - `duration_code` pos 7, len 1, catalog `("mp", "duration")`

   **`_CW`** — `total_length=None` (variable)
   - `seasonal` pos 0, len 1, catalog `("cw", "seasonal")`
   - `periodicity_code` pos 1, len 1, catalog `("cw", "periodicity")`
   - `area_code` pos 2, len 4, catalog `("cw", "area")`
   - `item_code` pos 6, len 8, catalog `("cw", "item")`

   **`_WP`** — `total_length=None` (variable)
   - `seasonal` pos 0, len 1, catalog `("wp", "seasonal")`
   - `series_code` pos 1, len 8, opaque (no catalog key)

   **`_EI`** — `total_length=None` (variable)
   - `seasonal` pos 0, len 1, catalog `("ei", "seasonal")`
   - `index_code` pos 1, len 2, catalog `("ei", "index")`
   - `series_code` pos 3, len 9, opaque (no catalog key)

   **`_CI`** — `total_length=17`
   - `seasonal` pos 0, len 1, catalog `("ci", "seasonal")`
   - `owner_code` pos 1, len 1, catalog `("ci", "owner")`
   - `industry_code` pos 2, len 6, catalog `("ci", "industry")`
   - `occupation_code` pos 8, len 6, catalog `("ci", "occupation")`
   - `subcell_code` pos 14, len 2, catalog `("ci", "subcell")`
   - `periodicity_code` pos 16, len 1, catalog `("ci", "periodicity")`

3. Register all six in `SCHEMAS`: `"PR": _PR, "MP": _MP, "CW": _CW, "WP": _WP, "EI": _EI, "CI": _CI`.
4. Update the module docstring supported-surveys list.
5. Run `ruff check src/example_server/bls_series_schema.py`.
6. Add tests to `tests/test_bls_series_schema.py`:
   - Extend the `test_get_schema_known_prefix` parametrize list to include all six new prefixes.
   - `test_decode_pr_structure` — decode `"PRS30006013"`, check `prefix`, segment count, `sector_code` label resolves.
   - `test_decode_pr_build_roundtrip` — build then decode, confirm the assembled ID matches `"PRS30006013"`.
   - `test_decode_mp_structure` — decode `"MPU0011012"`, check `prefix` and segment count.
   - `test_decode_cw_structure` — decode `"CWSR0000SA0"`, check `prefix=="CW"`, `area_code=="0000"`.
   - `test_decode_ei_index_code` — decode an EI series, verify `index_code` segment resolves a label.
   - `test_decode_ci_structure` — decode `"CIS1010000000000I"`, check `prefix=="CI"`, owner label resolves.
   - `test_build_id_pr_valid` — build PR series from named parts, assert correct string and length.
   - `test_build_id_ci_valid` — build CI series, assert correct string.
   - `test_build_id_variable_length_returns_error` — parametrize over `["CW", "WP", "EI"]`; assert `build_id` returns a dict with `"error"`.
7. Run `pytest tests/test_bls_series_schema.py` — all tests pass.

**Relevant Context:**
- [`src/example_server/bls_series_schema.py`](src/example_server/bls_series_schema.py) — `_LN` (line 167) and `SCHEMAS` (line 179) as insertion points
- [`src/example_server/local-cache/pr.series`](src/example_server/local-cache/pr.series) — cross-reference for PR segment layout
- [`src/example_server/local-cache/ci.series`](src/example_server/local-cache/ci.series) — cross-reference for CI segment layout

---

### Sub-Task 4 — Flagship Series Entries

**Status:** [ ] pending

**Intent:**
Add curated flagship entries for all six new surveys to `bls_flagship_series.py`. The
existing test `test_each_survey_has_at_least_six_entries` requires at least 6 entries per
survey, and `test_all_surveys_represented` requires all surveys to be present in
`FLAGSHIP_SERIES`. Both tests need updating. Flagship entries power `suggest_series` and
`get_series_metadata` for the new surveys.

**Expected Outcomes:**
- `FLAGSHIP_SERIES` contains at least 6 entries each for PR, MP, CW, WP, EI, and CI.
- All flagship entries have non-empty `series_id`, `survey`, `survey_name`, `description`, `keywords` (≥1), `notes`, `concept`, `measure_type`, and `unit`.
- `measure_type` is one of `{"level", "rate", "index", "dollar_amount"}` for all entries.
- Existing `test_all_surveys_represented` and `test_entry_has_required_fields` tests are updated to include the new surveys.

**Todo List:**
1. Update `test_all_surveys_represented` in `tests/test_bls_flagship_series.py` to use `>=` (superset check) rather than `==`, so adding future surveys doesn't require another test change.
2. Update `test_each_survey_has_at_least_six_entries` to include all 12 surveys in its iteration.
3. Update `test_entry_has_required_fields` to allow all 12 surveys in the `entry.survey in (...)` assertion.
4. Verify that the candidate series IDs below exist in the local cache `.series` files before hardcoding them.
5. Add the following entry lists to `bls_flagship_series.py` (after `_LN_ENTRIES`, before `FLAGSHIP_SERIES`):

   **`_PR_ENTRIES`** (≥6): manufacturing employment index/level, nonfarm business labor productivity index/level, unit labor costs, compensation per hour. Use `series_id` values from `pr.series`. `measure_type` is `"index"` for index variants, `"level"` for level variants, `"dollar_amount"` for compensation per hour.

   **`_MP_ENTRIES`** (≥6): total factor productivity indexes for agriculture, mining, utilities, construction, durable manufacturing, nondurable manufacturing. Use `series_id` values from `mp.series`. All `measure_type="index"`.

   **`_CW_ENTRIES`** (≥6): all items SA, all items NSA, energy SA, food SA, core (less food and energy) SA, shelter SA. Use `series_id` values from `cw.series`. All `measure_type="index"`, `unit="index 1982-84=100"`.

   **`_WP_ENTRIES`** (≥6): all commodities SA/NSA, farm products, processed foods, industrial commodities, fuels/related products/power, metals and metal products. Use `series_id` values from `wp.series`. All `measure_type="index"`, `unit="index 1982=100"`.

   **`_EI_ENTRIES`** (≥6): total import price index (NSA), total export price index (NSA), import prices by end-use (industrial supplies, capital goods, consumer goods), export prices by end-use. Use `series_id` values from `ei.series`. All `measure_type="index"`.

   **`_CI_ENTRIES`** (≥6): total compensation civilian workers (index and % change), wages and salaries civilian workers, total benefits civilian workers, total compensation private industry, total compensation state and local government, total compensation all occupations. Use `series_id` values from `ci.series`. `measure_type="index"` for index series, `"rate"` for percent-change series.

6. Append all six lists to the `FLAGSHIP_SERIES` concatenation at the bottom of the file.
7. Update the module docstring and `FlagshipEntry.survey` docstring to list all 12 survey prefixes.
8. Run `ruff check src/example_server/bls_flagship_series.py`.
9. Run `pytest tests/test_bls_flagship_series.py` — all tests pass (including updated ones).
10. Add new test functions:
    - `test_pr_flagship_min_six_entries` — at least 6 PR entries
    - `test_mp_flagship_entries_are_index` — all MP entries have `measure_type=="index"`
    - `test_cw_flagship_all_items_sa` — verify the SA all-items CPI-W entry is present and correct
    - `test_wp_flagship_entries` — at least 6 WP entries, all `measure_type=="index"`
    - `test_ei_flagship_entries` — at least 6 EI entries
    - `test_ci_flagship_entries` — at least 6 CI entries

**Relevant Context:**
- [`src/example_server/bls_flagship_series.py`](src/example_server/bls_flagship_series.py) — `_LN_ENTRIES` (line 587) and `FLAGSHIP_SERIES` (line 734) as insertion points
- [`tests/test_bls_flagship_series.py`](tests/test_bls_flagship_series.py) — `test_all_surveys_represented` (line 19), `test_each_survey_has_at_least_six_entries` (line 24), `test_entry_has_required_fields` (line 36) all need updating

---

### Sub-Task 5 — Search Tool Coverage

**Status:** [ ] pending

**Intent:**
Extend `tools/search_series.py` to route queries about the six new surveys to the
appropriate per-survey search functions, just as SM, CE, LA, JT, CU, and LN are handled.
This makes the `search_series` tool useful for all 12 supported surveys.

**Expected Outcomes:**
- A query for `"productivity manufacturing"` with `survey="PR"` returns results with series IDs starting with `"PR"`.
- A query for `"cpi wage earners"` with `survey="CW"` returns results with series IDs starting with `"CW"`.
- A query for `"employer costs compensation"` with `survey="CI"` returns results starting with `"CI"`.
- Queries without explicit survey filter use `_SURVEY_HINTS` to auto-detect the new surveys.
- The `survey` parameter annotation is updated to list all 12 prefixes.
- The `_detect_survey` function falls back to searching all `SCHEMAS` keys (now 12) when no hint matches.

**Todo List:**
1. Add new keyword → survey mappings to `_SURVEY_HINTS` in `search_series.py`:
   - `"productivity": "PR"`, `"labor productivity": "PR"`
   - `"multifactor": "MP"`, `"total factor": "MP"`, `"tfp": "MP"`
   - `"cpi-w": "CW"`, `"wage earners": "CW"`, `"clerical workers": "CW"`
   - `"ppi": "WP"`, `"producer price": "WP"`, `"commodity price": "WP"`
   - `"import price": "EI"`, `"export price": "EI"`, `"international price": "EI"`
   - `"employee compensation": "CI"`, `"employer costs": "CI"`, `"ecec": "CI"`
2. Add a `_CW_ITEM_HINTS` dict analogous to `_CU_ITEM_HINTS`:
   `{"all items": "SA0", "cpi-w": "SA0", "energy": "SA0E", "food": "SAF", "core": "SA0L1E"}`.
3. Implement per-survey search functions:
   - `_search_pr(query, seasonal, limit)` — builds one default PR series via `build_id("PR", seasonal=seasonal, sector_code="3000", class_code="6", measure_code="01", duration_code="3")`. Returns a single result.
   - `_search_mp(query, limit)` — delegates to `search_flagship(query, limit=limit)`, filters `entry.survey == "MP"`, returns decoded results.
   - `_search_cw(query, seasonal, limit)` — parallel to `_search_cu`: resolves item from `_CW_ITEM_HINTS`, uses area `"0000"`, builds `build_id("CW", ...)`. Because CW is variable-length, `build_id` will error; instead construct the ID directly: `"CW" + seasonal + "R" + "0000" + item` and call `_make_result`.
   - `_search_wp(query, limit)` — delegates to `search_flagship`, filters `entry.survey == "WP"`.
   - `_search_ei(query, limit)` — delegates to `search_flagship`, filters `entry.survey == "EI"`.
   - `_search_ci(query, seasonal, limit)` — delegates to `search_flagship`, filters `entry.survey == "CI"`, or builds a default CI series via `build_id("CI", ...)` for `owner_code="1"`, all-industry, all-occupation.
4. Wire up new branches in the `for sv in surveys_to_try` loop inside `search_series`:
   `elif sv == "PR"`, `elif sv == "MP"`, `elif sv == "CW"`, `elif sv == "WP"`, `elif sv == "EI"`, `elif sv == "CI"`.
5. Update the `survey` parameter annotation string from `'SM', 'CE', 'LA', 'JT', 'CU', or 'LN'` to include all 12 prefixes.
6. Run `ruff check src/example_server/tools/search_series.py`.
7. Add tests to `tests/test_tools_search_suggest.py`:
   - Extend `_fake_catalog_sm_chicago()` (or create a new `_fake_catalog_full()`) with fake catalog entries for all new surveys (pr.sector, mp.sector, cw.area, cw.item, ei.index, ci.owner, ci.industry, etc. — see relevant context for complete list).
   - `test_search_series_pr_productivity` — `survey="PR"`, query `"productivity manufacturing"` → count ≥ 1, series IDs start with `"PR"`.
   - `test_search_series_cw_wage_earners` — `survey="CW"`, query `"cpi wage earners all items"` → count ≥ 1.
   - `test_search_series_ci_compensation` — `survey="CI"`, query `"employer costs compensation"` → count ≥ 1.
   - `test_search_series_hint_producer_price` — no explicit survey, query `"producer price index"` → results include WP series.
   - `test_search_series_hint_import_price` — no explicit survey, query `"import price"` → results include EI series.
8. Run `pytest tests/test_tools_search_suggest.py` — all tests pass.

**Relevant Context:**
- [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py) — `_SURVEY_HINTS` (line 74), `_search_cu` (line 393) as pattern for CW, loop dispatch (line 163)
- Fake catalog entries needed in tests: `("pr", "seasonal")`, `("pr", "sector")`, `("pr", "class")`, `("pr", "measure")`, `("pr", "duration")`, `("mp", "seasonal")`, `("mp", "sector")`, `("mp", "measure")`, `("mp", "duration")`, `("cw", "area")`, `("cw", "item")`, `("cw", "seasonal")`, `("cw", "periodicity")`, `("wp", "seasonal")`, `("wp", "group")`, `("ei", "seasonal")`, `("ei", "index")`, `("ci", "owner")`, `("ci", "industry")`, `("ci", "occupation")`, `("ci", "subcell")`, `("ci", "periodicity")`, `("ci", "seasonal")`

---

### Sub-Task 6 — Build / Decode / Validate Tool Tests

**Status:** [ ] pending

**Intent:**
Extend the build/decode/validate tool tests to exercise the six new surveys through the
MCP tool layer, mirroring the existing coverage for SM, CE, LA.

**Expected Outcomes:**
- `build_series_id` tool correctly assembles PR and CI series IDs.
- `decode_series_id` tool correctly decodes PR and CI series IDs with resolved labels.
- `validate_series_id` tool returns `valid=True` for well-formed PR and CI series IDs.
- `build_series_id` returns an error for CW (variable-length), not a Python exception.
- `validate_series_id` returns `valid=True` for a CW series (no spurious length failure).

**Todo List:**
1. Add tests to `tests/test_tools_build_decode_validate.py`:
   - `test_build_series_id_valid_pr` — build `("PR", seasonal_adjustment="S", sector_code="3000", class_code="6", measure_code="01", duration_code="3")` → `series_id=="PRS30006013"`, `decoded["prefix"]=="PR"`.
   - `test_build_series_id_valid_ci` — build CI with all required fields → series ID starts with `"CI"`, length == 17.
   - `test_build_series_id_variable_length_error` — parametrize `["CW", "WP", "EI"]`; call `build_series_id` with minimal kwargs → result has `"error"` key.
   - `test_decode_series_id_pr` — decode `"PRS30006013"` → `prefix=="PR"`, `sector_code` label resolves (non-None).
   - `test_decode_series_id_ci` — decode `"CIS1010000000000I"` → `prefix=="CI"`, owner segment label is `"Civilian workers"`.
   - `test_validate_valid_pr_series` — validate `"PRS30006013"` → `valid=True`, `issues==[]`.
   - `test_validate_valid_ci_series` — validate `"CIS1010000000000I"` → `valid=True`.
   - `test_validate_variable_length_cw_no_length_failure` — validate `"CWSR0000SA0"` → `valid=True` (or if there are catalog issues, no length-related issues in `result["issues"]`).
2. Run `pytest tests/test_tools_build_decode_validate.py` — all tests pass.

**Relevant Context:**
- [`tests/test_tools_build_decode_validate.py`](tests/test_tools_build_decode_validate.py) — existing SM/CE tests as pattern
- The `_capture` helper already defined at the top of this test file — reuse it.

---

### Sub-Task 7 — Surveys Resource and Assistant Prompt

**Status:** [ ] pending

**Intent:**
The `bls://surveys/overview` resource and `bls_assistant` prompt are the entry points that
LLM clients use to discover what data this server provides. Both currently list only the
original six surveys. Adding the new surveys here ensures an AI client can discover and
correctly use the new series without hallucinating capabilities.

**Expected Outcomes:**
- `bls://surveys/overview` includes PR, MP, CW, WP, EI, and CI in its survey index.
- `bls://surveys/PR` (and each new prefix) returns a fully populated detail page.
- The `bls_assistant` prompt table lists all 12 supported surveys with key measures.
- Existing resource tests still pass.

**Todo List:**
1. Open `src/example_server/resources/bls_surveys.py` and read the full `_SURVEY_META` dict.
2. Add six new entries to `_SURVEY_META`, one per survey, following the exact structure of the existing entries (keys: `full_name`, `program`, `update_frequency`, `seasonal_note`, `unit_note`, `data_api_note`, `catalog_dimensions`, `tool_guidance`, plus any survey-specific notes):
   - **PR:** quarterly release, index and level measures, build_series_id supported.
   - **MP:** annual release, index measures only, series IDs are opaque / use suggest_series.
   - **CW:** monthly release (same as CU), index 1982-84=100, note that build_series_id is NOT supported (variable-length).
   - **WP:** monthly release, commodity price index 1982=100, series IDs are hierarchical / use suggest_series.
   - **EI:** monthly release, import and export price indexes, series IDs are opaque / use suggest_series.
   - **CI:** quarterly release, index and percent-change measures, build_series_id supported.
3. Open `src/example_server/prompts/bls_assistant.py` and extend the `## Supported Surveys` table to include the six new rows:
   - `| PR | Productivity and Costs | Labor productivity, unit labor costs |`
   - `| MP | Multifactor Productivity | Total factor productivity by sector |`
   - `| CW | Consumer Price Index — Urban Wage Earners | CPI-W, inflation for wage earners |`
   - `| WP | PPI Commodity Data | Producer price indexes by commodity |`
   - `| EI | International Price Program | Import and export price indexes |`
   - `| CI | Employer Costs for Employee Compensation | Total compensation, wages, benefits |`
4. Run `ruff check src/example_server/resources/ src/example_server/prompts/`.
5. Run `pytest tests/test_resources_bls_surveys.py` — all existing resource tests pass.

**Relevant Context:**
- [`src/example_server/resources/bls_surveys.py`](src/example_server/resources/bls_surveys.py) — `_SURVEY_META` dict (line 44); `_build_overview` and `_build_survey_detail` functions consume it automatically — no logic changes needed, only new metadata entries.
- [`src/example_server/prompts/bls_assistant.py`](src/example_server/prompts/bls_assistant.py) — supported surveys table (line 50).
- [`tests/test_resources_bls_surveys.py`](tests/test_resources_bls_surveys.py) — read before editing to understand what it asserts.

---

### Sub-Task 8 — Full Suite Validation

**Status:** [ ] pending

**Intent:**
Run the complete test suite to confirm all changes integrate cleanly, no regressions were
introduced, and all new tests pass. Also run `ruff check` across the full source tree.

**Expected Outcomes:**
- `ruff check src/` exits with code 0 and no warnings.
- `pytest tests/` (without `--run-live`) exits with code 0 and all tests pass.
- No new skipped or xfailed tests beyond the pre-existing live-test skips.

**Todo List:**
1. Run `ruff check src/` — fix any remaining issues.
2. Run `pytest tests/ -v` — confirm all tests pass.
3. If any test fails, trace the failure to the specific sub-task and fix before marking this task done.

**Relevant Context:**
- `pyproject.toml` ruff config: rules `["E", "F", "I"]`, line-length 88, target Python 3.11.
- `pyproject.toml` pytest config: `testpaths = ["tests"]`, `asyncio_mode = "auto"`.
- Live tests are skipped unless `--run-live` is passed — this is expected and acceptable.
