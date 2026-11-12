# BLS Series Enrichment — concept, measure_type, unit

## Top-Level Overview

**Goal:** Add three new metadata fields — `concept`, `measure_type`, and `unit` — to every
entry in the flagship series table, then surface those fields in the three tools that already
return flagship metadata.

**Files touched (4 total):**
- `src/example_server/bls_flagship_series.py`
- `src/example_server/tools/get_series_metadata.py`
- `src/example_server/tools/get_series_data.py`
- `src/example_server/tools/suggest_series.py`

**Ruff configuration (from `pyproject.toml`):**
- Rules: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort)
- Line length: 88 characters
- Target: Python 3.11
- `ruff format` enforces Black-compatible formatting

**Non-goals:**
- No changes to `bls_series_schema.py`, `catalog.py`, `models.py`, or test files.
- No new files, no new tools.

---

## Vocabulary Conventions

| Field | Format | Values |
|---|---|---|
| `concept` | `snake_case` short label | e.g. `"nonfarm_payrolls"`, `"unemployment_rate"`, `"cpi_all_items"` |
| `measure_type` | one of four fixed strings | `"level"`, `"rate"`, `"index"`, `"dollar_amount"` |
| `unit` | exact BLS publication unit | e.g. `"thousands of persons"`, `"percent"`, `"index 1982-84=100"`, `"dollars per hour"` |

---

## Authoritative Value Table

Derived from existing local-cache catalog files (`ce.datatype`, `la.measure`,
`jt.dataelement`, `jt.ratelevel`, `sm.data_type`) — no external lookups needed.

