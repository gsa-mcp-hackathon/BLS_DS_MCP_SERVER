# BLS Top-Picks Full Coverage Plan

## Top-Level Overview

The file [`src/example_server/local-cache/bls_top_picks`](src/example_server/local-cache/bls_top_picks)
lists **29 authoritative BLS series** across four economic categories
(Employment, Productivity, Price Indexes, Compensation).
These are BLS's own published "top picks" — the headline series that the
bureau highlights for public use.

**Current state:** Only 9 of the 29 series IDs are present in
[`src/example_server/bls_flagship_series.py`](src/example_server/bls_flagship_series.py)
(the in-process discovery table that backs `suggest_series`, `get_series_metadata`,
and the `bls://surveys/{survey_code}` resource).  The remaining 20 are undiscoverable,
unvalidatable through metadata tools, and have no test coverage asserting they exist.
Additionally, there is no machine-readable loader for the `bls_top_picks` file itself
and no inventory test that cross-checks the file against the flagship table, so the gap
could silently grow again.

**Goal:** Every series in `bls_top_picks` must be:
1. Present as a [`FlagshipEntry`](src/example_server/bls_flagship_series.py:21) in the flagship table with correct metadata.
2. Parseable by [`decode_id()`](src/example_server/bls_series_schema.py:297) without an `"error"` key.
3. Discoverable via `suggest_series` and `get_series_metadata` tools.
4. Retrievable via `get_series_data` (live; relies on BLS API availability).
5. Protected by an inventory test that will fail if any top-picks series is later dropped.

**Approach:** Minimal extension of existing abstractions — no new files except
one new test file and a small top-picks loader module.  All changes extend
`bls_flagship_series.py`, `bls_series_schema.py` (if schema gaps are found),
the `catalog.py` reference tables, and add a new test file
`tests/test_bls_top_picks_coverage.py`.

**Program families covered by bls_top_picks:**

| Prefix | Survey | Missing count |
|--------|--------|:---:|
| LN | Labor Force Statistics (CPS) | 1 |
| CE | Current Employment Statistics | 3 |
| PR | Productivity and Costs | 3 |
| MP | Multifactor Productivity | 2 |
| CU | Consumer Price Index — All Urban | 1 |
| CW | Consumer Price Index — Wage Earners | 1 |
| WP | PPI Commodity / Final Demand | 5 |
| EI | International Price Program | 0 |
| CI | Employment Cost Index (ECEC) | 3 |

---

## Precise Gap Inventory

The table below is the authoritative gap list driving all subtasks.
Series marked **MISSING** are absent from `FLAGSHIP_SERIES`.

| # | Series ID | Category | Survey | Status |
|---|-----------|----------|--------|--------|
| 1 | LNS13000000 | Employment | LN | **MISSING** |
| 2 | CES0500000002 | Employment | CE | **MISSING** |
| 3 | CES0500000007 | Employment | CE | **MISSING** |
| 4 | CES0500000008 | Employment | CE | **MISSING** |
| 5 | PRS85006092 | Productivity | PR | **MISSING** |
| 6 | PRS85006112 | Productivity | PR | **MISSING** |
| 7 | PRS85006152 | Productivity | PR | **MISSING** |
| 8 | MPU4910012 | Productivity | MP | **MISSING** |
| 9 | MPU4900012 | Productivity | MP | **MISSING** |
| 10 | CUUR0000AA0 | Price Indexes | CU | **MISSING** |
| 11 | CWUR0000SA0 | Price Indexes | CW | **present in CU block** (survey mislabeled) |
| 12 | CWUR0000SA0L1E | Price Indexes | CW | **MISSING** |
| 13 | WPSFD4 | Price Indexes | WP | **MISSING** |
| 14 | WPUFD4 | Price Indexes | WP | **MISSING** |
| 15 | WPUFD49104 | Price Indexes | WP | **MISSING** |
| 16 | WPUFD49116 | Price Indexes | WP | **MISSING** |
| 17 | WPUFD49207 | Price Indexes | WP | **MISSING** |
| 18 | CIU1010000000000A | Compensation | CI | **MISSING** |
| 19 | CIU2010000000000A | Compensation | CI | **MISSING** |
| 20 | CIU2020000000000A | Compensation | CI | **MISSING** |

