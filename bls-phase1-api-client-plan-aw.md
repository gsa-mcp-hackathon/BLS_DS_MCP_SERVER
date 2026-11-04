# BLS Phase 1 — API Configuration, Client, and Tests Plan

## Top-Level Overview

**Goal:** Establish a working, tested connection to the official BLS Public Data API (v1 and v2)
by modifying only three existing files (`config.py`, `utils.py`, `models.py`), updating
`.env.example`, and adding one new test file (`tests/test_bls_utils.py`). No MCP tools,
resources, or prompts are created in this phase.

**Scope:**
- `src/example_server/config.py` — add `bls_api_key`, BLS base URL constants, and per-version limits
- `src/example_server/utils.py` — add `BLSAPIError`, `fetch_bls()`, `unwrap_bls_response()`, `validate_series_request()`; keep all existing symbols intact
- `src/example_server/models.py` — add `BLSSeriesRequest` input model with Pydantic validators
- `.env.example` — document `BLS_API_KEY` (no real key)
- `tests/test_bls_utils.py` — new file: all mocked unit tests for the above
- Live connectivity verification — run locally, results reported in chat; no verification script committed

**Non-goals:**
- No MCP tool, resource, or prompt files
- No changes to `app.py`, `routes.py`, `tools/`, `resources/`, `prompts/`
- No Docker, HTTP server, or cloud deployment work
- No pagination — the BLS time-series API returns all requested data points in a single
  response; `paginate()` is left in `utils.py` untouched (existing tests depend on it)
  but is never called by any BLS function
- No package rename (stays `example_server` for now)

---

## Existing File Constraints — Must Not Break

| File | Constraint |
|---|---|
| `utils.py` | `fetch_json`, `_validate_relative_path`, `paginate`, `UpstreamServiceError`, `API_BASE_URL` must remain present and unmodified — `test_http_security.py` references all of them by name |
| `config.py` | `mcp_transport`, `mcp_host`, `mcp_port` fields and `settings` singleton must remain — `test_server.py::test_default_transport_is_stdio` depends on them |
| `models.py` | `ResponseFormat` and `PaginationParams` must remain — existing tools import them |
| `tests/test_http_security.py` | All 6 tests reference `utils.fetch_json`, `utils.API_BASE_URL`, `utils._validate_relative_path`, `utils.UpstreamServiceError` — none of these symbols can be removed or renamed |

---

## BLS API Reference Summary

| Property | v1 | v2 |
|---|---|---|
| Base URL | `https://api.bls.gov/publicAPI/v1/` | `https://api.bls.gov/publicAPI/v2/` |
| Auth | None (anonymous) | `registrationKey` in POST JSON body |
| Series per request | Up to 25 | Up to 50 |
| Year range | Up to 10 years | Up to 20 years |
| Daily request limit | 25 / day | 500 / day |
| Endpoint path | `timeseries/data/` | `timeseries/data/` |
| HTTP method | POST (JSON body) | POST (JSON body) |
| Response envelope | `{"status": "REQUEST_SUCCEEDED", "Results": {"series": [...]}}` | Same shape; richer optional fields |
| Calculations | Not available | Optional (`calculations: true`) |
| Annual averages | Not available | Optional (`annualaverage: true`) |
| Pagination | None — all matching observations returned in one response | None — same |

Series ID format: alphanumeric, uppercase, variable length (typically 12–20 chars).
Example: `CUUR0000SA0` (CPI-U, all urban consumers, all items).

---

## Sub-Tasks

---

### Sub-Task 1 — Update `config.py` and `.env.example`

**Intent:** Add the BLS API key field and all BLS URL/limit constants to the single
authoritative configuration object. Utils and tools import from `config.py`; they
must never hardcode URLs, limits, or key values themselves.

**Expected Outcomes:**
- `Settings` has `bls_api_key: SecretStr = SecretStr("")` reading from `BLS_API_KEY` env var;
  `SecretStr` ensures the value is masked in all `repr`/`str` outputs and never accidentally logged
- Module-level URL constants defined after `settings = Settings()`:
  `BLS_V1_BASE_URL`, `BLS_V2_BASE_URL`
- Per-version limit constants: `BLS_V1_MAX_SERIES`, `BLS_V1_MAX_YEAR_RANGE`,
  `BLS_V2_MAX_SERIES`, `BLS_V2_MAX_YEAR_RANGE`, `BLS_V1_DAILY_LIMIT`, `BLS_V2_DAILY_LIMIT`