| series_id | concept | measure_type | unit |
|---|---|---|---|
| **SM — State and Metro Area Employment** ||||
| `SMU00000000000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `SMU36356200000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `SMU06310800000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `SMU17169800000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `SMU48264200000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `SMU04380600000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| **CE — Current Employment Statistics** ||||
| `CES0000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `CEU0000000001` | `nonfarm_payrolls` | `level` | `thousands of persons` |
| `CES0500000001` | `private_payrolls` | `level` | `thousands of persons` |
| `CES0600000001` | `goods_producing_payrolls` | `level` | `thousands of persons` |
| `CES0700000001` | `service_payrolls` | `level` | `thousands of persons` |
| `CES0500000003` | `average_hourly_earnings` | `dollar_amount` | `dollars per hour` |
| **LA — Local Area Unemployment Statistics** ||||
| `LAUST000000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUNT000000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUST060000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUST480000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUST360000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUST170000000000003` | `unemployment_rate` | `rate` | `percent` |
| `LAUMT171698000000003` | `unemployment_rate` | `rate` | `percent` |
| **JT — Job Openings and Labor Turnover** ||||
| `JTS000000000000001` | `job_openings` | `level` | `thousands of jobs` |
| `JTS000000000000HIL` | `hires` | `level` | `thousands of persons` |
| `JTS000000000000QUL` | `quits` | `level` | `thousands of persons` |
| `JTS000000000000LDL` | `layoffs_and_discharges` | `level` | `thousands of persons` |
| `JTS000000000000OSL` | `other_separations` | `level` | `thousands of persons` |
| `JTS000000000000JOR` | `job_openings_rate` | `rate` | `percent` |
| **CU — Consumer Price Index** ||||
| `CUUR0000SA0` | `cpi_all_items` | `index` | `index 1982-84=100` |
| `CUSR0000SA0` | `cpi_all_items` | `index` | `index 1982-84=100` |
| `CUUR0000SAF1` | `cpi_food` | `index` | `index 1982-84=100` |
| `CUUR0000SA0E` | `cpi_energy` | `index` | `index 1982-84=100` |
| `CUUR0000SA0L1E` | `cpi_core` | `index` | `index 1982-84=100` |
| `CWUR0000SA0` | `cpi_all_items` | `index` | `index 1982-84=100` |

---

## Sub-Tasks

---

### Sub-Task 1 — Extend `FlagshipEntry` with the three new fields

**Status:** `[ ] pending`

**Intent:**
Add `concept`, `measure_type`, and `unit` as optional string fields (defaulting to `""`) to
the frozen `FlagshipEntry` dataclass. The `""` default keeps all 30 existing constructor
calls valid until Sub-Task 2 populates them.

**Expected Outcomes:**
- `FlagshipEntry` has three new fields after `notes`: `concept: str = ""`,
  `measure_type: str = ""`, `unit: str = ""`.
- The module imports cleanly.
- `ruff check` and `ruff format --check` both pass.

**Lint / style rules to follow:**
- Each new field on its own line, aligned with the existing `notes: str = ""` pattern.
- Update the class docstring `Attributes:` block to document the three new attributes,
  keeping the same indentation and style as the existing attribute docs.
- No import additions needed — all three fields are `str`.

**Todo List:**
1. Open `src/example_server/bls_flagship_series.py`.
2. After `notes: str = ""` (line 37), append:
   ```python
   concept: str = ""
   measure_type: str = ""
   unit: str = ""
   ```
3. In the class docstring, after the `notes:` attribute description, add:
   ```
   concept:     Short snake_case label for the economic concept
                (e.g. "unemployment_rate", "nonfarm_payrolls").
   measure_type: One of "level", "rate", "index", "dollar_amount".
   unit:        BLS publication unit (e.g. "percent",
                "thousands of persons", "index 1982-84=100").
   ```
4. Run `ruff check src/example_server/bls_flagship_series.py` — expect zero issues.
5. Run `ruff format --check src/example_server/bls_flagship_series.py` — expect no diff.

**Relevant Context:**
- `FlagshipEntry` is `frozen=True`; fields with defaults must follow all fields without
  defaults. `concept`, `measure_type`, `unit` all have defaults so they go after `notes`.
- File: `src/example_server/bls_flagship_series.py`, lines 19–37.
- **Existing test impact:** `tests/test_bls_flagship_series.py` line 45 asserts
  `assert entry.notes, "notes must not be empty"`. This test does NOT assert on the new
  fields — adding them with `""` defaults does not break it.

---

### Sub-Task 2 — Populate every existing flagship entry with values

**Status:** `[ ] pending`

**Intent:**
Add `concept=`, `measure_type=`, and `unit=` keyword arguments to all 30 `FlagshipEntry`
constructor calls, using the authoritative value table.

**Expected Outcomes:**
- All 30 `FlagshipEntry` instances have non-empty values for all three fields.
- `ruff check` and `ruff format --check` pass.
- All existing tests still pass (no test asserts on the new fields being empty/absent).

**Lint / style rules to follow:**
- Each new kwarg on its own line, indented 8 spaces (matching the existing `notes=` line).
- String values use double quotes consistently with the rest of the file.
- Lines must not exceed 88 characters. All values are short strings — no wrapping needed.
- Place the three new kwargs after `notes=...` and before the closing `),` of each entry.
- Example of correct formatting for one entry:
  ```python
  FlagshipEntry(
      series_id="CES0000000001",
      survey="CE",
      survey_name="Current Employment Statistics",
      description="Total Nonfarm Payrolls — Seasonally Adjusted (Thousands)",
      keywords=[...],
      notes="Monthly. Seasonally adjusted. Subject to annual benchmark revision.",
      concept="nonfarm_payrolls",
      measure_type="level",
      unit="thousands of persons",
  ),
  ```

**Todo List:**
1. Work through each of the five `_XX_ENTRIES` lists in order (SM → CE → LA → JT → CU).
2. For each `FlagshipEntry(...)` constructor, add the three kwargs using the value table.
3. After all edits, run:
   ```
   ruff check src/example_server/bls_flagship_series.py
   ruff format --check src/example_server/bls_flagship_series.py
   ```
4. Fix any line-length or import-order issues reported before proceeding.

**Relevant Context:**
- All entries: `src/example_server/bls_flagship_series.py`, lines 45–480.
- The value table in this plan is the single source of truth.
- CE code derivation: datatype segment `01` → level/thousands; `03` → dollar_amount/dollars
  per hour (from `ce.datatype` cache file).
- LA measure `03` → rate/percent (from `la.measure` cache file).
- JT ratelevel `L` → level; `R` → rate (from `jt.ratelevel`). JT dataelement codes:
  `JO`=job_openings, `HI`=hires, `QU`=quits, `LD`=layoffs_and_discharges,
  `OS`=other_separations (from `jt.dataelement`).
- SM datatype `01` → All Employees, In Thousands → level/thousands (from `sm.data_type`).
- CU is always index 1982-84=100 (BLS CPI definition; no catalog ambiguity).

---

### Sub-Task 3 — Surface fields in `get_series_metadata`

**Status:** `[ ] pending`

**Intent:**
When `get_series_metadata` finds a flagship entry, include `concept`, `measure_type`, and
`unit` in the response dict alongside the existing `notes` field. Omit the keys entirely
when the values are empty (guards against any future entry that is not yet populated).

**Expected Outcomes:**
- `get_series_metadata("CUUR0000SA0")` returns a dict including `"concept"`,
  `"measure_type"`, and `"unit"`.
- Series without a flagship entry return no new keys.
- `ruff check` passes with zero issues.

**Lint / style rules to follow:**
- Use `if flagship.concept:` guard (not `if flagship.concept is not None:`) — consistent
  with the truthy-check pattern already used in this codebase for optional string enrichment.
- Each `if` block is a single assignment line; no blank lines between the three blocks.
- No new imports needed.

**Exact code to insert** (after `result["notes"] = flagship.notes`, inside the
`if flagship is not None:` block):
```python
if flagship.concept:
    result["concept"] = flagship.concept