Existing but correct: LNS11000000, LNS12000000, LNS14000000, CES0000000001,
CES0500000003, CUUR0000SA0, CUUR0000SA0L1E, EIUIR, EIUIQ.

**Additional schema/metadata issues to fix in the same pass:**
- `CWUR0000SA0` already exists in the flagship table but is filed under the CU block
  with `survey="CU"`. The BLS series prefix is `CW`, so this entry should carry
  `survey="CW"` and live in `_CW_ENTRIES`.  Confirm before changing — if the existing
  entry in the CU block uses `series_id="CWUR0000SA0"` with `survey="CU"` that is a
  metadata error; the actual BLS page for that ID uses the CW (Wage Earners) program.
  (Inspection confirmed: line 574 sets `survey="CU"` on `CWUR0000SA0` — this must be
  corrected to `survey="CW"`.)
- `CIU…A` series use periodicity code `A` ("12-month percent change") which is not
  listed in the existing CI schema's periodicity catalog.  The schema's `periodicity_code`
  segment must accept `A` without returning `label: null` as a silent failure.
- PPI Final Demand series (`WPSFD4`, `WPUFD4`, `WPUFD49xxx`) are WP-prefix IDs but
  use a "Final Demand" commodity code structure that is semantically different from the
  commodity PPI IDs already in the flagship table.  They must be added to `_WP_ENTRIES`
  with correct unit and measure_type.
- `PRS85006092`, `PRS85006112`, `PRS85006152` use the existing PR format
  (prefix PR, sector 8500, class 6, various measure codes) but were simply never added
  to `_PR_ENTRIES`.
- `MPU4910012` and `MPU4900012` are 10-char MP-prefix IDs: sector 4910/4900, measure 01,
  duration 2 — consistent with the MP schema.  They were never added to `_MP_ENTRIES`.

---

## Sub-Tasks

---

### Sub-Task 1 — Add a Top-Picks Loader Module

**Status:** `[ ] pending`

**Intent:**
Create a small, standalone module that parses `bls_top_picks` into a structured
list at import time.  This becomes the single authoritative source of truth for
"which series IDs are top picks" — used directly by the new coverage test and
optionally by the `suggest_series` or `bls://surveys/overview` resource in future.
No existing tools are modified in this subtask.

**Expected Outcomes:**
- A new module `src/example_server/bls_top_picks.py` with:
  - A `TopPickEntry` dataclass (fields: `category`, `title`, `series_id`).
  - A `TOP_PICKS: list[TopPickEntry]` constant populated by parsing the file at
    import time (resolved relative to the module file so it always finds the cache).
  - A `TOP_PICKS_BY_ID: dict[str, TopPickEntry]` index for O(1) lookup.
  - A `get_top_pick(series_id)` function.
- The parser handles:
  - Category header lines (no `-` separator) → update current category.
  - Series lines of the form `Title — SERIES_ID` and `Title - SERIES_ID` (both dash variants).
  - Blank lines → skip.
  - Raises `ValueError` on a malformed line so regressions are caught at import time.
- No dependency on external libraries; uses only `pathlib` and `dataclasses`.

**Todo List:**
1. Create `src/example_server/bls_top_picks.py` with `TopPickEntry`, `TOP_PICKS`,
   `TOP_PICKS_BY_ID`, and `get_top_pick()`.
2. Write a minimal docstring explaining provenance (points to the BLS top-picks page URL)
   and how to refresh (re-download the file from BLS and update the cache).
3. Run `uv run ruff check src/example_server/bls_top_picks.py` — fix any issues.
4. Run `uv run pytest tests/ -v` — confirm no existing tests break.

