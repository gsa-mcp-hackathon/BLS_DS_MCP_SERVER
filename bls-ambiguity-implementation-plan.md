# BLS Ambiguity Implementation Plan

## A. EXECUTIVE SUMMARY

### Current Protection Against Incorrect Series Selection

The application **does not currently protect** against silent incorrect series selection. The
primary entry point for natural-language queries is [`answer_bls_question`](src/example_server/tools/answer_bls_question.py)
in `answer_bls_question.py`. It calls `_discover_series`, which calls
[`search_flagship`](src/example_server/bls_flagship_series.py:2150) with
`limit=3` and immediately takes `hits[0]` — the first result — without any
ambiguity check, without disclosing what series was chosen, and without asking the user to
confirm. No clarification gate exists anywhere in the codebase.

### Where Ambiguity Is Currently Handled

- **Partial:** [`FlagshipEntry`](src/example_server/bls_flagship_series.py:20) carries
  `concept`, `measure_type`, and `unit` fields per series. These exist in the data but are
  never compared against user intent.
- **Partial:** [`search_series`](src/example_server/tools/search_series.py:154) uses keyword
  hints to route queries to surveys and infers seasonal adjustment from query words, defaulting
  silently to `U` (not seasonally adjusted) when no hint is detected.
- **Not handled:** No intent schema, no candidate eligibility filter, no clarification
  mechanism, no comparison-period enforcement, no household-vs-establishment disambiguation,
  no level-vs-rate disambiguation, no stock-vs-flow disambiguation.

### Where Ambiguity Is Not Handled

Every layer from intent interpretation through response generation is absent or incomplete:

- No structured intent representation exists.
- Discovery immediately selects `hits[0]` from a word-match score.
- Candidates are not checked for measure-type or unit compatibility with the query.
- No clarification is ever generated.
- Seasonal adjustment defaults silently to `U` in `search_series`.
- Ranking queries (e.g. "what industry added the most jobs?") have no comparison-period
  enforcement.
- Geographic ambiguity (e.g. "Washington") is never detected or resolved.
- Stock vs. flow (e.g. "how many people lost jobs?") is unresolved.
- CPI-index vs. inflation-rate is unresolved.
- Conversational follow-ups have no context-carry mechanism.

### Three to Seven Highest-Risk Gaps

1. **`hits[0]` auto-selection in `_discover_series`** — Any ambiguous query silently
   resolves to the top word-match result. A query for "employment" could return a nonfarm
   payroll level, an employment-population ratio, or a household employment level depending
   on keyword ordering.

2. **Level vs. rate not distinguished** — "Show employment" and "show the
   employment-population ratio" use the same keyword `employment` and can return the same
   top hit from `search_flagship`. The `measure_type` field exists but is never used to filter.

3. **CPI index vs. inflation rate conflated** — `search_series` maps "cpi" and "inflation"
   both to item code `SA0`, returning an index-level series. A user asking "what is the
   inflation rate" receives an index level, not a percent-change figure.

4. **Seasonal adjustment defaults to `U` silently** — `search_series` line 194:
   `seasonal = _match_first(query, _SEASONAL_HINTS) or "U"`. Not seasonally adjusted is
   applied by default even for metrics such as payroll employment change where the seasonally
   adjusted figure is the standard published headline.

5. **No clarification gate before BLS API call** — `answer_bls_question` calls
   `_fetch_observations` after discovery without any ambiguity check. The live API is called
   before the user has had an opportunity to confirm the interpretation.

6. **Ranking and comparison queries have no period enforcement** — Queries like "what
   industry added the most jobs?" have no mechanism to determine the comparison window
   (month-over-month vs. year-over-year vs. YTD).

7. **No conversation context tracking** — Follow-up queries ("What about California?",
   "Show the rate instead") have no context from the prior turn. Each call to
   `answer_bls_question` is stateless.

### Primary Problem Layers

The problems span all layers: **prompts** (no disambiguation guidance), **code** (no
eligibility rules, no clarification gate, `hits[0]` selection), **tool metadata** (tool
descriptions do not state when clarification is required), **data metadata** (`concept` and
`measure_type` exist but are not used in routing), and **tests** (no tests for ambiguous
queries or clarification behavior).

### What Must Be Fixed Before Implementation Is Reliable

1. Remove the `hits[0]` auto-selection from `_discover_series` and replace with an
   eligibility-and-conflict check.
2. Add a `measure_type` and `concept` comparison between user intent and candidate metadata.
3. Add a clarification gate that blocks the BLS API call when material ambiguity remains.
4. Enforce seasonal-adjustment policy: document the default, make it safe, disclose it.
5. Add conversation-context tracking for follow-up queries.
6. Add tests that assert no BLS API call occurs for materially ambiguous queries.

---

## B. REPOSITORY INVENTORY

### Source Files

| File | Role in Ambiguity Handling |
|------|---------------------------|
| [`src/example_server/app.py`](src/example_server/app.py) | Entry point; wires all tools, prompts, resources. No ambiguity logic. |
| [`src/example_server/config.py`](src/example_server/config.py) | Transport and API-key settings only. No ambiguity defaults or thresholds. |
| [`src/example_server/models.py`](src/example_server/models.py) | `BLSSeriesRequest` with Pydantic validation; `ResponseFormat`; `PaginationParams`. No intent schema, no candidate schema. |
| [`src/example_server/bls_flagship_series.py`](src/example_server/bls_flagship_series.py) | `FlagshipEntry` dataclass with `concept`, `measure_type`, `unit` fields. `search_flagship` does word-count scoring; `get_flagship` does exact-ID lookup. This is the only location that carries measure semantics. |
| [`src/example_server/bls_series_schema.py`](src/example_server/bls_series_schema.py) | Structural schemas for 12 surveys. `decode_id`, `build_id`. No semantic content (measure types, units). |
| [`src/example_server/catalog.py`](src/example_server/catalog.py) | Code→name lookups for survey dimensions. Used for geographic and industry code resolution. No semantic filtering. |
| [`src/example_server/bls_top_picks.py`](src/example_server/bls_top_picks.py) | Loads BLS top-picks series list from local cache. Used in coverage tests. Not wired into discovery. |
| [`src/example_server/utils.py`](src/example_server/utils.py) | `fetch_bls`, `unwrap_bls_response`, `validate_series_request`, `paginate`. API-layer validation only; no semantic validation. |
| [`src/example_server/routes.py`](src/example_server/routes.py) | HTTP infrastructure (health check). No ambiguity logic. |

### Tool Files

| File | Role |
|------|------|
| [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py) | **Primary orchestrator.** `_discover_series` → `hits[0]` selection. **Critical gap.** |
| [`src/example_server/tools/suggest_series.py`](src/example_server/tools/suggest_series.py) | Calls `search_flagship`, returns ranked list with `concept`/`measure_type`/`unit`. Returns all candidates — does not select one. |
| [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py) | Multi-survey catalog search. Defaults seasonal to `U`. Builds series IDs from dimension codes. No eligibility filtering. |
| [`src/example_server/tools/get_series_data.py`](src/example_server/tools/get_series_data.py) | Live BLS API call. No semantic guard. Any series ID triggers retrieval. |
| [`src/example_server/tools/get_series_metadata.py`](src/example_server/tools/get_series_metadata.py) | Local decode + validate + flagship notes. Returns `concept`/`measure_type`/`unit` for flagship series. |
| [`src/example_server/tools/validate_series_id.py`](src/example_server/tools/validate_series_id.py) | Structural validation only (prefix, length, catalog codes). No semantic validation. |
| [`src/example_server/tools/build_series_id.py`](src/example_server/tools/build_series_id.py) | Assembles series IDs from named parts. No intent-to-dimension mapping. |
| [`src/example_server/tools/decode_series_id.py`](src/example_server/tools/decode_series_id.py) | Decodes series ID into human-readable segments. No semantic filtering. |
| [`src/example_server/tools/lookup_area_code.py`](src/example_server/tools/lookup_area_code.py) | Geographic code lookup. Returns candidates; does not select one. |
| [`src/example_server/tools/lookup_industry_code.py`](src/example_server/tools/lookup_industry_code.py) | Industry code lookup. Returns candidates; does not select one. |