if flagship.measure_type:
    result["measure_type"] = flagship.measure_type
if flagship.unit:
    result["unit"] = flagship.unit
```

**Todo List:**
1. Open `src/example_server/tools/get_series_metadata.py`.
2. Locate `result["notes"] = flagship.notes` (~line 102).
3. Insert the three `if` blocks immediately after that line.
4. Update the docstring return block to add:
   ```
   "concept": str      # only for flagship series
   "measure_type": str # only for flagship series
   "unit": str         # only for flagship series
   ```
5. Run `ruff check src/example_server/tools/get_series_metadata.py`.

**Relevant Context:**
- File: `src/example_server/tools/get_series_metadata.py`, lines 99–103.
- The `flagship` variable is guarded by `if flagship is not None:` at line 100.
- **Existing test impact:** No existing test asserts on the shape of `get_series_metadata`
  responses beyond the fields already documented — no test breakage expected.

---

### Sub-Task 4 — Surface fields in `get_series_data`

**Status:** `[ ] pending`

**Intent:**
When a returned series matches a flagship entry, include `concept`, `measure_type`, and
`unit` in the per-series dict alongside the existing `notes` field.

**Expected Outcomes:**
- Each series dict in the `"series"` list includes the three new fields when the series ID
  has a flagship entry.
- `"observations"` and all other existing fields are unchanged.
- `ruff check` passes.

**Lint / style rules to follow:**
- Same three `if flagship.X:` guard pattern as Sub-Task 3.
- No new imports — `get_flagship` is already imported at line 9.

**Exact code to insert** (after `entry["notes"] = flagship.notes` inside
`if flagship:` block, lines 147–148):
```python
if flagship.concept:
    entry["concept"] = flagship.concept
if flagship.measure_type:
    entry["measure_type"] = flagship.measure_type
if flagship.unit:
    entry["unit"] = flagship.unit