**Relevant Context:**
- File to parse: [`src/example_server/local-cache/bls_top_picks`](src/example_server/local-cache/bls_top_picks)
- Pattern to follow for module-level constants: [`bls_flagship_series.py`](src/example_server/bls_flagship_series.py:1704)
- Path resolution pattern: use `pathlib.Path(__file__).parent / "local-cache" / "bls_top_picks"`

---

### Sub-Task 2 — Add Coverage Inventory Test

**Status:** `[ ] pending`

**Intent:**
Create `tests/test_bls_top_picks_coverage.py` as a pure local (no network) test file
that acts as the ongoing regression guard.  This test will initially fail (because 20
series are missing from the flagship table) and will only pass once all subtasks are
complete.  It is the acceptance criterion for the whole plan.

**Expected Outcomes:**
- `tests/test_bls_top_picks_coverage.py` exists and contains:
  - `test_top_picks_loader_parses_all_series()` — asserts exactly 29 `TopPickEntry` objects
    are loaded with non-empty `series_id`, `title`, and `category`.
  - `test_all_top_picks_in_flagship()` — parametrized over `TOP_PICKS`; each entry's
    `series_id` must be found by `get_flagship(series_id)`.  This is the key coverage
    guard: it will fail for all 20 missing series.
  - `test_all_top_picks_decodable()` — parametrized; `decode_id(series_id)` must not
    return an `"error"` key for any top-picks series.
  - `test_all_top_picks_flagship_metadata_correct()` — parametrized; for each top-picks
    series present in the flagship table, asserts that `series_id`, `survey`, `concept`,
    `measure_type`, and `unit` are non-empty.
  - `test_top_picks_categories_present()` — asserts that all four categories
    (Employment, Productivity, Price Indexes, Compensation) appear in `TOP_PICKS`.
  - `test_no_duplicate_top_picks_series_ids()` — asserts no duplicate series IDs in `TOP_PICKS`.
  - Per-program-family tests asserting each family represented in top picks has ≥1
    matching entry in the flagship table: `test_top_picks_ln_coverage()`,
    `test_top_picks_ce_coverage()`, `test_top_picks_pr_coverage()`,
    `test_top_picks_mp_coverage()`, `test_top_picks_cu_coverage()`,
    `test_top_picks_cw_coverage()`, `test_top_picks_wp_coverage()`,
    `test_top_picks_ei_coverage()`, `test_top_picks_ci_coverage()`.
- These tests run without any network access.
- After Sub-Task 1 (loader) is done, the loader tests pass.
- The parametrized coverage tests fail until Sub-Tasks 3–6 are complete.

**Todo List:**
1. Create `tests/test_bls_top_picks_coverage.py` with all the tests described above.
2. Run `uv run pytest tests/test_bls_top_picks_coverage.py -v` to confirm:
   - Loader and structural tests pass.
   - Coverage tests for missing series fail with clear messages.
3. Run `uv run ruff check tests/test_bls_top_picks_coverage.py` — fix any issues.

**Relevant Context:**
- Loader module from Sub-Task 1: `src/example_server/bls_top_picks.py`
- Flagship functions: [`bls_flagship_series.py`](src/example_server/bls_flagship_series.py:1724)
- Schema decoder: [`bls_series_schema.py`](src/example_server/bls_series_schema.py:297)
- Existing parametrized pattern: [`tests/test_bls_flagship_series.py:41`](tests/test_bls_flagship_series.py:41)

---

### Sub-Task 3 — Add Missing LN, CE Flagship Entries

**Status:** `[ ] pending`

**Intent:**
Add the 4 missing Employment-category series from `bls_top_picks` to the
`_LN_ENTRIES` and `_CE_ENTRIES` lists in `bls_flagship_series.py`.  These all
use already-supported schemas with no schema changes required.

**Missing series in this subtask:**