### Prompts

| File | Role |
|------|------|
| [`src/example_server/prompts/bls_assistant.py`](src/example_server/prompts/bls_assistant.py) | System prompt. Describes tool workflow. **Does not contain any disambiguation guidance, clarification instructions, or measure-type guidance.** |
| [`src/example_server/prompts/example.py`](src/example_server/prompts/example.py) | Placeholder exploration prompt. Not relevant to BLS disambiguation. |

### Resources

| File | Role |
|------|------|
| [`src/example_server/resources/bls_surveys.py`](src/example_server/resources/bls_surveys.py) | Survey reference documentation. Documents SA notes, unit notes per survey. Never read at query time — it is a resource, not a runtime component. |

### Configuration

| Setting | Current Value | Ambiguity Role |
|---------|--------------|----------------|
| `bls_api_key` | Optional; selects v1 or v2 | No ambiguity role |
| `mcp_transport` | `stdio` default | No ambiguity role |
| Auto-select threshold | **Not configured** | Absent |
| Clarify threshold | **Not configured** | Absent |
| Seasonal default | Hardcoded `"U"` in `search_series.py:194` | Unsafe default, undocumented |
| Year range default | BLS API default (last 3 years) | Safe for current-value queries |

### Tests

| File | Coverage |
|------|----------|
| [`tests/test_tools_answer_bls_question.py`](tests/test_tools_answer_bls_question.py) | Happy-path orchestration, error paths, API mocking. **No ambiguity tests.** |
| [`tests/test_tools_search_suggest.py`](tests/test_tools_search_suggest.py) | Search/suggest shape and coverage tests. **No ambiguity tests.** |
| [`tests/test_bls_flagship_series.py`](tests/test_bls_flagship_series.py) | Integrity tests for concept/measure_type/unit fields. **No query-resolution tests.** |
| [`tests/test_bls_top_picks_coverage.py`](tests/test_bls_top_picks_coverage.py) | Top-picks loader and flagship coverage. |
| [`tests/test_tools_build_decode_validate.py`](tests/test_tools_build_decode_validate.py) | Structural series ID tools. |
| [`tests/test_bls_utils.py`](tests/test_bls_utils.py) | HTTP utility tests. |
| [`tests/test_catalog.py`](tests/test_catalog.py) | Catalog lookup tests. |
| [`tests/test_server.py`](tests/test_server.py) | Server registration tests. |
| [`tests/test_bls_live.py`](tests/test_bls_live.py) | Live API integration (skipped by default). |

---

## C. CURRENT EXECUTION FLOW

```
User query (natural language)
  │
  ▼
answer_bls_question (tools/answer_bls_question.py:167)
  │
  ├─ [if series_id supplied] → skip discovery
  │
  ├─ [else] _discover_series(question)   (line 235)
  │     │
  │     └─ search_flagship(question, limit=3)  (bls_flagship_series.py:2150)
  │           │  word-count scoring over keywords+description+survey_name
  │           └─ returns sorted list of FlagshipEntry
  │
  │     hits[0]  ← FIRST RESULT IS TAKEN WITH NO ELIGIBILITY CHECK  (line 68)
  │
  ├─ _validate_locally(resolved_id)   (line 254)
  │     └─ SCHEMAS prefix check only — not semantic
  │
  └─ _fetch_observations(resolved_id, start_year, end_year)   (line 269)
        │  NO CLARIFICATION GATE HERE
        └─ BLS API live call via fetch_bls()
```

**Defaults entering the flow:**

- `seasonal` in `search_series`: defaults to `"U"` (not seasonally adjusted) at line 194 when
  no seasonal hint is in the query.
- `start_year`/`end_year` in `answer_bls_question`: when `None`, BLS API returns its default
  range (~last 3 years). This is disclosed in the tool docstring.
- `limit=3` in `_discover_series`: only 3 candidates are considered; the first is taken.

**Where candidate selection occurs:**

`answer_bls_question.py:68` — `best = hits[0]`

**Where API retrieval occurs:**

`answer_bls_question.py:269` — `_fetch_observations(...)`

**Where clarification could interrupt the flow:**

Nowhere currently. The correct location is between `_discover_series` and `_fetch_observations`.

**Paths that cannot be confirmed statically:**

The behavior when the LLM client uses `suggest_series` or `search_series` directly (not through
`answer_bls_question`) depends entirely on what the LLM does with the results. This path cannot
be traced statically and requires runtime evaluation.

---

## D. AMBIGUITY COVERAGE MATRIX

| Category | Example Query | Current Location | Current Behavior | Risk | Desired Behavior | Layer | Test Coverage | Gap |
|----------|--------------|-----------------|-----------------|------|-----------------|-------|--------------|-----|
| 4.1 Level vs. rate | "Show employment" | `answer_bls_question._discover_series` | Returns `hits[0]` from word match; could be level or ratio | Critical | Detect `employment` ambiguity; clarify level vs. ratio vs. household vs. payroll | Code+Prompt | None | OPEN |
| 4.1 Level vs. rate | "Show the unemployment rate" | `search_flagship` | Returns LA or LN rate series correctly if keyword hits | Medium | Auto-resolve if `measure_type=rate` confirmed in top hit | Code | Partial (shape tests) | PARTIAL |
| 4.2 Percent vs. ppt change | "What is the inflation rate?" | `search_series._search_cu` | Returns CPI-U all-items index (SA0) — not a percent-change series | Critical | Clarify: index level vs. 1-month % change vs. 12-month % change | Code+Prompt | None | OPEN |
| 4.3 Time period | "What industry added the most jobs last month?" | No handler | No comparison-window logic exists | Critical | Require explicit comparison period or apply documented default + disclose | Code | None | OPEN |
| 4.4 Geography | "Show employment in Washington" | `_search_sm` via `_area_tokens` | Returns first catalog hit for "Washington" (could be state or DC) | High | Detect multiple geographic matches; present options | Code | None | OPEN |
| 4.5 Household vs. establishment | "How many jobs were added?" | `search_flagship` word-match | Likely returns CE nonfarm payrolls (keyword "jobs"→"01") but not guaranteed | High | Clarify if query could mean household employment (LN) or payroll (CE) | Code+Prompt | None | OPEN |
| 4.6 Stock vs. flow | "How many people lost jobs?" | `search_flagship` | No stock/flow detection; random keyword match | Critical | Detect stock/flow ambiguity; clarify among unemployed job losers, layoffs, employment decline | Prompt+Code | None | OPEN |
| 4.7 CPI vs. inflation | "Give me the inflation rate" | `search_series._search_cu` | Returns `CUUR0000SA0` (index level) or SA equivalent | Critical | Clarify: index vs. 1-month % change vs. 12-month % change | Code+Prompt | None | OPEN |
| 4.8 Industry rankings | "Which industry added the most jobs?" | No handler | No ranking logic exists in any tool | Critical | Require comparison period; build multi-series ranking response | Code | None | OPEN |
| 4.9 Broad labor market | "How is the labor market doing?" | `search_flagship` word-match | Returns first keyword match; likely CE nonfarm | High | Define multi-indicator overview or ask for specific topic | Product+Code | None | OPEN |
| 4.10 Seasonal adjustment | "Show payroll employment" | `search_series` line 194 | Defaults to `U` (unadjusted) | High | Default to `S` for CE headline series; disclose default | Code+Config | None | OPEN |
| 4.11 Frequency | "Annual average unemployment" | No handler | No frequency detection; monthly series returned | Medium | Detect annual-average request; use `annual_average=True` flag in v2 | Code | None | OPEN |
| 4.12 Units/scale | "How many unemployed?" | `answer_bls_question` | Returns series in thousands; value displayed as published string | Medium | Disclose "thousands of persons" unit in response summary | Prompt+Code | None | OPEN |
| 4.13 Demographics | "Unemployment rate for young workers" | No handler | No demographic dimension parsing | Medium | Detect demographic qualifier; clarify or search LN demographic series | Code | None | OPEN |
| 4.14 Industry/occupation | "Show healthcare employment" | `search_series._search_ce` | Builds CE total nonfarm (default `000000`) — not healthcare | High | Extract industry from query; map to industry code before building series ID | Code | None | OPEN |
| 4.15 Conversational follow-up | "What about California?" | Stateless per-call | No context; query starts fresh each call | High | Add context-carry for geographic and series dimensions from prior turn | Architecture | None | OPEN |
| 4.16 Unavailable request | "Show weekly unemployment claims" | `search_flagship` | No initial claims series in flagship; returns no-match error | Low | Explain unavailability; do not substitute a different concept | Code | Partial (no-match test) | PARTIAL |