```

**Todo List:**
1. Open `src/example_server/tools/get_series_data.py`.
2. Locate `entry["notes"] = flagship.notes` (line 148 in the `if flagship:` block).
3. Insert the three `if` blocks immediately after that line.
4. Update the docstring `"notes": str` line to also mention the three new optional fields.
5. Run `ruff check src/example_server/tools/get_series_data.py`.

**Relevant Context:**
- File: `src/example_server/tools/get_series_data.py`, lines 146–149.
- The `if flagship:` guard is already on line 147; `entry` dict is built from line 141.

---

### Sub-Task 5 — Surface fields in `suggest_series`

**Status:** `[ ] pending`

**Intent:**
Include `concept`, `measure_type`, and `unit` in each suggestion dict returned by
`suggest_series`.

**Expected Outcomes:**
- Each dict in `result["suggestions"]` includes `"concept"`, `"measure_type"`, `"unit"`.
- Existing fields (`series_id`, `survey_name`, `description`, `rationale`) are unchanged.
- `ruff check` passes.

**Lint / style rules to follow:**
- Add the three new keys directly inside the `suggestions.append({...})` dict literal,
  after the `"rationale"` key.
- Use trailing comma on the last key (consistent with Black / ruff format style).
- No new imports — `entry` is already a `FlagshipEntry` in scope.
- Lines must stay under 88 characters; all values are short attribute references.

**Exact change to the dict literal** at lines 62–69 of `suggest_series.py`:
```python
suggestions.append(
    {
        "series_id": entry.series_id,
        "survey_name": entry.survey_name,
        "description": description,
        "rationale": entry.notes,
        "concept": entry.concept,
        "measure_type": entry.measure_type,
        "unit": entry.unit,
    }
)
```

**Todo List:**
1. Open `src/example_server/tools/suggest_series.py`.
2. Locate the `suggestions.append({...})` block (lines 62–69).
3. Add `"concept"`, `"measure_type"`, `"unit"` after the `"rationale"` key.
4. Update the docstring line `Each suggestion: {"series_id", "survey_name", ...}` to
   include the three new fields.
5. Run `ruff check src/example_server/tools/suggest_series.py`.

**Relevant Context:**
- File: `src/example_server/tools/suggest_series.py`, lines 62–69.
- **Critical test compatibility:** `tests/test_tools_search_suggest.py` line 175
  (`test_suggest_series_result_shape`) asserts that each suggestion contains `series_id`,
  `survey_name`, `description`, and `rationale`. Adding new keys does NOT break this test
  — it only checks `in`, not exact equality. The test will still pass.

---

### Sub-Task 6 — Validation

**Status:** `[ ] pending`

**Intent:**
Confirm all changes are coherent: every entry is fully populated, lint passes, and all
existing tests pass without modification.

**Expected Outcomes:**
- Python assertion that every flagship entry is fully populated exits 0.
- `ruff check src/` reports zero issues.
- `ruff format --check src/` reports no files would be reformatted.
- `pytest tests/` passes with zero failures and zero errors.

**Todo List:**
1. Run the population assertion:
   ```
   python -c "
   from example_server.bls_flagship_series import FLAGSHIP_SERIES
   empty = [
       e.series_id for e in FLAGSHIP_SERIES
       if not (e.concept and e.measure_type and e.unit)
   ]
   assert not empty, f'Missing values for: {empty}'
   print(f'All {len(FLAGSHIP_SERIES)} entries populated OK')
   "
   ```
2. Run `ruff check src/`.
3. Run `ruff format --check src/`.
4. Run `pytest tests/ -v` and confirm all tests pass.
5. If any test fails, read the failure message carefully — the most likely cause is a
   line-length violation (fix by checking the 88-char limit) or an `isort` import-order
   issue (fix by running `ruff check --fix`).

**Known test files that touch changed code:**
- `tests/test_bls_flagship_series.py` — tests `FlagshipEntry` fields and `FLAGSHIP_SERIES`
  list; adding new fields with defaults does not break any existing assertion.
- `tests/test_tools_search_suggest.py` — `test_suggest_series_result_shape` checks four
  keys via `in`; adding more keys does not break it.
- `tests/test_tools_get_series.py` — if it asserts on `get_series_data` response shape,
  adding optional keys to flagship-matched series will not break it (same `in` pattern).

---

### Sub-Task 7 — Write tests for the new fields

**Status:** `[ ] pending`

**Intent:**
Add test coverage for all three new fields across the four changed code units:
`FlagshipEntry`, `get_series_metadata`, `get_series_data`, and `suggest_series`.
Tests are appended to the two most relevant existing test files — no new test files created.

**Expected Outcomes:**
- New tests are added to `tests/test_bls_flagship_series.py` (FlagshipEntry coverage)
  and `tests/test_tools_get_series.py` (tool coverage for metadata and data) and
  `tests/test_tools_search_suggest.py` (suggest_series coverage).
- All new and existing tests pass under `pytest tests/ -v`.
- `ruff check tests/` and `ruff format --check tests/` pass.

**Style rules to follow (match existing test conventions):**
- `from __future__ import annotations` at top of every test file.
- Module imports inside test functions (`import example_server.tools.X as mod`) — match
  the existing deferred-import pattern already used throughout the test files.
- Async tests are plain `async def` — `asyncio_mode = "auto"` in `pyproject.toml` handles
  the event loop.
- Use the existing `_capture(module)` helper (already defined in both
  `test_tools_get_series.py` and `test_tools_search_suggest.py`) — do NOT redefine it.
- Use the existing `_FakeBLSClient` and `_call_get_series_data` helpers from
  `test_tools_get_series.py` for `get_series_data` tests — do NOT redefine them.
- `_make_bls_envelope(series_id=...)` is already defined in `test_tools_get_series.py`;
  pass `series_id="CUUR0000SA0"` (a flagship series) to exercise the enrichment path.
- No `monkeypatch` fixture needed for `get_series_metadata` or `suggest_series`
  (they make no network calls).

---

**Tests to add to `tests/test_bls_flagship_series.py`:**

Append after the existing test functions (after line 143).

```python
# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit
# ---------------------------------------------------------------------------