| Series ID | Description from top_picks | Survey |
|-----------|---------------------------|--------|
| LNS13000000 | Civilian Unemployment (Seasonally Adjusted) | LN |
| CES0500000002 | Total Private Avg Weekly Hours of All Employees (SA) | CE |
| CES0500000007 | Total Private Avg Weekly Hours of Prod./Nonsup. Employees (SA) | CE |
| CES0500000008 | Total Private Avg Hourly Earnings of Prod./Nonsup. Employees (SA) | CE |

**Expected Outcomes:**
- `get_flagship("LNS13000000")` returns a valid `FlagshipEntry` with:
  - `survey="LN"`, `concept="civilian_unemployment"`, `measure_type="level"`,
    `unit="thousands of persons"`, `notes` mentions seasonal adjustment.
- `get_flagship("CES0500000002")` returns a valid `FlagshipEntry` with:
  - `survey="CE"`, `concept="avg_weekly_hours_all_employees"`,
    `measure_type="level"`, `unit="hours"`.
- `get_flagship("CES0500000007")` returns a valid `FlagshipEntry` with:
  - `survey="CE"`, `concept="avg_weekly_hours_prod_nonsup"`,
    `measure_type="level"`, `unit="hours"`.
- `get_flagship("CES0500000008")` returns a valid `FlagshipEntry` with:
  - `survey="CE"`, `concept="avg_hourly_earnings_prod_nonsup"`,
    `measure_type="dollar_amount"`, `unit="dollars per hour"`.
- `decode_id()` on each ID succeeds (no error key).
- `test_all_top_picks_in_flagship()` passes for these 4 series IDs.

**Todo List:**
1. Add `LNS13000000` entry to `_LN_ENTRIES` in `bls_flagship_series.py`.
2. Add the three CE entries to `_CE_ENTRIES` (insert after `CES0500000003`).
3. Run `uv run pytest tests/test_bls_flagship_series.py tests/test_bls_top_picks_coverage.py -v`
   — confirm these 4 parametrized coverage cases now pass.
4. Run `uv run ruff check src/example_server/bls_flagship_series.py` — fix any issues.

**Relevant Context:**
- [`bls_flagship_series.py:590`](src/example_server/bls_flagship_series.py:590) — `_LN_ENTRIES`
- [`bls_flagship_series.py:141`](src/example_server/bls_flagship_series.py:141) — `_CE_ENTRIES`
- CE data type codes: `01`=employees, `02`=avg weekly hours (all), `03`=avg hourly earnings (all),
  `07`=avg weekly hours (prod/nonsup), `08`=avg hourly earnings (prod/nonsup)
- BLS CE format: `CE(2)+seasonal(1)+supersector(2)+industry(6)+datatype(2)` = 13 chars

---

### Sub-Task 4 — Add Missing PR and MP Flagship Entries

**Status:** `[ ] pending`

**Intent:**
Add the 5 missing Productivity-category series from `bls_top_picks` to
`_PR_ENTRIES` and `_MP_ENTRIES`.  The PR entries require attention to the
measure/duration code distinction (percent change from previous quarter = duration `2`).
The MP entries must map to the correct sector codes for Private Nonfarm Business (4910)
and Private Business (4900).

**Missing series in this subtask:**

| Series ID | Description from top_picks | Survey |
|-----------|---------------------------|--------|
| PRS85006092 | Nonfarm Business — Labor Productivity, % chg from prev quarter | PR |
| PRS85006112 | Nonfarm Business — Unit Labor Costs, % chg from prev quarter | PR |
| PRS85006152 | Nonfarm Business — Real Hourly Compensation, % chg from prev quarter | PR |
| MPU4910012 | TFP Private Nonfarm Business Sector (NAICS 113-81), annual index | MP |
| MPU4900012 | TFP Private Business Sector (NAICS 11-81), annual index | MP |

**Expected Outcomes:**
- `get_flagship("PRS85006092")` → `measure_type="rate"`, `unit="percent"`,
  `concept="nonfarm_business_labor_productivity_pct_change"`.
- `get_flagship("PRS85006112")` → `measure_type="rate"`, `unit="percent"`,
  `concept="nonfarm_business_unit_labor_costs_pct_change"`.
