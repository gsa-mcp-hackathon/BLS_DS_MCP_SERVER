# LN Series Integration Plan

## Top-Level Overview

New BLS local-cache files have been added for the **LN (Current Population Survey / Labor Force Statistics)** survey, along with files for additional surveys (`ci`, `ei`, `mp`, `pr`, `wp`). This plan focuses on incorporating the LN data — the highest-value gap — into the three MCP tool layers: catalog lookups, series metadata/decoding, and flagship series suggestions.

**Critical design constraint:** The BLS documentation (`ln.txt`, Section 4) explicitly states that LN series IDs **cannot be structurally decoded** from their character positions. Only the first 3 characters are meaningful: `LNS` = Seasonally Adjusted, `LNU` = Not Seasonally Adjusted. The remaining digits are opaque identifiers. This means LN cannot get a `SeriesSchema` with segments the way SM/CE/LA/JT/CU have. Instead, the `ln.series` file (which maps series IDs to human-readable titles) is the authoritative lookup mechanism.

**Scope of this plan:**
1. Register LN catalog dimensions in `catalog.py` so they are accessible
2. Add an LN schema to `bls_series_schema.py` — opaque body, series-file-driven label lookup
3. Add curated LN flagship entries to `bls_flagship_series.py` covering key CPS metrics
4. Add LN search hints to `search_series.py` so participation rate and unemployment questions surface LN series
5. Update existing tests and add new tests to cover the above

**Out of scope:** Full integration of `ci`, `ei`, `mp`, `pr` surveys — those have their own series files but are lower priority than LN CPS metrics.

---

## Sub-Tasks

---

### Sub-Task 1 — Register LN catalog dimensions in `catalog.py`

**Intent:**
Make the LN mapping files accessible through the shared `catalog.get()` and `catalog.search()` interface. This is the foundation all other sub-tasks depend on. The most useful dimensions for lookup and search are `seasonal`, `lfst` (labor force status), `sexs`, `ages`, `periodicity`, and `series` (series_id → title).

**Expected Outcomes:**
- `catalog.get("ln", "seasonal")` returns `{"S": "Seasonally Adjusted", "U": "Not Seasonally Adjusted"}`
- `catalog.get("ln", "lfst")` returns a dict with codes like `"13"` → `"Civilian labor force participation rate"`
- `catalog.get("ln", "series")` returns a dict mapping series_id → series_title (from `ln.series`, col 0 → col 3)
- `catalog.get("ln", "sexs")`, `catalog.get("ln", "ages")`, `catalog.get("ln", "periodicity")` all return populated dicts
- All existing catalog tests continue to pass

**Todo List:**
- [ ] In `catalog.py` `_REGISTRY`, add entries for `("ln", "seasonal")`, `("ln", "lfst")`, `("ln", "sexs")`, `("ln", "ages")`, `("ln", "periodicity")`, and `("ln", "series")` (series file uses col 0 as key, col 3 as title value)
- [ ] Verify the column indices: `ln.series` header is `series_id[0] … series_title[3]` — use `key_col=0, val_col=3`

**Relevant Context:**
- [`src/example_server/catalog.py`](src/example_server/catalog.py) — `_REGISTRY` dict at line 28
- [`src/example_server/local-cache/ln.series`](src/example_server/local-cache/ln.series) — first column is series_id (padded to 17 chars), col 3 is series_title
- [`src/example_server/local-cache/ln.lfst`](src/example_server/local-cache/ln.lfst) — 2-column TSV, key=`lfst_code`, val=`lfst_text`
- Pattern: other survey dimensions like `("jt", "dataelement")` follow identical TSV structure

**Status:** `[ ] pending`

---

### Sub-Task 2 — Add LN schema to `bls_series_schema.py`

**Intent:**
Allow `get_series_metadata` and `decode_id` to recognize `LN` prefixed series without returning an "unrecognised prefix" error. Because the body of an LN series ID is opaque (per BLS documentation), the schema has only two meaningful segments: the seasonal indicator (1 char) and the opaque body (remainder). The series title lookup should use the `ln.series` catalog to resolve a human-readable label for the full series ID.