def test_flagship_entry_has_concept_field() -> None:
    from example_server.bls_flagship_series import FlagshipEntry

    e = FlagshipEntry(
        series_id="TEST000001",
        survey="CE",
        survey_name="Test Survey",
        description="Test",
        keywords=["test"],
        notes="Test notes.",
        concept="test_concept",
        measure_type="level",
        unit="thousands of persons",
    )
    assert e.concept == "test_concept"
    assert e.measure_type == "level"
    assert e.unit == "thousands of persons"


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_concept(entry: FlagshipEntry) -> None:
    assert entry.concept, f"{entry.series_id}: concept must not be empty"


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_measure_type(entry: FlagshipEntry) -> None:
    valid = {"level", "rate", "index", "dollar_amount"}
    assert entry.measure_type in valid, (
        f"{entry.series_id}: measure_type '{entry.measure_type}' not in {valid}"
    )


@pytest.mark.parametrize("entry", FLAGSHIP_SERIES)
def test_all_entries_have_unit(entry: FlagshipEntry) -> None:
    assert entry.unit, f"{entry.series_id}: unit must not be empty"


def test_cpi_entries_are_index_type() -> None:
    from example_server.bls_flagship_series import get_flagship

    for sid in ("CUUR0000SA0", "CUSR0000SA0", "CUUR0000SAF1"):
        e = get_flagship(sid)
        assert e is not None
        assert e.measure_type == "index"
        assert e.unit == "index 1982-84=100"


def test_la_entries_are_rate_percent() -> None:
    from example_server.bls_flagship_series import get_flagship

    for sid in ("LAUST000000000000003", "LAUNT000000000000003"):
        e = get_flagship(sid)
        assert e is not None
        assert e.measure_type == "rate"
        assert e.unit == "percent"


def test_ce_nonfarm_is_level_thousands() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("CES0000000001")
    assert e is not None
    assert e.concept == "nonfarm_payrolls"
    assert e.measure_type == "level"
    assert e.unit == "thousands of persons"


def test_ce_earnings_is_dollar_amount() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("CES0500000003")
    assert e is not None
    assert e.concept == "average_hourly_earnings"
    assert e.measure_type == "dollar_amount"
    assert e.unit == "dollars per hour"


def test_jt_openings_level() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("JTS000000000000001")
    assert e is not None
    assert e.concept == "job_openings"
    assert e.measure_type == "level"


def test_jt_openings_rate() -> None:
    from example_server.bls_flagship_series import get_flagship

    e = get_flagship("JTS000000000000JOR")
    assert e is not None
    assert e.concept == "job_openings_rate"
    assert e.measure_type == "rate"
    assert e.unit == "percent"
```

---

**Tests to add to `tests/test_tools_get_series.py`:**

Append after the last existing test function (after line 310).

```python
# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit in get_series_metadata
# ---------------------------------------------------------------------------


def test_get_series_metadata_flagship_has_concept() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "concept" in result
    assert result["concept"] == "cpi_all_items"


def test_get_series_metadata_flagship_has_measure_type() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "measure_type" in result
    assert result["measure_type"] == "index"


def test_get_series_metadata_flagship_has_unit() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CUUR0000SA0")
    assert "unit" in result
    assert result["unit"] == "index 1982-84=100"


def test_get_series_metadata_non_flagship_no_concept() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    # SMU01000000000000001 is a valid SM series not in the flagship table
    result = fn(series_id="SMU01000000000000001")
    assert "concept" not in result
    assert "measure_type" not in result
    assert "unit" not in result


def test_get_series_metadata_la_rate_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="LAUST000000000000003")
    assert result.get("concept") == "unemployment_rate"
    assert result.get("measure_type") == "rate"
    assert result.get("unit") == "percent"


def test_get_series_metadata_ce_earnings_series() -> None:
    import example_server.tools.get_series_metadata as mod

    fn = _capture(mod)
    result = fn(series_id="CES0500000003")
    assert result.get("measure_type") == "dollar_amount"
    assert result.get("unit") == "dollars per hour"


# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit in get_series_data
# ---------------------------------------------------------------------------