- `get_flagship("PRS85006152")` → `measure_type="rate"`, `unit="percent"`,
  `concept="nonfarm_business_real_hourly_compensation_pct_change"`.
- `get_flagship("MPU4910012")` → `measure_type="index"`, `unit="index 2017=100"`,
  `survey="MP"`, `concept="tfp_private_nonfarm_business"`.
- `get_flagship("MPU4900012")` → `measure_type="index"`, `unit="index 2017=100"`,
  `survey="MP"`, `concept="tfp_private_business"`.
- `decode_id()` succeeds for all five (no error key).
- Confirm PR measure code `09`=labor productivity, `11`=unit labor costs,
  `15`=real hourly compensation; duration `2` = percent change from previous quarter.
  If the PR catalog (`src/example_server/local-cache/pr.measure`, `pr.duration`)
  does not contain these codes, add the missing code→label mappings.
- Confirm MP sector catalog (`src/example_server/local-cache/mp.sector`) contains
  `4910` and `4900`. If not, add them.

**Todo List:**
1. Inspect `src/example_server/local-cache/pr.measure` and `pr.duration` to verify
   codes 09, 11, 15 and duration code 2 exist.
2. Inspect `src/example_server/local-cache/mp.sector` to verify sectors 4910 and 4900.
3. Add any missing catalog entries to the relevant local-cache files.
4. Add 3 PR entries to `_PR_ENTRIES` in `bls_flagship_series.py`.
5. Add 2 MP entries to `_MP_ENTRIES` in `bls_flagship_series.py`.
6. Run `uv run pytest tests/test_bls_flagship_series.py tests/test_bls_top_picks_coverage.py -v`.
7. Run `uv run ruff check src/example_server/bls_flagship_series.py`.

**Relevant Context:**
- [`bls_flagship_series.py:742`](src/example_server/bls_flagship_series.py:742) — `_PR_ENTRIES`
- [`bls_flagship_series.py:920`](src/example_server/bls_flagship_series.py:920) — `_MP_ENTRIES`
- PR format: `PR(2)+seasonal(1)+sector(4)+class(1)+measure(2)+duration(1)` = 11 chars
- MP format: `MP(2)+seasonal(1)+sector(4)+measure(2)+duration(1)` = 10 chars
- Local catalog files: `src/example_server/local-cache/pr.*`, `mp.*`

---

### Sub-Task 5 — Add Missing CU, CW Price Index Flagship Entries

**Status:** `[ ] pending`

**Intent:**
Add the 2 missing price index series `CUUR0000AA0` (CPI-U 1967=100) and
`CWUR0000SA0L1E` (CPI-W core, less food and energy) to the flagship table.
Also fix the existing metadata error where `CWUR0000SA0` is filed under `survey="CU"`
in the CU block — it must be moved to the CW block with `survey="CW"`.

**Key semantics:**
- `CUUR0000AA0`: the 1967=100 base-period variant of CPI-U All Items; not commonly
  discussed but is listed in BLS top picks. `measure_type="index"`, `unit="index 1967=100"`.
- `CWUR0000SA0L1E`: CPI-W All Items Less Food and Energy (core CPI-W), NSA.
- `CWUR0000SA0`: CPI-W All Items NSA — prefix is `CW`, not `CU`. The existing entry
  at line 574 incorrectly sets `survey="CU"`. This must be corrected to `survey="CW"`
  and the entry moved from `_CU_ENTRIES` to `_CW_ENTRIES`.

**Expected Outcomes:**
- `get_flagship("CUUR0000AA0")` → `survey="CU"`, `measure_type="index"`,
  `unit="index 1967=100"`, `concept="cpi_all_items_1967base"`.
- `get_flagship("CWUR0000SA0")` → `survey="CW"` (not `"CU"`).
- `get_flagship("CWUR0000SA0L1E")` → `survey="CW"`, `measure_type="index"`,
  `unit="index 1982-84=100"`, `concept="cpiw_core"`.