- A module-level helper `get_bls_api_version() -> str` that returns `"v2"` when
  `settings.bls_api_key.get_secret_value()` is non-empty, else `"v1"`
- `.env.example` documents `BLS_API_KEY` as optional with a note on v1/v2 selection
  and the BLS registration URL (`https://data.bls.gov/registrationEngine/`)
- All existing `Settings` fields and the `settings` singleton untouched

**Todo List:**
1. Open `src/example_server/config.py`
2. Add `from pydantic import SecretStr` to imports
3. In `Settings`, below the transport fields, add a `# ── BLS Public Data API ──` section
   and the `bls_api_key: SecretStr = SecretStr("")` field
4. After `settings = Settings()`, add module-level constants:
   - `BLS_V1_BASE_URL = "https://api.bls.gov/publicAPI/v1/"`
   - `BLS_V2_BASE_URL = "https://api.bls.gov/publicAPI/v2/"`
   - `BLS_V1_MAX_SERIES = 25`
   - `BLS_V1_MAX_YEAR_RANGE = 10`
   - `BLS_V2_MAX_SERIES = 50`
   - `BLS_V2_MAX_YEAR_RANGE = 20`
   - `BLS_V1_DAILY_LIMIT = 25`
   - `BLS_V2_DAILY_LIMIT = 500`
5. Add `get_bls_api_version() -> str` function after the constants
6. Open `.env.example` and append a `# ── BLS Public Data API ──` section with a commented
   `BLS_API_KEY=` line and explanatory comments (no real key)

**Relevant Context:**
- `src/example_server/config.py` lines 12–39: existing `Settings` class and `settings` singleton
- `.env.example` lines 14–18: existing API key comment pattern to follow
- `pydantic.SecretStr` is already available via the `pydantic>=2.0.0` dependency;
  value is retrieved via `.get_secret_value()`, never via direct attribute access

**Status:** [ ] pending

---

### Sub-Task 2 — Add BLS Client Functions to `utils.py`

**Intent:** Add BLS-specific async HTTP and response-handling functions alongside (not
replacing) all existing symbols. The BLS API uses HTTP POST for all data requests — the
existing `fetch_json` is GET-only and targets a different base URL. The new `fetch_bls`
uses the same security posture: `follow_redirects=False`, `trust_env=False`, explicit
timeout, 5 MB response cap, fully sanitized errors.

**Expected Outcomes:**
- `BLSAPIError(RuntimeError)` class added — distinct from `UpstreamServiceError` so callers
  can differentiate BLS envelope-level failures from transport failures