async def test_get_series_data_flagship_has_concept(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "concept" in series_entry
    assert series_entry["concept"] == "cpi_all_items"


async def test_get_series_data_flagship_has_measure_type(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "measure_type" in series_entry
    assert series_entry["measure_type"] == "index"


async def test_get_series_data_flagship_has_unit(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    client = _FakeBLSClient()
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["CUUR0000SA0"]
    )
    series_entry = result["series"][0]
    assert "unit" in series_entry
    assert series_entry["unit"] == "index 1982-84=100"


async def test_get_series_data_non_flagship_no_concept(monkeypatch) -> None:
    import example_server.tools.get_series_data as mod

    fn = _capture(mod)
    # Use a non-flagship series ID — SMU01000000000000001 (Alabama, valid but not curated)
    client = _FakeBLSClient(body=_make_bls_envelope(series_id="SMU01000000000000001"))
    result = await _call_get_series_data(
        fn, monkeypatch, client, series_ids=["SMU01000000000000001"]
    )
    series_entry = result["series"][0]
    assert "concept" not in series_entry
    assert "measure_type" not in series_entry
    assert "unit" not in series_entry
```

---

**Tests to add to `tests/test_tools_search_suggest.py`:**

Append after the last existing test function (after line 186).

```python
# ---------------------------------------------------------------------------
# New fields: concept, measure_type, unit in suggest_series
# ---------------------------------------------------------------------------


def test_suggest_series_result_has_concept() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="consumer price inflation")
    assert result["count"] >= 1
    for s in result["suggestions"]:
        assert "concept" in s, f"Missing 'concept' in suggestion: {s['series_id']}"


def test_suggest_series_result_has_measure_type() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="nonfarm payrolls")
    assert result["count"] >= 1
    for s in result["suggestions"]:
        assert "measure_type" in s
        assert s["measure_type"] in {"level", "rate", "index", "dollar_amount"}


def test_suggest_series_result_has_unit() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="unemployment rate national")
    assert result["count"] >= 1
    for s in result["suggestions"]:
        assert "unit" in s
        assert s["unit"]  # non-empty


def test_suggest_series_cpi_concept_is_index() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="cpi all items")
    cpi_suggestions = [s for s in result["suggestions"] if s["series_id"] == "CUUR0000SA0"]
    assert cpi_suggestions, "CUUR0000SA0 should appear for 'cpi all items' topic"
    s = cpi_suggestions[0]
    assert s["concept"] == "cpi_all_items"
    assert s["measure_type"] == "index"
    assert s["unit"] == "index 1982-84=100"


def test_suggest_series_unemployment_concept_is_rate() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="unemployment rate national")
    rate_suggestions = [s for s in result["suggestions"] if s.get("measure_type") == "rate"]
    assert rate_suggestions, "At least one rate suggestion expected for unemployment topic"
    for s in rate_suggestions:
        assert s["unit"] == "percent"
```

---

**Todo List:**
1. Open `tests/test_bls_flagship_series.py` and append the `FlagshipEntry` tests block
   (ensuring `pytest` and `FlagshipEntry` are already imported at the top of the file —
   they are, per the existing imports at lines 5–12).
2. Open `tests/test_tools_get_series.py` and append the metadata and data test blocks
   (all helpers `_capture`, `_FakeBLSClient`, `_call_get_series_data`, `_make_bls_envelope`
   are already defined in that file — do NOT redefine them).
3. Open `tests/test_tools_search_suggest.py` and append the suggest_series test block
   (`_capture` is already defined at line 9 of that file — do NOT redefine it).
4. Run `ruff check tests/` and fix any issues (most likely: line too long on the
   `_make_bls_envelope` call or the `assert` message string — wrap at 88 chars).
5. Run `ruff format --check tests/`.
6. Run `pytest tests/ -v` and confirm all new tests pass.

**Relevant Context:**
- `tests/test_bls_flagship_series.py` — existing imports: `pytest`, `FLAGSHIP_SERIES`,
  `FlagshipEntry`, `get_flagship`, `search_flagship` (lines 5–12). The new tests reuse all
  of these; no new imports needed at the file level.
- `tests/test_tools_get_series.py` — existing helpers at lines 14–26 (`_capture`),
  95–121 (`_make_bls_envelope`), 124–179 (`_FakeBLSClient` + `_FakeStream`),
  187–189 (`_call_get_series_data`). The new async tests follow the exact same pattern as
  `test_get_series_data_flagship_series_has_notes` (lines 285–294).
- `tests/test_tools_search_suggest.py` — `_capture` defined at lines 9–22; reused by all
  suggest_series tests. The `cpi_suggestions` line-length check: `series_id == "CUUR0000SA0"`
  fits within 88 chars; the `rate_suggestions` line with `.get("measure_type") == "rate"`
  may need to be split if ruff reports it.