- `decode_id("CWUR0000SA0")` succeeds with prefix `"CW"` (currently decodes with `"CU"` schema).
- `test_all_top_picks_in_flagship()` passes for these series.
- Existing tests in `test_bls_flagship_series.py` for `CWUR0000SA0` continue to pass
  (update the survey assertion from `"CU"` to `"CW"` where it appears).
- CU and CW item catalogs (`cu.item`, `cw.item`) must contain code `AA0` for
  "All items, 1967=100". Inspect and add if missing.

**Todo List:**
1. Inspect `src/example_server/local-cache/cu.item` and `cw.item` for code `AA0`.
2. Add `AA0` to `cu.item` if missing (label: `"All items, 1967=100"`).
3. Remove `CWUR0000SA0` from `_CU_ENTRIES` in `bls_flagship_series.py`.
4. Add `CWUR0000SA0` and `CWUR0000SA0L1E` to `_CW_ENTRIES` with `survey="CW"`.
5. Add `CUUR0000AA0` to `_CU_ENTRIES`.
6. Update any test in `test_bls_flagship_series.py` that asserts `survey="CU"` for
   `CWUR0000SA0` — change to `survey="CW"`.
7. Run `uv run pytest tests/test_bls_flagship_series.py tests/test_bls_top_picks_coverage.py -v`.
8. Run `uv run ruff check src/example_server/bls_flagship_series.py`.

**Relevant Context:**
- [`bls_flagship_series.py:574`](src/example_server/bls_flagship_series.py:574) — `CWUR0000SA0` currently in `_CU_ENTRIES`
- [`bls_flagship_series.py:1063`](src/example_server/bls_flagship_series.py:1063) — `_CW_ENTRIES`
- CW format: `CW(2)+seasonal(1)+periodicity(1)+area(4)+item(variable)` (variable length)
- CW item catalog: `src/example_server/local-cache/cw.item`

---

### Sub-Task 6 — Add Missing WP Final Demand PPI and CI Compensation Entries

**Status:** `[ ] pending`

**Intent:**
Add the 5 missing WP (PPI Final Demand) series and 3 missing CI (Employment Cost Index)
series to the flagship table.  These are the most semantically complex additions because:

**WP (PPI Final Demand):** The existing `_WP_ENTRIES` cover PPI Commodity Data
(traditional goods-based PPI).  The top-picks entries (`WPSFD4`, `WPUFD4`,
`WPUFD49104`, `WPUFD49116`, `WPUFD49207`) are PPI Final Demand series, which BLS
introduced in 2014 and are now the headline PPI measures.  They share the `WP`-prefix
but use a "FD" commodity structure rather than the traditional numeric group codes.
The WP schema uses `total_length=None` (variable), so these IDs decode structurally
without schema changes.  However, the WP commodity catalog lookup will return
`label: null` for `FD4`, `FD49104`, etc.  The WP catalog
(`src/example_server/local-cache/wp.commodity` or similar) should be inspected;
if it lacks Final Demand codes, add them so decode_id returns human-readable labels.

**CI (ECI — Employment Cost Index):** The top-picks entries use `CIU…A` IDs
(periodicity `A` = 12-month percent change). The existing CI flagship entries
use `CIS…I` and `CIS…Q`. Note also the top-picks use `CIU` prefix (unadjusted) vs
the existing `CIS` (seasonally adjusted). The CI schema covers all CI-prefix IDs
(prefix `CI`, not `CIS` or `CIU` as a separate prefix — the schema's `seasonal`
segment at position 0 carries `S` or `U`). Confirm `periodicity_code = A` is
present in `ci.periodicity` catalog; add if missing.

**Missing series:**