**Expected Outcomes:**
- `get_schema("LNS11300000")` returns an LN schema (not `None`)
- `decode_id("LNS11300000")` returns `valid: True` with segments including `{"name": "seasonal", "value": "S", "label": "Seasonally Adjusted"}` and `{"name": "series_code", "value": "11300000", "label": "(Seas) Labor Force Participation Rate"}`
- `get_series_metadata("LNS11300000")` returns `valid: True` with `prefix: "LN"`, not an error
- The `SCHEMAS` dict error message in `get_series_metadata` now lists `LN` among supported prefixes
- All existing schema tests continue to pass

**Todo List:**
- [ ] Define `_LN = SeriesSchema(...)` in `bls_series_schema.py` with `prefix="LN"`, `total_length=12` (LN + 1 seasonal + 8-digit opaque body = 11; check actual lengths from `ln.series`), and two segments: `seasonal` (length 1, `catalog_key=("ln", "seasonal")`) and `series_code` (opaque body, no catalog_key for segment-level lookup — the title is resolved from the whole series ID via flagship or series file)
- [ ] Add `"LN": _LN` to the `SCHEMAS` dict
- [ ] Update the docstring at the top of `bls_series_schema.py` to include LN in the supported surveys list

**Design note on title resolution:** Because the opaque body cannot be decoded segment-by-segment, the `series_code` segment will have `catalog_key=("ln", "series")` with the lookup key being the full original series ID (stripped of trailing whitespace from the catalog), not just the body. This requires a small adaptation in `decode_id` — or alternatively a `catalog_key=None` for the body segment, relying on the flagship entry or `get_series_metadata` to supply the label. The simpler path: use `catalog_key=None` for the body segment, so decode_id returns `label: null` for the body, but `get_series_metadata` enriches it with the series title from the `ln.series` catalog.

**Relevant Context:**
- [`src/example_server/bls_series_schema.py`](src/example_server/bls_series_schema.py) — `SCHEMAS` at line 160
- LN series IDs from `ln.series`: `LNS11000000` = 11 chars, `LNS11000000Q` = 12 chars (with periodicity suffix). Standard monthly series are 11 chars, quarterly append `Q`. Total length may be variable — check and decide if `total_length` should be 11 (monthly) with quarterly treated as a variant, or support both.
- The `ln.series` catalog key is the stripped series_id — `LNS11000000      ` → `LNS11000000` after strip

**Status:** `[ ] pending`

---

### Sub-Task 3 — Add LN flagship entries to `bls_flagship_series.py`

**Intent:**
Add a new `_LN_ENTRIES` list with curated entries for the most important CPS/LN series so that `suggest_series("labor force participation rate")` and similar queries produce correct results. These are the canonical series an economist or journalist would ask about.

**Expected Outcomes:**
- `search_flagship("labor force participation rate")` returns at least one LN entry with `series_id="LNS11300000"`
- `search_flagship("unemployment rate")` continues to return LA entries AND now also returns `LNS14000000` (CPS U-3)
- `search_flagship("employment population ratio")` returns `LNS12300000`
- `suggest_series("what is the labor force participation rate?")` returns LN entries with `unit="percent"` and `measure_type="rate"`
- The existing `test_all_five_surveys_represented` test **must be updated** to include `LN` (currently asserts exactly `{"SM", "CE", "LA", "JT", "CU"}`)
- All new LN entries pass the parametrized `test_all_entries_have_concept`, `test_all_entries_have_measure_type`, `test_all_entries_have_unit` tests

**Proposed entries (minimum viable set):**
| series_id | description | concept | measure_type | unit |
|---|---|---|---|---|
| `LNS11300000` | Labor Force Participation Rate — Seasonally Adjusted | `labor_force_participation_rate` | `rate` | `percent` |
| `LNU01300000` | Labor Force Participation Rate — Not Seasonally Adjusted | `labor_force_participation_rate` | `rate` | `percent` |
| `LNS14000000` | Unemployment Rate (U-3) — Seasonally Adjusted (CPS) | `unemployment_rate` | `rate` | `percent` |
| `LNU04000000` | Unemployment Rate (U-3) — Not Seasonally Adjusted (CPS) | `unemployment_rate` | `rate` | `percent` |
| `LNS12300000` | Employment-Population Ratio — Seasonally Adjusted | `employment_population_ratio` | `rate` | `percent` |
| `LNS12000000` | Civilian Employment Level — Seasonally Adjusted | `civilian_employment` | `level` | `thousands of persons` |
| `LNS11000000` | Civilian Labor Force Level — Seasonally Adjusted | `civilian_labor_force` | `level` | `thousands of persons` |