---

## E. FINDINGS

### FINDING-001
- **Severity:** Critical
- **Confidence:** Confirmed
- **Category:** 4.1, 4.5, 4.6 (level vs. rate; household vs. establishment; stock vs. flow)
- **File:** [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py)
- **Location:** `_discover_series`, line 68 — `best = hits[0]`
- **Current behavior:** Takes the first result from a word-count-ranked list without any
  eligibility check or measure-type comparison.
- **Evidence:** Code reads `hits = search_flagship(question, limit=3)` then `best = hits[0]`.
  No conditional on `measure_type`, `concept`, or any semantic dimension.
- **Failure scenario:** "Show me employment" → `search_flagship("show me employment")` →
  top result is `CES0000000001` (Total Nonfarm Payrolls, level, thousands) purely because
  "employment" and "nonfarm" appear in its keywords. A user wanting the
  employment-population ratio receives the wrong series silently.
- **User impact:** Wrong data returned and labelled as correct. No disclosure that an
  assumption was made.
- **Root cause:** No intent schema; no structured comparison between query semantics and
  candidate semantics.
- **Recommended resolution:** Introduce a structured `QueryIntent` dataclass that captures
  `requested_measure_type` and `requested_concept`. Compare against `FlagshipEntry.measure_type`
  and `FlagshipEntry.concept` for each candidate. If two or more candidates remain after
  filtering and they represent different concepts or measure types, generate a clarification
  question before proceeding.
- **Layer:** Code (application logic)
- **Tests required:** `test_employment_query_generates_clarification`,
  `test_employment_level_resolves_to_CE_not_LN_ratio`

---