- `fetch_bls(payload: dict, timeout: float = DEFAULT_TIMEOUT) -> dict` async function:
  - Selects base URL via `get_bls_api_version()`
  - Copies the caller's payload dict before injecting `registrationKey` (never mutates
    the caller's object; never logs or returns the key value)
  - POSTs to `{base_url}timeseries/data/` with `Content-Type: application/json`
  - Uses `httpx.AsyncClient(follow_redirects=False, trust_env=False, timeout=timeout)`
  - Streams response, enforces 5 MB cap, parses JSON
  - HTTP 401/403 on v2 → `BLSAPIError("BLS API rejected the registration key. Verify BLS_API_KEY.")` (no key value in message)
  - Other HTTP errors → `UpstreamServiceError("BLS API returned HTTP {status_code}.")`
  - Connection/timeout → `UpstreamServiceError("BLS API request failed.")`
  - Malformed JSON → `UpstreamServiceError("BLS API returned invalid JSON.")`
  - Returns raw parsed JSON dict (envelope intact — unwrapping is the caller's responsibility)
- `unwrap_bls_response(payload: dict) -> list[dict]` function:
  - Checks `payload.get("status") == "REQUEST_SUCCEEDED"`; on failure extracts
    `payload.get("message", [])`, sanitizes (strips any substring matching the key pattern),
    raises `BLSAPIError` with those messages
  - Checks `"Results"` key exists and contains `"series"` key; raises `BLSAPIError` if missing
  - Returns `payload["Results"]["series"]` list verbatim — no type conversion on any field
- All existing symbols (`fetch_json`, `_validate_relative_path`, `paginate`,
  `UpstreamServiceError`, `API_BASE_URL`) remain present and unmodified

**Data integrity rules enforced by `unwrap_bls_response`:**
- `value` fields are returned as the original strings published by BLS (`"274.310"`, not `274.31`)
- `footnotes` lists are returned verbatim
- `period` and `periodName` are returned as-is (`"M01"`, `"January"`)
- Missing observations (value `"-"` or `"."`) are passed through unchanged — never replaced with `0`
- No metadata is fabricated when absent

**Todo List:**
1. Open `src/example_server/utils.py`
2. Add imports: `from example_server.config import (settings, get_bls_api_version, BLS_V1_BASE_URL, BLS_V2_BASE_URL)`
3. Add `class BLSAPIError(RuntimeError)` with docstring immediately after `UpstreamServiceError`
4. Add `async def fetch_bls(payload: dict, timeout: float = DEFAULT_TIMEOUT) -> dict` after `fetch_json`
5. Add `def unwrap_bls_response(payload: dict) -> list[dict]` after `fetch_bls`
6. Verify that `API_BASE_URL`, `fetch_json`, `_validate_relative_path`, `paginate`,
   and `UpstreamServiceError` are all still present and unmodified

**Relevant Context:**
- `src/example_server/utils.py` lines 65–93: `fetch_json` — exact httpx pattern to mirror
- BLS v2 POST body: `{"seriesid": [...], "startyear": "YYYY", "endyear": "YYYY", "registrationKey": "KEY"}`
- BLS v1 POST body: same but no `registrationKey`
- BLS endpoint path to POST: `timeseries/data/` (appended directly to the base URL string,
  not passed through `_validate_relative_path` — the path is hardcoded, not user-supplied)

**Status:** [ ] pending

---

### Sub-Task 3 — Add `BLSSeriesRequest` to `models.py`

**Intent:** Define a Pydantic model that validates all BLS request parameters at the boundary
before any network call is attempted. Invalid input raises `ValidationError` immediately with
a clear message; tools never write defensive checks themselves.

**Fields:**
| Field | Type | Default | Description |
|---|---|---|---|
| `series_ids` | `list[str]` | required | One or more BLS series IDs |
| `start_year` | `int \| None` | `None` | Start year (4-digit); None = BLS default |
| `end_year` | `int \| None` | `None` | End year (4-digit); None = BLS default |
| `calculations` | `bool` | `False` | v2 only: include net/percent change calculations |
| `annual_average` | `bool` | `False` | v2 only: include annual average row |

**Validators:**
1. `series_ids` — `len >= 1`; each ID matches `^[A-Z0-9]{1,20}$` (uppercase alphanumeric)
2. `start_year`, `end_year` — if provided, must be a 4-digit integer (1000–9999)
3. Cross-field: `start_year <= end_year` when both are provided
4. Cross-field: year range `(end_year - start_year + 1) <= 20` at model level (most permissive
   limit); the stricter v1 10-year check is applied at call time in `validate_series_request()`
   in `utils.py` when the version is known

**Expected Outcomes:**
- `BLSSeriesRequest` added to `models.py`
- All validators use Pydantic v2 style (`@field_validator`, `@model_validator(mode="after")`)
- `ValidationError` messages are human-readable (e.g., `"start_year must be <= end_year"`)
- `ResponseFormat` and `PaginationParams` untouched

**Todo List:**
1. Open `src/example_server/models.py`
2. Add imports: `import re`, `from pydantic import field_validator, model_validator`
3. Add `BLSSeriesRequest(BaseModel)` class below `PaginationParams`
4. Define all five fields with `Field(...)` descriptions
5. Add `@field_validator("series_ids")` class method for non-empty and format checks
6. Add `@field_validator("start_year", "end_year", mode="before")` for 4-digit year check
7. Add `@model_validator(mode="after")` for `start_year <= end_year` and `<= 20 year range`

**Relevant Context:**
- `src/example_server/models.py` lines 28–45: `PaginationParams` — style to follow
- Pydantic v2: `@field_validator` replaces v1 `@validator`; `@model_validator(mode="after")`
  replaces `@root_validator(pre=False)`

**Status:** [ ] pending

---

### Sub-Task 4 — Add `validate_series_request()` to `utils.py`

**Intent:** Enforce version-specific API limits that cannot be baked into the Pydantic model
because they depend on the configured API version at runtime. Produce actionable error messages
that tell the user exactly what is wrong and how to fix it (e.g., set `BLS_API_KEY`).

**Expected Outcomes:**
- `validate_series_request(request: BLSSeriesRequest) -> None` added to `utils.py`
- Raises `BLSAPIError` (not `ValueError`) with specific messages:
  - Series count over v1 limit: `"v1 allows up to 25 series per request. Configure BLS_API_KEY to use v2 (up to 50 series)."`
  - Series count over v2 limit: `"v2 allows a maximum of 50 series per request."`
  - Year range over v1 limit: `"v1 allows a maximum year range of 10 years. Configure BLS_API_KEY to use v2 (up to 20 years)."`
  - Year range over v2 limit: `"v2 allows a maximum year range of 20 years."`
  - `calculations=True` on v1: `"The calculations option requires v2. Configure BLS_API_KEY to enable v2."`
  - `annual_average=True` on v1: `"The annual_average option requires v2. Configure BLS_API_KEY to enable v2."`
- Returns `None` silently when all limits are satisfied

**Todo List:**
1. Add `from example_server.models import BLSSeriesRequest` to imports in `utils.py`
2. Add `from example_server.config import (BLS_V1_MAX_SERIES, BLS_V1_MAX_YEAR_RANGE, BLS_V2_MAX_SERIES, BLS_V2_MAX_YEAR_RANGE)` to imports
3. Add `def validate_series_request(request: BLSSeriesRequest) -> None` after `unwrap_bls_response`
4. Call `get_bls_api_version()` once at the top of the function to determine limits
5. Check series count, year range (when both years provided), and v2-only flags in order

**Relevant Context:**
- Constants defined in Sub-Task 1: `BLS_V1_MAX_SERIES=25`, `BLS_V1_MAX_YEAR_RANGE=10`,
  `BLS_V2_MAX_SERIES=50`, `BLS_V2_MAX_YEAR_RANGE=20`
- `get_bls_api_version()` defined in Sub-Task 1

**Status:** [ ] pending

---

### Sub-Task 5 — Write `tests/test_bls_utils.py`

**Intent:** Provide complete mocked test coverage for every new function. No real network calls.
Follows the exact patterns already established in `test_http_security.py`.

**Test cases:**

| Test name | What it covers |
|---|---|
| `test_version_selection_no_key` | `get_bls_api_version()` returns `"v1"` when key is empty |
| `test_version_selection_with_key` | `get_bls_api_version()` returns `"v2"` when key is set |
| `test_fetch_bls_v1_posts_to_v1_url` | v1 POST goes to `BLS_V1_BASE_URL`, no `registrationKey` in sent payload |
| `test_fetch_bls_v2_posts_to_v2_url` | v2 POST goes to `BLS_V2_BASE_URL` |
| `test_fetch_bls_v2_injects_key` | `registrationKey` present in payload actually sent to mock |
| `test_fetch_bls_key_not_in_error_message` | HTTP 401 error message does not contain the key value |
| `test_fetch_bls_http_failure` | `httpx.RequestError` → `UpstreamServiceError` |
| `test_fetch_bls_http_500` | HTTP 500 → `UpstreamServiceError` with status code, no body content |
| `test_fetch_bls_invalid_json` | Malformed response body → `UpstreamServiceError` |
| `test_fetch_bls_response_size_limit` | Response > 5 MB → `UpstreamServiceError` |
| `test_unwrap_success` | `REQUEST_SUCCEEDED` + valid `Results.series` → returns series list |
| `test_unwrap_failure_status` | `REQUEST_NOT_PROCESSED` → `BLSAPIError` containing message text |
| `test_unwrap_missing_results_key` | Missing `Results` key → `BLSAPIError` |
| `test_unwrap_missing_series_key` | `Results` present, no `series` key → `BLSAPIError` |
| `test_unwrap_preserves_value_string` | `"value": "274.310"` returned as exactly `"274.310"` (no float cast) |
| `test_unwrap_preserves_footnotes` | `footnotes` list returned verbatim |
| `test_unwrap_preserves_period_fields` | `period` and `periodName` returned as-is |
| `test_unwrap_preserves_missing_observation` | `"value": "-"` returned as `"-"`, not `0` |
| `test_unwrap_empty_series_list` | `"series": []` → returns `[]` without error |
| `test_validate_request_v1_series_limit_exceeded` | 26 series on v1 → `BLSAPIError` mentioning v2 |
| `test_validate_request_v2_series_limit_exceeded` | 51 series on v2 → `BLSAPIError` |
| `test_validate_request_v1_year_range_exceeded` | 11-year range on v1 → `BLSAPIError` mentioning v2 |
| `test_validate_request_v2_year_range_exceeded` | 21-year range on v2 → `BLSAPIError` |
| `test_validate_request_v1_calculations_rejected` | `calculations=True` on v1 → `BLSAPIError` mentioning v2 |
| `test_validate_request_v1_annual_average_rejected` | `annual_average=True` on v1 → `BLSAPIError` mentioning v2 |
| `test_validate_request_ok_v1` | Valid v1 request → no error |
| `test_validate_request_ok_v2` | Valid v2 request → no error |
| `test_bls_series_request_empty_ids` | `series_ids=[]` → `ValidationError` |
| `test_bls_series_request_bad_format` | `series_ids=["lowercase1"]` → `ValidationError` |
| `test_bls_series_request_bad_year` | `start_year=99` → `ValidationError` |
| `test_bls_series_request_year_order` | `start_year=2020, end_year=2010` → `ValidationError` |
| `test_bls_series_request_year_range_over_20` | 21-year range at model level → `ValidationError` |
| `test_bls_series_request_valid` | Valid request constructs without error |

**Implementation notes:**
- Use a `_FakeBLSPost` mock class following the `_FakeClient` pattern in `test_http_security.py`;
  capture the JSON body that was sent so key-injection tests can inspect it
- For version-selection tests, monkeypatch `example_server.config.settings.bls_api_key` or use
  `monkeypatch.setattr` on `utils.get_bls_api_version` to avoid re-instantiating `Settings`
- `asyncio_mode = "auto"` is already set in `pyproject.toml` — no `@pytest.mark.asyncio` decorator needed
- Import `ValidationError` from `pydantic` for model-level error assertions

**Relevant Context:**
- `tests/test_http_security.py`: `_FakeClient` mock pattern and `monkeypatch.setattr(utils.httpx, ...)` idiom
- `pyproject.toml` `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`

**Status:** [ ] pending

---

### Sub-Task 6 — Live Connectivity Verification (results reported in chat only)

**Intent:** Confirm the implemented client reaches the real BLS API correctly for both
versions. No code is committed; a temporary local script is run and discarded.

**v1 test (no `BLS_API_KEY` set):**
- Series: `CUUR0000SA0`, year: `2025`
- Expected: HTTP 200, `status = REQUEST_SUCCEEDED`, ≥ 1 observation returned

**v2 test (`BLS_API_KEY` loaded from `.env`):**
- Same series and year
- Expected: HTTP 200, `status = REQUEST_SUCCEEDED`, ≥ 1 observation, key injected
  (confirmed by observing `"v2"` in version log — key value never printed)

**Report format (posted in chat):**

| Field | v1 result | v2 result |
|---|---|---|
| API version used | | |
| HTTP status code | | |
| BLS envelope status | | |
| Series ID returned | | |
| Number of observations | | |
| BLS message field | | |
| Errors / warnings | | |

**Todo List:**
1. After Sub-Task 5 passes all tests, write a short temporary script in `scripts/verify_bls.py`
2. Run it without `BLS_API_KEY` set (v1 path)
3. Set `BLS_API_KEY` in `.env` (real registered key), re-run (v2 path)
4. Post the results table in chat
5. Delete `scripts/verify_bls.py` — do not commit it

**Status:** [ ] pending

---

## Implementation Order

1. **Sub-Task 1** — `config.py` + `.env.example`; no dependencies, safe to do first
2. **Sub-Task 2** — BLS client functions in `utils.py`; depends on config constants
3. **Sub-Task 3** — `BLSSeriesRequest` in `models.py`; independent, can run alongside Sub-Task 2
4. **Sub-Task 4** — `validate_series_request()` in `utils.py`; depends on Sub-Tasks 1–3
5. **Sub-Task 5** — `tests/test_bls_utils.py`; depends on all prior sub-tasks
6. **Sub-Task 6** — live verification; depends on all prior sub-tasks passing tests

## Files Modified / Created

| File | Action |
|---|---|
| `src/example_server/config.py` | Modified — `bls_api_key`, URL constants, limit constants, `get_bls_api_version()` |
| `src/example_server/utils.py` | Modified — `BLSAPIError`, `fetch_bls`, `unwrap_bls_response`, `validate_series_request` |
| `src/example_server/models.py` | Modified — `BLSSeriesRequest` with validators |
| `.env.example` | Modified — document `BLS_API_KEY` |
| `tests/test_bls_utils.py` | Created — all BLS unit tests (mocked, no live calls) |
| `scripts/verify_bls.py` | Temporary — live connectivity check; deleted after Sub-Task 6 |