| Series ID | Description from top_picks |
|-----------|---------------------------|
| WPSFD4 | PPI Final Demand (Seasonally Adjusted) |
| WPUFD4 | PPI Final Demand (Unadjusted) |
| WPUFD49104 | PPI Final Demand less foods and energy |
| WPUFD49116 | PPI Final Demand less foods, energy, and trade services |
| WPUFD49207 | PPI Finished Goods 1982=100 |
| CIU1010000000000A | ECI Civilian (Unadjusted) |
| CIU2010000000000A | ECI Private (Unadjusted) |
| CIU2020000000000A | ECI Private Wage and Salaries |

**Expected Outcomes:**
- `get_flagship("WPSFD4")` → `survey="WP"`, `measure_type="index"`,
  `unit="index 2009=100"`, `concept="ppi_final_demand_sa"`.
- `get_flagship("WPUFD4")` → `survey="WP"`, `measure_type="index"`,
  `unit="index 2009=100"`, `concept="ppi_final_demand_nsa"`.
- `get_flagship("WPUFD49104")` → `concept="ppi_final_demand_less_food_energy"`.
- `get_flagship("WPUFD49116")` → `concept="ppi_final_demand_less_food_energy_trade"`.
- `get_flagship("WPUFD49207")` → `concept="ppi_finished_goods"`.
- `get_flagship("CIU1010000000000A")` → `survey="CI"`, `measure_type="rate"`,
  `unit="percent"`, `concept="eci_total_compensation_civilian_12mo_pct_change"`.
- `get_flagship("CIU2010000000000A")` → `survey="CI"`, `concept="eci_total_compensation_private_12mo_pct_change"`.
- `get_flagship("CIU2020000000000A")` → `survey="CI"`, `concept="eci_wages_salaries_private_12mo_pct_change"`.
- `decode_id()` succeeds for all 8 (no error key; labels may be null for opaque segments
  that have no catalog entries, but no "error" key is acceptable).
- `test_all_top_picks_in_flagship()` passes for all 8 — completing the full coverage set.

**Todo List:**
1. Inspect `src/example_server/local-cache/wp.*` files to find PPI commodity catalog;
   check for Final Demand codes (`FD4`, `FD49104`, `FD49116`, `FD49207`). Add if missing.
2. Inspect `src/example_server/local-cache/ci.periodicity` for code `A`. Add if missing
   (label: `"12-month percent change"`).
3. Add 5 WP entries to `_WP_ENTRIES` in `bls_flagship_series.py`.
4. Add 3 CI entries to `_CI_ENTRIES` in `bls_flagship_series.py`.
5. Run `uv run pytest tests/test_bls_flagship_series.py tests/test_bls_top_picks_coverage.py -v`.
   At this point `test_all_top_picks_in_flagship` should pass for all 29 series.
6. Run `uv run ruff check src/example_server/bls_flagship_series.py`.

**Relevant Context:**
- [`bls_flagship_series.py:1230`](src/example_server/bls_flagship_series.py:1230) — `_WP_ENTRIES`
- [`bls_flagship_series.py:1554`](src/example_server/bls_flagship_series.py:1554) — `_CI_ENTRIES`
- WP schema: variable length, `total_length=None`, seasonal segment + opaque code
- CI schema: 17 chars, segments: seasonal(1)+owner(1)+estimate(2)+series_code(10)+periodicity(1)
- PPI Final Demand base period: `index 2009=100` (simplified from "November 2009=100" for consistency with other index unit strings)
- BLS reference: https://www.bls.gov/ppi/ (Final Demand-Intermediate Demand system)

---

### Sub-Task 7 — Full Validation Pass

**Status:** `[ ] pending`

**Intent:**
Run the complete test suite, linter, and type checker to confirm:
- All 29 top-picks series are covered (no parametrized coverage tests fail).
- No existing tests regressed.
- Code style is consistent with the project.
- The `bls_top_picks` loader, flagship additions, and schema/catalog fixes are production-ready.

**Expected Outcomes:**
- `uv run pytest tests/ -v` exits 0 with no failures or errors.
- `test_all_top_picks_in_flagship` shows 29 parametrized cases all passing.
- `test_all_top_picks_decodable` shows 29 parametrized cases all passing.
- `test_each_survey_has_at_least_six_entries` continues to pass (no survey count dropped).
- `uv run ruff check .` exits 0 with no warnings.
- No test has been weakened, deleted, or marked xfail.