### FINDING-002
- **Severity:** Critical
- **Confidence:** Confirmed
- **Category:** 4.7 (CPI index vs. inflation rate)
- **File:** [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** `_search_cu`, lines 511–523; `_SURVEY_HINTS` line 87 (`"inflation": "CU"`)
- **Current behavior:** Any query containing "inflation" or "cpi" is routed to CU survey and
  resolves to item code `SA0` (all items) — the index-level series `CUUR0000SA0` or its SA
  equivalent. This is an index value, not a percent-change figure.
- **Evidence:** `_CU_ITEM_HINTS` maps `"cpi"` → `"SA0"`. `_search_cu` builds
  `CU + seasonal + "R" + "0000" + "SA0"` as the candidate. No percent-change series exists
  in the returned candidate set.
- **Failure scenario:** "What is the inflation rate?" → returns `CUUR0000SA0` with value
  ~314 (index). The user expected a percent-change figure (~3.x%).
- **User impact:** Numerically incorrect answer. Index level and percent change differ by
  two orders of magnitude and are not interchangeable.
- **Root cause:** No distinction between "CPI index" and "inflation rate" in the search and
  discovery layers.
- **Recommended resolution:** Add a `percent_change` measure type to the vocabulary.
  When "rate" or "inflation rate" or "percent change" is in the query, do not auto-resolve
  to the index-level series. Clarify: "By inflation, do you want the CPI index level, the
  one-month percent change, or the 12-month percent change?"
- **Layer:** Code + Prompt
- **Tests required:** `test_inflation_rate_does_not_return_index_level`,
  `test_inflation_query_generates_clarification`

---

### FINDING-003
- **Severity:** Critical
- **Confidence:** Confirmed
- **Category:** 4.10 (seasonal adjustment)
- **File:** [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** Line 194 — `seasonal = _match_first(query, _SEASONAL_HINTS) or "U"`
- **Current behavior:** Seasonal adjustment defaults to `"U"` (not seasonally adjusted) for
  every query that does not contain an explicit seasonal hint.
- **Evidence:** Hardcoded `or "U"` fallback. No documentation of this default anywhere in
  user-facing output.
- **Failure scenario:** "Show payroll employment change" → `search_series` builds a CE series
  with `seasonal="U"`. The published headline CE figure is seasonally adjusted (`CES0000000001`).
  An NSA figure returned as the answer to a payroll employment question could differ
  substantially from the headline.
- **User impact:** Returns NSA data where SA is the standard. Comparisons made by the user
  with published BLS releases will not match.
- **Root cause:** No survey-specific seasonal-adjustment defaults. The fallback is a single
  global default that is wrong for most headline series.
- **Recommended resolution:** Define per-survey seasonal-adjustment defaults in `config.py`
  or a constants file. For CE and LA, default to `"S"` (seasonally adjusted) as the
  headline figure. For surveys where SA is not available or less common (MP, EI), use `"U"`.
  Disclose the applied default in the response.
- **Layer:** Code + Configuration
- **Tests required:** `test_ce_search_defaults_to_seasonally_adjusted`,
  `test_seasonal_default_disclosed_in_response`

---

### FINDING-004
- **Severity:** High
- **Confidence:** Confirmed
- **Category:** 4.3 (time period), 4.8 (rankings)
- **File:** No existing file
- **Location:** No ranking or comparison logic exists anywhere in the codebase.
- **Current behavior:** Ranking queries ("what industry added the most jobs?") are passed to
  `search_flagship`, which returns a single series based on word matching. No multi-series
  comparison, no period specification, no ranking computation.
- **Failure scenario:** "What industry added the most jobs last month?" → returns
  `CES0000000001` (total nonfarm) — not an industry breakdown or a comparison.
- **User impact:** Completely wrong answer type. User asked for a ranking and receives a
  single aggregate series.
- **Root cause:** No ranking capability exists in the tool suite.
- **Recommended resolution:** This is partly a product decision (which industries to compare,
  at what level of detail, over what period). The minimum requirement is: detect ranking
  intent; require a comparison window; return an error or clarification question until a
  window is specified. Full ranking would require a multi-series retrieval and comparison.
- **Layer:** Code (new capability) + Product decision
- **Tests required:** `test_ranking_query_requires_comparison_period`,
  `test_ranking_query_does_not_auto_select_aggregate_series`

---

### FINDING-005
- **Severity:** High
- **Confidence:** Confirmed
- **Category:** 4.4 (geography)
- **File:** [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** `_search_sm`, lines 313–360; `_area_tokens`, lines 272–310
- **Current behavior:** `_area_tokens` extracts word tokens from the query and searches the
  SM catalog by substring. The first few matches are used. No disambiguation when multiple
  areas match (e.g. "Washington" matches Washington state and Washington DC metro area and
  multiple Washington-named metros).
- **Evidence:** `area_hits.extend(catalog.search("sm", "area", tok, max_results=3))` —
  takes up to 3 area hits per token and uses all of them, never asking the user which one.
- **Failure scenario:** "Show employment in Washington" → returns series for all Washington
  areas that matched: could include Washington DC metro, Washington state, etc.
- **User impact:** Returns data for the wrong geographic area.
- **Root cause:** No geographic disambiguation; multiple matches are silently used without
  user confirmation.
- **Recommended resolution:** When more than one geographic area matches, present the
  options and ask the user to confirm before building the series ID.
- **Layer:** Code
- **Tests required:** `test_ambiguous_geography_generates_clarification`

---

### FINDING-006
- **Severity:** High
- **Confidence:** Confirmed
- **Category:** 4.5 (household vs. establishment)
- **File:** [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py) and [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** `_discover_series` and `_SURVEY_HINTS`
- **Current behavior:** "Employment" keywords match both CE (payroll/establishment) and LN
  (CPS/household) series. The first word-count match wins. No household-vs-establishment
  disambiguation exists.
- **Evidence:** `_SURVEY_HINTS` has `"civilian employment": "LN"` but plain `"employment"`
  has no survey hint. `search_flagship` will return whichever series accumulates more
  word-count score, which varies by exact phrasing.
- **Failure scenario:** "How many people are employed?" → could return CE nonfarm payrolls
  (jobs) or LN civilian employment (persons). These are different concepts measuring
  different universes.
- **User impact:** Returns the wrong conceptual measure. "People employed" ≠ "payroll jobs".
- **Root cause:** No household/establishment disambiguation in the routing logic.
- **Recommended resolution:** Detect when both CE and LN series are plausible candidates
  and generate a clarification question: "Do you want payroll employment (jobs on
  establishment payrolls) or household employment (employed persons from the CPS)?"
- **Layer:** Code + Prompt
- **Tests required:** `test_employment_query_offers_household_vs_establishment_choice`

---

### FINDING-007
- **Severity:** High
- **Confidence:** Confirmed
- **Category:** 4.6 (stock vs. flow)
- **File:** [`src/example_server/prompts/bls_assistant.py`](src/example_server/prompts/bls_assistant.py)
  and [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py)
- **Location:** `bls_assistant` prompt; `_discover_series`
- **Current behavior:** "How many people lost jobs?" — no stock/flow detection. Query is
  passed to `search_flagship` which may match JT layoffs and discharges (`JTS000000000000LDL`),
  LN unemployed job losers, or CE employment change, depending on word scoring.
- **Evidence:** `search_flagship("how many people lost jobs", limit=3)` — the word "jobs"
  scores for CE entries, "lost" is not in any keyword list. Result is nondeterministic across
  rephrasings.
- **Failure scenario:** Returns layoffs-and-discharges (a flow) when user meant unemployed
  persons classified as job losers (a stock), or returns employment decline.
- **User impact:** Materially different numbers (e.g. JOLTS layoffs ~1.6M/month vs. LN
  unemployed job losers ~3M+ stock).
- **Root cause:** No stock/flow vocabulary in the routing layer.
- **Recommended resolution:** Add stock/flow detection keywords. When a query triggers
  multiple plausible stock/flow interpretations, generate a clarification question.
- **Layer:** Prompt + Code
- **Tests required:** `test_lost_jobs_query_generates_clarification_not_auto_select`

---

### FINDING-008
- **Severity:** High
- **Confidence:** Confirmed
- **Category:** 4.15 (conversational follow-up)
- **File:** [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py)
- **Location:** Tool signature — no context parameter
- **Current behavior:** `answer_bls_question` accepts `question`, `series_id`, `start_year`,
  `end_year`. No `context` or `prior_dimensions` parameter. Each call is fully stateless.
- **Evidence:** Tool signature at line 167 — no conversation context parameter.
- **Failure scenario:** "What is the unemployment rate?" followed by "What about California?"
  — the follow-up has no way to inherit the `unemployment_rate` concept; it starts fresh.
- **User impact:** Follow-up queries cannot be meaningfully answered without repeating the
  full context in each turn.
- **Root cause:** Stateless tool design with no context-carry mechanism.
- **Recommended resolution:** Add an optional `context` parameter to `answer_bls_question`
  containing previous `series_id`, `measure_type`, `concept`, and `geography`. Document
  which dimensions are safe to inherit and which require explicit re-specification.
- **Layer:** Architecture + Code
- **Tests required:** `test_follow_up_geography_inherits_prior_concept`

---

### FINDING-009
- **Severity:** Medium
- **Confidence:** Confirmed
- **Category:** 4.1 (level vs. rate — JT)
- **File:** [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** `_search_jt`, line 415 — `ratelevel_code="L"` hardcoded
- **Current behavior:** JT searches always build level series (`ratelevel_code="L"`).
  Rate series (job openings rate, hires rate, etc.) are never returned from `search_series`.
- **Evidence:** `build_id("JT", ..., ratelevel_code="L")` — hardcoded.
- **Failure scenario:** "What is the job openings rate?" → returns job openings level (thousands)
  not the openings rate (percent).
- **User impact:** Wrong measure type returned for rate queries.
- **Root cause:** JT rate/level not extracted from query.
- **Recommended resolution:** Extend `_JT_DE_HINTS` to also capture rate keywords and pass
  `ratelevel_code` dynamically based on query context. Or detect "rate" in the query and
  set `ratelevel_code="R"`.
- **Layer:** Code
- **Tests required:** `test_jt_rate_query_returns_rate_series`

---

### FINDING-010
- **Severity:** Medium
- **Confidence:** Confirmed
- **Category:** 4.12 (units/scale)
- **File:** [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py)
- **Location:** `_build_summary`, lines 40–60
- **Current behavior:** Summary sentence format: "Most recent value for {label}: {value} ({period})."
  No unit disclosure. A value of "157823" (thousands of persons) is presented without the
  "thousands" qualifier.
- **Evidence:** `_build_summary` constructs the summary string with no unit field.
  `FlagshipEntry.unit` is available but not used in the summary.
- **Failure scenario:** User sees "Most recent value for CE: 157823 (December 2024)" and
  interprets it as 157,823 persons rather than 157.8 million.
- **User impact:** Order-of-magnitude misinterpretation.
- **Root cause:** Unit not propagated to the summary string.
- **Recommended resolution:** Include `unit` in the summary: "Most recent value: 157,823 thousands
  of persons." Alternatively, include it as a top-level `unit` field in the response.
- **Layer:** Code
- **Tests required:** `test_summary_includes_unit_for_level_series`

---

### FINDING-011
- **Severity:** Medium
- **Confidence:** Confirmed
- **Category:** 4.14 (industry scope)
- **File:** [`src/example_server/tools/search_series.py`](src/example_server/tools/search_series.py)
- **Location:** `_search_ce`, lines 363–376 — `industry_code="000000"` hardcoded
- **Current behavior:** CE search always uses total nonfarm (`industry_code="000000"`).
  No industry extraction from the query. "Show healthcare employment" returns total nonfarm.
- **Evidence:** `build_id("CE", ..., industry_code="000000", ...)` hardcoded.
- **Failure scenario:** "Show manufacturing employment" → returns total nonfarm payrolls
  instead of manufacturing.
- **User impact:** Returns the wrong sector's data.
- **Root cause:** No industry code extraction in `_search_ce`.
- **Recommended resolution:** Add CE industry lookup from the query using `catalog.search("ce",
  "industry", ...)`. When an industry match is found, use it. When multiple industries match,
  present options.
- **Layer:** Code
- **Tests required:** `test_ce_search_extracts_industry_from_query`

---

### FINDING-012
- **Severity:** Medium
- **Confidence:** Confirmed
- **Category:** 4.1, 4.9 (broad labor market)
- **File:** [`src/example_server/prompts/bls_assistant.py`](src/example_server/prompts/bls_assistant.py)
- **Location:** Entire prompt
- **Current behavior:** System prompt describes tool workflow but contains no disambiguation
  guidance, no instruction to clarify ambiguous queries, no instruction about measure types,
  no instruction about seasonal adjustment defaults, and no instruction about when to avoid
  calling `get_series_data`.
- **Evidence:** Prompt text at lines 14–64 — no mention of clarification, ambiguity,
  measure type, or household vs. establishment.
- **Failure scenario:** LLM using this prompt has no guidance to ask "do you want the rate or
  the level?" before calling `get_series_data`.
- **User impact:** LLM silently selects incorrect series.
- **Root cause:** Prompt does not specify disambiguation responsibilities.
- **Recommended resolution:** Add disambiguation section to prompt: (a) define when to
  clarify vs. auto-resolve; (b) list measure-type distinctions; (c) specify seasonal-adjustment
  disclosure requirement; (d) prohibit calling `get_series_data` when measure type is
  materially ambiguous.
- **Layer:** Prompt
- **Tests required:** Prompt evaluation tests (model-level)

---

### FINDING-013
- **Severity:** Low
- **Confidence:** Confirmed
- **Category:** 4.3 (time period)
- **File:** [`src/example_server/tools/answer_bls_question.py`](src/example_server/tools/answer_bls_question.py)
- **Location:** `_validate_locally`, lines 77–96
- **Current behavior:** Validation comment says "length and catalog mismatches are surfaced as
  informational issues but do NOT block retrieval." The API is the authoritative validator.
- **Evidence:** `return True, []` after prefix check regardless of catalog mismatches.
- **Failure scenario:** A model-generated or slightly incorrect series ID passes local
  validation and is sent to the BLS API, which either returns empty data or an error.
- **User impact:** Wasted API quota; confusing error message returned to user.
- **Root cause:** Intentional leniency in local validation — documented in the comment but
  still creates a path where invalid IDs reach the API.
- **Recommended resolution:** Return catalog mismatch issues as warnings in the response,
  not silently. The existing behavior is acceptable if the warnings are surfaced to the LLM
  client, allowing it to retry with corrected IDs before consuming API quota.
- **Layer:** Code
- **Tests required:** `test_catalog_mismatch_surfaced_as_warning`

---


---

## F. OPTIONS AND TRADEOFFS

### Option F-1: Prompt-Only Interpretation vs. Typed Intent Parsing

**Prompt-only:** Add disambiguation instructions to `bls_assistant.py`. Rely entirely on the
LLM to detect ambiguity and ask clarification questions.

| | Benefits | Risks |
|-|----------|-------|
| Prompt-only | Low implementation cost; works across query types; flexible | Non-deterministic; different LLMs behave differently; no enforcement; untestable without model evals; regression-prone |
| Typed intent | Deterministic; testable; enforced; works independently of LLM quality | Higher implementation cost; requires new data structures; needs calibration |

**Recommendation:** Use typed intent parsing as the enforcement layer. Use prompt improvements
as a complementary guidance layer. Deterministic code should enforce the policy; prompts
should guide the LLM toward providing the correct intent fields.

---

### Option F-2: Numeric Confidence vs. Deterministic Eligibility

**Numeric confidence:** Assign a similarity score to each candidate; auto-select above a
threshold; clarify below.

**Deterministic eligibility:** Define hard rules: reject candidates with conflicting
measure_type; reject candidates with conflicting geography; require explicit resolution when
two eligible candidates represent different concepts.

| | Benefits | Risks |
|-|----------|-------|
| Numeric | Handles fuzzy queries; works without full intent parsing | Score is not calibrated; high lexical match can override semantic conflict; thresholds require evaluation data |
| Deterministic | Predictable; testable without model; no calibration needed | May over-clarify simple cases; requires explicit rule authoring |

**Recommendation:** Use deterministic eligibility as the primary mechanism. The existing
`measure_type` and `concept` fields in `FlagshipEntry` provide the basis for hard rules
without any scoring. Add numeric scoring only after deterministic rules are in place and
the need for fuzzy ranking has been demonstrated.

---

### Option F-3: Combined Search-and-Retrieve vs. Separate Discovery and Retrieval

**Current state:** `answer_bls_question` combines discovery and retrieval in one call.

**Separate tools:** Keep `suggest_series` and `search_series` as pure discovery tools.
Add a `resolve_intent` tool that takes discovered candidates and user intent and either
returns a resolved series ID or a clarification question. `get_series_data` remains the
only retrieval tool.

| | Benefits | Risks |
|-|----------|-------|
| Combined (current) | One call; simpler for callers | Ambiguity cannot be interrupted between steps |
| Separated | Clarification can occur between discovery and retrieval; testable | More LLM orchestration required; more tool calls per query |

**Recommendation:** Keep `answer_bls_question` as a convenience wrapper but add an ambiguity
gate inside it that returns a clarification response (not a retrieval response) when material
ambiguity is detected. The gate is a new internal function, not a new external tool. This
preserves the single-call convenience while adding enforcement.

---

### Option F-4: Single Clarification vs. Staged Clarification

**Single:** Ask one clarification question that covers all unresolved dimensions.

**Staged:** Ask the most material question first; re-route after the answer.

**Recommendation:** Single clarification for the most material unresolved choice. Staged
clarification only if the first question resolves to a still-ambiguous state (which should
be uncommon for well-designed questions).

---

### Option F-5: Central Policy Module vs. Distributed Validation

**Central policy:** A single `ambiguity.py` module that defines all disambiguation rules,
default policies, and clarification generation logic.

**Distributed:** Each tool handles its own disambiguation.

**Recommendation:** Central policy module. Disambiguation rules should be consistent across
`answer_bls_question`, `search_series`, and any future orchestration layer. Distributed
implementation leads to inconsistency and duplication.

---

## G. RECOMMENDED TARGET DESIGN

### Intent Schema

Add a `QueryIntent` dataclass to `models.py`:

```python
@dataclass
class QueryIntent:
    original_query: str
    normalized_query: str
    concept: str | None = None           # e.g. "unemployment_rate", "nonfarm_payrolls"
    requested_measure_type: str | None = None  # "level", "rate", "index", "percent_change"
    dataset: str | None = None           # Survey prefix, e.g. "CE", "LN", "CU"
    geography_type: str | None = None    # "national", "state", "metro"
    geography_value: str | None = None   # e.g. "17" (Illinois FIPS)
    seasonal_adjustment: str | None = None  # "S" or "U"
    frequency: str | None = None         # "monthly", "quarterly", "annual"
    start_period: str | None = None
    end_period: str | None = None
    comparison_period: str | None = None
    calculation_type: str | None = None  # "level", "percent_change", "ppt_change", "ranking"
    ranking_metric: str | None = None
    ranking_direction: str | None = None # "highest", "lowest"
    result_limit: int | None = None
    applied_defaults: list[str] = field(default_factory=list)
    inherited_context: list[str] = field(default_factory=list)
    unresolved_dimensions: list[str] = field(default_factory=list)
    candidate_series: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    clarification_options: list[str] = field(default_factory=list)
```

### Candidate Schema

Add to `models.py`:

```python
@dataclass
class CandidateSeries:
    series_id: str
    description: str
    dataset: str
    concept: str
    measure_type: str
    unit: str
    geography: str | None
    seasonal_adjustment: str
    frequency: str
    available_date_range: tuple[str, str] | None
    match_score: int
    mismatch_reasons: list[str] = field(default_factory=list)
    eligible: bool = True
    rejection_reason: str | None = None
```

### Ambiguity Policy Module

Create `src/example_server/ambiguity.py`:

```python
# Deterministic eligibility rules:

def filter_candidates(
    intent: QueryIntent,
    candidates: list[CandidateSeries],
) -> list[CandidateSeries]:
    """Return only candidates compatible with the intent.
    
    Rejects candidates where:
    - measure_type conflicts with requested_measure_type
    - seasonal_adjustment conflicts with an explicit request
    - geography conflicts with a resolved geography
    """

def detect_unresolved_dimensions(
    intent: QueryIntent,
    eligible_candidates: list[CandidateSeries],
) -> list[str]:
    """Return names of dimensions that remain materially unresolved.
    
    Returns non-empty list when:
    - Two or more eligible candidates have different concepts
    - Two or more eligible candidates have different measure_types
    - requested_measure_type is 'percent_change' but only index candidates exist
    - Household vs. establishment not resolved when both are plausible
    - Stock vs. flow not resolved when both are plausible
    """

def generate_clarification(
    intent: QueryIntent,
    eligible_candidates: list[CandidateSeries],
    unresolved: list[str],
) -> str:
    """Return a concise clarification question for the most material unresolved dimension.
    
    Uses user-friendly language, not BLS series IDs.
    Offers 2–4 concrete options when possible.
    """

SAFE_DEFAULTS: dict[str, str] = {
    # survey → seasonal_adjustment
    "CE": "S",   # CE headline is seasonally adjusted
    "LA": "S",   # LA headline is seasonally adjusted
    "LN": "S",   # LN headline is seasonally adjusted
    "JT": "S",   # JOLTS headline is seasonally adjusted
    "CU": "U",   # CPI-U is typically published NSA for all-items
    "CW": "U",   # CPI-W NSA is the reference series for COLA
    "PR": "S",
    "SM": "U",   # State/metro data is predominantly NSA
}
```

### Validation Sequence

Inside `answer_bls_question`:

```
1. Parse QueryIntent from query text
2. Run search_flagship to get candidate FlagshipEntry list
3. Convert to CandidateSeries list (with structured metadata)
4. Apply filter_candidates: remove ineligible candidates
5. Run detect_unresolved_dimensions on remaining eligible candidates
6. If unresolved dimensions exist:
   a. Generate clarification question
   b. Return clarification response (do not call BLS API)
7. If single eligible candidate:
   a. Apply and log safe defaults for any undeclared dimensions
   b. Call BLS API
   c. Return response with applied_defaults disclosed
8. If zero eligible candidates:
   a. Return unavailability explanation
```

### Safe-Default Mechanism

- Defaults defined in `SAFE_DEFAULTS` dict in `ambiguity.py` (or `config.py`).
- Each applied default logged in `QueryIntent.applied_defaults`.
- Applied defaults disclosed in response under a `"defaults_applied"` key.
- Defaults are survey-specific, not global.

### Clarification Mechanism

- Clarification question returned as `{"clarification_required": true, "question": "...", "options": [...]}`.
- BLS API is never called when this is returned.
- The LLM re-calls `answer_bls_question` with additional dimensions after user responds.

### Context Inheritance

Add optional `context` parameter to `answer_bls_question`:

```python
context: dict | None = None  # {"series_id": ..., "concept": ..., "measure_type": ..., "geography": ...}
```

- When provided, inherit only dimensions safe to carry forward.
- Do not inherit `measure_type` or `concept` across conceptually unrelated follow-ups.
- Log inherited dimensions in `QueryIntent.inherited_context`.

### Calculation Validation

Before computing or displaying percent changes:

- Confirm the series has `measure_type="index"` or `measure_type="level"`.
- Confirm adjacent observations have the same frequency and seasonal adjustment.
- Never mix NSA and SA values in a change calculation.

### Ranking Comparability

Before ranking across industries:

- Confirm all candidates have identical frequency, seasonal adjustment, units, and reference period.
- Require an explicit comparison period.
- Reject ranking if any candidate has incompatible metadata.

### Logging and Telemetry

Each `answer_bls_question` call should log (without user PII):

- `normalized_intent`: serialized `QueryIntent`
- `candidates_considered`: list of series IDs
- `applied_defaults`: what defaults were used
- `inherited_context`: what was inherited from prior turn
- `rejection_reasons`: why candidates were rejected
- `selected_series`: final series ID
- `selection_reason`: why this series was chosen
- `clarification_decision`: whether clarification was returned
- `bls_api_called`: boolean

---

## H. FILE-BY-FILE CHANGE PLAN

### H-1: `src/example_server/models.py`
- **Reason for change:** Add `QueryIntent` and `CandidateSeries` dataclasses.
- **Current responsibility:** `BLSSeriesRequest`, `ResponseFormat`, `PaginationParams`.
- **Proposed responsibility:** Add intent and candidate schemas.
- **Functions/sections affected:** None existing; add new dataclasses.
- **New interfaces:** `QueryIntent`, `CandidateSeries`.
- **Compatibility concerns:** Additive only; no existing imports change.
- **Tests affected:** New tests for `QueryIntent` construction.

### H-2: `src/example_server/ambiguity.py` (NEW FILE)
- **Reason for creation:** Centralise all disambiguation logic. No existing file contains
  this responsibility. Distributing it across tool files would cause duplication.
- **Responsibilities:** `filter_candidates`, `detect_unresolved_dimensions`,
  `generate_clarification`, `SAFE_DEFAULTS`, `parse_intent_from_query`.
- **Dependencies:** `models.py` (QueryIntent, CandidateSeries), `bls_flagship_series.py`
  (FlagshipEntry), `config.py` (settings).
- **Tests affected:** New test file `tests/test_ambiguity.py`.

### H-3: `src/example_server/tools/answer_bls_question.py`
- **Reason for change:** Replace `hits[0]` auto-selection with ambiguity gate; add context
  parameter; add applied-defaults disclosure.
- **Current responsibility:** Orchestrates discovery → validation → retrieval.
- **Proposed responsibility:** Same, plus intent parsing, eligibility filtering, clarification
  gate, default disclosure, context carry.
- **Functions/sections affected:** `_discover_series` (replace or extend); add intent parsing
  before discovery; add gate between discovery and retrieval.
- **New interfaces:** `context` parameter; clarification response shape.
- **Compatibility concerns:** Response shape changes (adds `clarification_required`,
  `defaults_applied`). Clients using the tool need to handle new response keys.
- **Tests affected:** `test_tools_answer_bls_question.py` — extend with ambiguity scenarios.

### H-4: `src/example_server/tools/search_series.py`
- **Reason for change:** Replace hardcoded `"U"` seasonal default; add per-survey defaults;
  add geographic disambiguation; add CE industry extraction; add JT rate/level detection.
- **Current responsibility:** Multi-survey catalog search with hardcoded defaults.
- **Proposed responsibility:** Same, with safe per-survey seasonal defaults, industry
  extraction for CE, rate/level detection for JT.
- **Functions/sections affected:** Line 194 (seasonal default); `_search_ce` (industry);
  `_search_jt` (rate/level); `_search_sm` (geographic disambiguation).
- **Compatibility concerns:** Changing the seasonal default for CE from `U` to `S` changes
  search results. This is correct but may change existing test expectations.
- **Tests affected:** `test_tools_search_suggest.py` — update seasonal default tests.

### H-5: `src/example_server/tools/suggest_series.py`
- **Reason for change:** Expose `measure_type` conflict detection in the return value to
  help callers understand when multiple measure types are present in suggestions.
- **Current responsibility:** Returns ranked suggestions with `concept`, `measure_type`, `unit`.
- **Proposed responsibility:** Same plus `has_measure_type_conflict: bool` flag.
- **Functions/sections affected:** Return value construction.
- **Compatibility concerns:** Additive; new field.
- **Tests affected:** `test_tools_search_suggest.py`.

### H-6: `src/example_server/prompts/bls_assistant.py`
- **Reason for change:** Add disambiguation guidance; clarification policy; seasonal
  disclosure requirements; prohibition on calling `get_series_data` before resolution.
- **Current responsibility:** Tool workflow description.
- **Proposed responsibility:** Add disambiguation section.
- **Functions/sections affected:** `bls_assistant` prompt string.
- **Compatibility concerns:** Longer prompt; potential behavior change for LLM clients.
- **Tests affected:** Prompt evaluation (model-level).

### H-7: `src/example_server/config.py`
- **Reason for change:** Add `SEASONAL_DEFAULTS` dict; add ambiguity policy feature flags
  (`CLARIFY_ON_MEASURE_AMBIGUITY`, `CLARIFY_ON_GEOGRAPHY_AMBIGUITY`).
- **Current responsibility:** Transport and API-key settings.
- **Proposed responsibility:** Same plus ambiguity policy settings.
- **Functions/sections affected:** `Settings` class — add fields; add constants.
- **Compatibility concerns:** Additive only.
- **Tests affected:** Existing config tests; new policy tests.

### H-8: `tests/test_ambiguity.py` (NEW FILE)
- **Reason for creation:** Test all ambiguity detection, eligibility filtering, default
  application, and clarification generation logic.
- **Responsibilities:** Unit tests for every function in `ambiguity.py`.

### H-9: `tests/test_tools_answer_bls_question.py`
- **Reason for change:** Extend with ambiguity scenario tests (see Section J).

---

## I. IMPLEMENTATION PHASES

### Phase 1: Tests That Reproduce Current Ambiguity Failures
- **Goal:** Establish a regression test baseline that documents current incorrect behaviors.
  These tests should initially fail (or confirm current bad behavior).
- **Files affected:** `tests/test_ambiguity_regression.py` (new)
- **Prerequisites:** None
- **Expected behavior:** Tests document that `answer_bls_question("Show me employment")`
  silently returns a single series without clarification. Tests document that "inflation rate"
  returns an index-level series. Tests document that seasonal default is `U`.
- **Tests:** See Section J
- **Risks:** None — read-only phase
- **Completion criteria:** All regression tests written and passing against current behavior

---

### Phase 2: Intent and Candidate Data Structures
- **Goal:** Add `QueryIntent` and `CandidateSeries` to `models.py`.
- **Files affected:** `src/example_server/models.py`
- **Prerequisites:** Phase 1
- **Expected behavior:** Data structures importable; no behavior change
- **Tests:** `tests/test_ambiguity.py` — dataclass construction tests
- **Risks:** None — additive
- **Completion criteria:** `QueryIntent` and `CandidateSeries` importable and all field
  defaults correct

---

### Phase 3: Deterministic Eligibility Rules
- **Goal:** Create `src/example_server/ambiguity.py` with `filter_candidates`,
  `detect_unresolved_dimensions`, `SAFE_DEFAULTS`.
- **Files affected:** `src/example_server/ambiguity.py` (new)
- **Prerequisites:** Phase 2
- **Expected behavior:** Given a query intent and candidate list, eligibility rules correctly
  identify conflicts and unresolved dimensions
- **Tests:** `tests/test_ambiguity.py` — eligibility and unresolved-dimension tests
- **Risks:** Eligibility rules may be overly broad initially; tune in Phase 6
- **Completion criteria:** All eligibility tests pass; no regression in existing tests

---

### Phase 4: Clarification Gate
- **Goal:** Integrate ambiguity gate into `answer_bls_question`. BLS API must not be called
  when `detect_unresolved_dimensions` returns a non-empty list.
- **Files affected:** `src/example_server/tools/answer_bls_question.py`
- **Prerequisites:** Phase 3
- **Expected behavior:** Ambiguous queries return `{"clarification_required": true, ...}`;
  BLS API not called
- **Tests:** `tests/test_tools_answer_bls_question.py` — clarification and no-API-call tests
- **Risks:** May initially over-clarify; acceptability depends on product decision (see Section K)
- **Completion criteria:** All tool-call safety tests pass; regression tests from Phase 1
  now show clarification behavior instead of silent wrong selection

---

### Phase 5: Prompt and Tool-Description Alignment
- **Goal:** Update `bls_assistant.py` prompt to describe disambiguation policy. Update tool
  descriptions in `answer_bls_question` and `get_series_data` to state when clarification
  is required.
- **Files affected:** `src/example_server/prompts/bls_assistant.py`;
  tool annotation strings in `answer_bls_question.py` and `get_series_data.py`
- **Prerequisites:** Phase 4
- **Expected behavior:** LLM client has guidance aligned with the deterministic code behavior
- **Tests:** Prompt evaluation tests (model-level)
- **Risks:** Prompt changes affect LLM behavior non-deterministically; evaluate before deploy
- **Completion criteria:** Prompt evaluation suite passes; no regression in unit tests

---

### Phase 6: Defaults and Configuration
- **Goal:** Replace hardcoded `"U"` seasonal default in `search_series.py` with per-survey
  defaults from `config.py`. Add CE industry extraction. Add JT rate/level detection.
  Add context-carry parameter to `answer_bls_question`.
- **Files affected:** `src/example_server/config.py`;
  `src/example_server/tools/search_series.py`;
  `src/example_server/tools/answer_bls_question.py`
- **Prerequisites:** Phase 4
- **Expected behavior:** Seasonal defaults are survey-appropriate and disclosed; industry
  queries return industry-specific series; JT rate queries return rate series
- **Tests:** `tests/test_tools_search_suggest.py` — seasonal default tests;
  `tests/test_ambiguity.py` — default-disclosure tests
- **Risks:** Changing CE seasonal default from `U` to `S` is a breaking change for existing
  behavior. Existing tests that expect `U` must be updated.
- **Completion criteria:** All search tests pass with updated defaults; default disclosed in
  response

---

### Phase 7: Observability
- **Goal:** Add structured logging to `answer_bls_question` covering all fields in the
  logging spec (Section G).
- **Files affected:** `src/example_server/tools/answer_bls_question.py`
- **Prerequisites:** Phase 4
- **Expected behavior:** Each call emits a structured log entry; no PII exposed
- **Tests:** `tests/test_tools_answer_bls_question.py` — log-emission tests
- **Risks:** Logging format must be agreed before implementation
- **Completion criteria:** Log entries emitted and testable

---

### Phase 8: Full Regression Evaluation
- **Goal:** Run all 28 query walkthroughs from Section 12 against the updated system.
  Confirm each query produces the expected behavior.
- **Files affected:** New test file `tests/test_query_walkthroughs.py`
- **Prerequisites:** Phases 1–7
- **Expected behavior:** Each walkthrough query resolves, clarifies, or declines correctly
- **Tests:** All walkthrough tests pass
- **Risks:** Some queries may require product decisions not yet made (Section K)
- **Completion criteria:** All walkthrough tests pass; no regression in any existing test

---

## J. TEST PLAN

### Ambiguity Regression Tests (Phase 1)

```
test_employment_query_currently_auto_selects_without_clarification
  Input: question="Show me employment."
  Expected current behavior: returns series without clarification
  Purpose: documents current gap

test_inflation_rate_currently_returns_index
  Input: question="What is the inflation rate?"
  Expected current behavior: returns CPI-U index series, not percent change
  Purpose: documents current gap

test_seasonal_default_is_currently_unadjusted
  Input: query="payroll employment"
  Expected current behavior: search_series returns U (unadjusted) series
  Purpose: documents current gap
```

### Unit Tests for Ambiguity Module (Phase 3)

```
test_filter_candidates_rejects_rate_when_level_requested
  Intent: requested_measure_type="level"
  Candidates: [CES0000000001 (level), LNS12300000 (rate)]
  Expected: LNS12300000 rejected

test_detect_unresolved_dimensions_flags_concept_conflict
  Intent: concept=None
  Candidates: [CES0000000001 (nonfarm_payrolls), LNS12000000 (civilian_employment)]
  Expected: returns ["concept"]

test_detect_unresolved_dimensions_flags_measure_type_conflict
  Intent: requested_measure_type=None
  Candidates: [CUUR0000SA0 (index), <percent_change_series> (percent_change)]
  Expected: returns ["measure_type"]

test_generate_clarification_employment_level_vs_ratio
  Intent: query="show employment", unresolved=["measure_type"]
  Candidates include both level and ratio
  Expected clarification: "Do you want the number of employed people or the
    employment-population ratio?"

test_generate_clarification_cpi_index_vs_rate
  Intent: query="what is the inflation rate", unresolved=["measure_type"]
  Expected clarification: "By inflation, do you want the CPI index level,
    the one-month percent change, or the 12-month percent change?"

test_safe_defaults_ce_is_seasonally_adjusted
  Input: survey="CE", no explicit seasonal_adjustment in intent
  Expected: SAFE_DEFAULTS["CE"] == "S"

test_safe_defaults_cu_is_unadjusted
  Input: survey="CU", no explicit seasonal_adjustment in intent
  Expected: SAFE_DEFAULTS["CU"] == "U"
```

### Tool-Call Safety Tests (Phase 4)

```
test_bls_api_not_called_when_measure_type_ambiguous
  Input: question="Show me employment."
  Expected: clarification_required=True; no fetch_bls call made

test_bls_api_not_called_when_stock_flow_ambiguous
  Input: question="How many people lost jobs?"
  Expected: clarification_required=True; no fetch_bls call made

test_bls_api_not_called_when_cpi_vs_inflation_ambiguous
  Input: question="What is the inflation rate?"
  Expected: clarification_required=True; no fetch_bls call made

test_bls_api_called_when_fully_resolved
  Input: question="What is the unemployment rate?" (unambiguous)
  Expected: clarification_required=False; fetch_bls called once

test_bls_api_not_called_when_geography_ambiguous
  Input: question="Show employment in Washington."
  Expected: clarification_required=True; no fetch_bls call made
```

### Query Walkthrough Tests (Phase 8)

```
test_walkthrough_01_show_employment
  Input: "Show me employment."
  Expected: clarification_required=True
  Clarification options: ["Payroll employment (jobs)", "Household employment (persons)", "Employment-population ratio"]

test_walkthrough_02_show_employment_level
  Input: "Show me the employment level."
  Expected: auto-resolve to CE nonfarm payrolls level; clarify household vs. payroll
  Note: "level" reduces to level measure type but household/payroll still unresolved

test_walkthrough_03_employment_population_ratio
  Input: "Show me the employment-population ratio."
  Expected: auto-resolve to LNS12300000; no clarification

test_walkthrough_06_unemployment_rate
  Input: "What is the unemployment rate?"
  Expected: auto-resolve to LNS14000000 (SA) or LAUST000000000000003; no clarification

test_walkthrough_08_unemployment_rate_california
  Input: "What is the unemployment rate in California?"
  Expected: auto-resolve to LA series for California statewide; disclose SA default

test_walkthrough_11_inflation_rate
  Input: "Give me the inflation rate."
  Expected: clarification_required=True
  Clarification: "By 'inflation rate' do you mean the CPI index level, the one-month percent
    change, or the 12-month percent change?"

test_walkthrough_15_how_many_lost_jobs
  Input: "How many people lost jobs?"
  Expected: clarification_required=True
  Clarification: "Do you mean (a) unemployed people classified as job losers, (b) layoffs and
    discharges from JOLTS, or (c) the decline in payroll employment?"

test_walkthrough_17_industry_added_most_jobs
  Input: "What industry added the most jobs?"
  Expected: clarification_required=True
  Clarification: "What time period should I use for comparison: the latest monthly change,
    the change over the past year, or another period?"

test_walkthrough_24_what_about_last_year
  Input (with prior context series_id="LNS14000000"): "What about last year?"
  Expected: inherit concept=unemployment_rate; resolve to 12-month prior period

test_walkthrough_25_show_the_rate_instead
  Input (with prior context series_id="LNS13000000" level): "Show the rate instead."
  Expected: switch to LNS14000000 (unemployment rate); preserve geography and SA

test_walkthrough_27_use_seasonally_adjusted
  Input (with prior series NSA): "Use seasonally adjusted data."
  Expected: switch to SA equivalent of prior series; validate SA exists for that series
```

### Boundary Tests

```
test_single_eligible_candidate_auto_resolves
  Intent fully specified; one candidate; eligible
  Expected: auto-resolve without clarification

test_two_candidates_different_concepts_requires_clarification
  Intent: unresolved concept
  Candidates: two FlagshipEntry with different concept values
  Expected: clarification_required=True

test_two_candidates_same_concept_different_sa_applies_default
  Intent: seasonal_adjustment not specified
  Candidates: SA and NSA series with same concept
  Expected: auto-resolve to survey default SA; disclose default

test_high_word_score_does_not_override_measure_type_conflict
  Candidate with score=5 but wrong measure_type vs. candidate with score=2 and correct type
  Expected: candidate with score=2 selected (after eligibility filter)
```

### Observability Tests (Phase 7)

```
test_log_records_applied_defaults
test_log_records_rejection_reasons
test_log_records_bls_api_called_flag
test_log_records_clarification_decision
test_log_does_not_expose_api_key
test_log_does_not_expose_user_query_pii (if applicable)
```

---

## K. PRODUCT AND SUBJECT-MATTER QUESTIONS

The following decisions cannot be made from code analysis alone and require product and/or
BLS subject-matter expertise.

### K-1: Approved Seasonal-Adjustment Defaults
Proposed defaults in SAFE_DEFAULTS (Section G) are based on common BLS publication practice.
They must be reviewed by someone with BLS subject-matter expertise. For example:
- Is `S` correct as the CE default? (CE headline is SA but NSA is also published)
- Is `U` correct for CU? (BLS publishes both; NSA CUUR0000SA0 is the reference but SA exists)

### K-2: Broad Labor-Market Overview Indicator Set
If a user asks "how is the labor market doing?", should the application return a
multi-indicator overview? If so, what indicators should be included, and in what order?
This is a product design decision. Possible components: nonfarm payrolls change,
unemployment rate, LFPR, EPOP ratio, AHE, JOLTS openings, hires, layoffs and discharges.
The exact set and defaults require product approval before implementation.

### K-3: Preferred Inflation Interpretation
When a user asks "what is inflation?" without further qualification, should the application:
(a) always clarify; (b) default to 12-month percent change of CPI-U all items; or (c) return
the index level and explain how to compute percent change? This requires a product decision.

### K-4: Standard Comparison Period for Rankings
When a user asks "what industry added the most jobs?" without specifying a period, should
the application:
(a) always clarify; (b) default to the latest monthly change; (c) default to 12-month change?
This requires a product decision before implementation.

### K-5: Geographic Default
When a query has no geographic qualifier (e.g. "Show payroll employment"), the application
currently returns a national series. Is this safe to auto-apply without disclosure? Under
what conditions should it disclose "I am showing national data"?

### K-6: Clarification Wording
The clarification question examples in Section I need review by a subject-matter expert to
confirm that the terminology is accessible to general users who may not know BLS program names.

### K-7: Acceptable Latency Trade-Off
Adding a clarification round trip increases latency. Is it acceptable to generate one
clarification before every ambiguous query, or should the system resolve more aggressively
to avoid extra turns? This is a product UX decision.

### K-8: Percent Change vs. Index Level: Which is the Default for CPI?
If a user asks "show CPI", is the index level or the percent change the preferred default?
BLS publishes both; neither is universally preferred. Product decision required.

---

## L. AGENT-MODE HANDOFF CHECKLIST

When implementation is authorized, the agent-mode instruction should cover the following.

### Approved Scope
Implement ambiguity handling improvements in `src/example_server` and `tests/`.
No changes to deployment configuration, external API integrations, or unrelated tools.

### Planned Files (in order)
1. `src/example_server/models.py` — Add `QueryIntent`, `CandidateSeries`
2. `src/example_server/ambiguity.py` (NEW) — Eligibility rules, defaults, clarification
3. `src/example_server/tools/answer_bls_question.py` — Ambiguity gate, context parameter
4. `src/example_server/tools/search_series.py` — Per-survey seasonal defaults, CE industry, JT rate/level
5. `src/example_server/tools/suggest_series.py` — Add measure_type conflict flag
6. `src/example_server/prompts/bls_assistant.py` — Add disambiguation guidance
7. `src/example_server/config.py` — Add SEASONAL_DEFAULTS, feature flags
8. `tests/test_ambiguity_regression.py` (NEW) — Phase 1 regression tests
9. `tests/test_ambiguity.py` (NEW) — Ambiguity module unit tests
10. `tests/test_tools_answer_bls_question.py` — Extend with ambiguity and safety tests
11. `tests/test_query_walkthroughs.py` (NEW) — 28-query walkthrough tests

### Order of Work
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8

Each phase must pass its own tests before the next phase begins.
No implementation without approval of relevant product decisions from Section K.

### Required Tests Per Phase

| Phase | Validation Command |
|-------|--------------------|
| 1 | `pytest tests/test_ambiguity_regression.py -v` |
| 2 | `pytest tests/test_ambiguity.py::test_query_intent_construction -v` |
| 3 | `pytest tests/test_ambiguity.py -v` |
| 4 | `pytest tests/test_tools_answer_bls_question.py -v` |
| 5 | Prompt evaluation (manual or model eval suite) |
| 6 | `pytest tests/test_tools_search_suggest.py tests/test_ambiguity.py -v` |
| 7 | `pytest tests/test_tools_answer_bls_question.py::test_log_records_applied_defaults -v` |
| 8 | `pytest tests/test_query_walkthroughs.py -v` |

### Full Regression After All Phases
```
pytest --tb=short -q
```
No new failures permitted against the pre-implementation baseline.

### Prohibited Changes
- Do not modify `src/example_server/bls_flagship_series.py` for the purpose of adding new
  series IDs (that is a separate sub-task governed by a separate plan).
- Do not modify `Dockerfile`, `manifest.yaml`, `deploy/`, or any CI configuration.
- Do not refactor or reformat files unrelated to ambiguity handling.
- Do not add new dependencies without explicit approval.

### Expected Final Report
After Phase 8:
- All 28 walkthrough tests pass.
- All new ambiguity unit tests pass.
- All existing tests pass with no new failures.
- Product decisions in Section K documented as resolved or deferred with justification.
- Summary of any test that required a product decision to implement.

---

*End of BLS Ambiguity Implementation Plan*