**Todo List:**
- [ ] Add `_LN_ENTRIES: list[FlagshipEntry] = [...]` block in `bls_flagship_series.py` with at minimum the 7 entries above (at least 6 required by `test_each_survey_has_at_least_six_entries`)
- [ ] Add `_LN_ENTRIES` to the `FLAGSHIP_SERIES` concatenation
- [ ] Update `test_all_five_surveys_represented` in `tests/test_bls_flagship_series.py` to assert `{"SM", "CE", "LA", "JT", "CU", "LN"}`
- [ ] Update `test_entry_has_required_fields` survey allowlist to include `"LN"`

**Relevant Context:**
- [`src/example_server/bls_flagship_series.py`](src/example_server/bls_flagship_series.py) — `FLAGSHIP_SERIES` at line 584, entry pattern from `_CU_ENTRIES` at line 477
- [`tests/test_bls_flagship_series.py`](tests/test_bls_flagship_series.py) — `test_all_five_surveys_represented` at line 19, `test_entry_has_required_fields` at line 36

**Status:** `[ ] pending`

---

### Sub-Task 4 — Add LN search support to `search_series.py`

**Intent:**
Wire up LN series detection in the `search_series` tool so that queries about labor force participation rate, CPS unemployment, or employment-population ratio return LN series IDs rather than dead ends.

**Expected Outcomes:**
- `search_series("labor force participation rate")` returns results including `LNS11300000`
- `search_series("cps unemployment rate")` returns `LNS14000000`
- `search_series("employment population ratio")` returns `LNS12300000`
- Survey detection keywords `"participation"`, `"cps"`, `"labor force"`, `"employment population"` map to `"LN"`
- All existing `search_series` tests continue to pass

**Todo List:**
- [ ] Add `"LN"` entries to `_SURVEY_HINTS` in `search_series.py` for keywords: `"participation rate"`, `"cps"`, `"labor force participation"`, `"employment population ratio"`, `"civilian employment"`, `"civilian labor force"`
- [ ] Write `_search_ln(query, seasonal, limit)` function that returns candidate LN series from the flagship table by calling `search_flagship(query, limit=limit)` filtered to `survey == "LN"`, returning them as `_make_result`-shaped dicts
- [ ] Add `"LN": _search_ln` to the survey dispatch in `search_series`

**Design note:** Because LN IDs are opaque (no build_id support), `_search_ln` should use the flagship table as its candidate pool. This avoids any need to build IDs from scratch and keeps the catalog-lookup approach consistent with the suggestion-first philosophy.

**Relevant Context:**
- [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py) — `_SURVEY_HINTS`, survey dispatch, `_make_result` helper
- [`src/example_server/bls_flagship_series.py`](src/example_server/bls_flagship_series.py) — `search_flagship` function

**Status:** `[ ] pending`

---

### Sub-Task 5 — Update and extend tests

**Intent:**
Ensure all four layers of changes are covered by tests that pass under the existing test harness (pytest, ruff-clean). Fix any existing tests broken by the schema/flagship changes, and add targeted new tests for LN behavior.

**Expected Outcomes:**
- All existing tests pass with no regressions
- New tests confirm LN series are recognized by `get_series_metadata`
- New tests confirm `suggest_series` returns LN entries for participation rate queries
- New tests confirm `search_flagship` finds LN entries by keyword
- Ruff linting passes with no new violations

**Todo List:**
- [ ] In `tests/test_bls_flagship_series.py`: update `test_all_five_surveys_represented` to include `"LN"`, update `test_entry_has_required_fields` survey allowlist
- [ ] In `tests/test_bls_flagship_series.py`: add `test_search_flagship_participation_rate` asserting LN entry is returned
- [ ] In `tests/test_tools_get_series.py`: add `test_get_series_metadata_ln_series` asserting `valid: True` and `prefix: "LN"` for `"LNS11300000"`
- [ ] In `tests/test_tools_search_suggest.py`: add `test_suggest_series_participation_rate` asserting at least one LN result with `unit="percent"`
- [ ] Run `pytest` and `ruff check src/ tests/` to confirm all pass

**Relevant Context:**
- [`tests/test_bls_flagship_series.py`](tests/test_bls_flagship_series.py)
- [`tests/test_tools_get_series.py`](tests/test_tools_get_series.py)
- [`tests/test_tools_search_suggest.py`](tests/test_tools_search_suggest.py)

**Status:** `[ ] pending`