**Todo List:**
1. Run `uv run pytest tests/ -v` and fix any remaining failures.
2. Run `uv run ruff check .` and fix any lint issues.
3. Confirm `test_bls_flagship_series.py::test_each_survey_has_at_least_six_entries` passes.
4. Confirm no tests are skipped for reasons other than `--run-live`.
5. Update `README.md` or relevant documentation to note:
   - `bls_top_picks` coverage is verified by `tests/test_bls_top_picks_coverage.py`.
   - To refresh the top-picks list, replace `src/example_server/local-cache/bls_top_picks`
     with the latest file from `https://www.bls.gov/bls/top_picks.htm` (tab-delimited
     or the plaintext format BLS publishes) and re-run the tests.
   - The loader module `bls_top_picks.py` explains the file format and provenance.

**Relevant Context:**
- All modified files in `src/example_server/`
- All test files in `tests/`
- `pyproject.toml` ruff config (line-length 88, rules E/F/I)

---

## Implementation Passes (Coin-Optimal Ordering)

Sub-Tasks 3–6 all touch non-overlapping lists in the same files and have no
interdependencies, so they are combined into a single agent pass to minimise
context re-loading cost.

```
Pass 1 → Sub-Task 1 (loader module — small, self-contained)
Pass 2 → Sub-Task 2 (inventory tests — depends on loader)
Pass 3 → Sub-Tasks 3 + 4 + 5 + 6 combined
           (all flagship additions + catalog fixes in one agent run)
Pass 4 → Sub-Task 7 (full validation)
```

**Why combined Pass 3 is cheaper:** Sub-Tasks 3–6 each add entries to separate
named lists (`_LN_ENTRIES`, `_CE_ENTRIES`, `_PR_ENTRIES`, `_MP_ENTRIES`,
`_CU_ENTRIES`, `_CW_ENTRIES`, `_WP_ENTRIES`, `_CI_ENTRIES`) with no conflicts.
One agent reading the plan once and applying all additions is significantly fewer
tokens than four agents each loading the full plan + file context independently.

Sub-Task 7 must come last.

---

## Files Changed (Expected)

| File | Change |
|------|--------|
| `src/example_server/bls_top_picks.py` | **New** — top-picks loader module |
| `src/example_server/bls_flagship_series.py` | Add 20 `FlagshipEntry` objects; fix `CWUR0000SA0` survey label |
| `src/example_server/local-cache/cu.item` | Add `AA0` if missing |
| `src/example_server/local-cache/cw.item` | Verify `SA0L1E` item code exists |
| `src/example_server/local-cache/pr.measure` | Add codes 09, 11, 15 if missing |
| `src/example_server/local-cache/pr.duration` | Verify duration 2 exists |
| `src/example_server/local-cache/mp.sector` | Add sectors 4910 and 4900 if missing |
| `src/example_server/local-cache/wp.*` | Add Final Demand commodity codes if missing |
| `src/example_server/local-cache/ci.periodicity` | Add code `A` if missing |
| `tests/test_bls_top_picks_coverage.py` | **New** — inventory and coverage tests |
| `tests/test_bls_flagship_series.py` | Update `CWUR0000SA0` survey assertion (`"CU"` → `"CW"`) |
| `README.md` | Note top-picks coverage and refresh procedure |

---

## Non-Goals

- Do not add a new MCP tool for top-picks specifically. The existing `suggest_series`
  and `get_series_metadata` tools are the correct interfaces once the flagship entries exist.
- Do not modify the `bls_top_picks` file itself (it is a reference input, not generated output).
- Do not add live/network tests for each individual top-picks series (the existing
  `test_bls_live.py` pattern already covers the retrieval path generically).
- Do not change the BLS API client, transport layer, or any tool other than the
  flagship series table and catalog reference files.
