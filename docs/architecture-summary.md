# BLS MCP Server — Architecture Summary Report

> Derived from full source-code inspection of the GSA MCP Hackathon repository.
> See [`docs/architecture.md`](architecture.md) for all UML diagrams.

---

## Architectural Style

**Single-process, layered MCP server.**

The codebase follows a strict thin-entrypoint / domain-layer / tool-presentation
separation. The FastMCP framework handles protocol serialisation; domain logic is
entirely in pure Python modules with no async background tasks, no database, and no
message queue. Transport is plug-in via three mutually exclusive modes:
`stdio` (local dev), `streamable-http` (manual HTTP), or `http` (platform-injected
port for cloud deploys).

---

## Main Components

| Component | Role | Makes Network Calls? |
|---|---|---|
| `app.py` | Thin wiring layer. Creates `FastMCP` instance, calls all `register_*` functions, selects transport. | No |
| `ambiguity.py` | Central policy brain. Intent parsing, candidate eligibility, clarification gate, safe-default application. Called only by `answer_bls_question`. | No |
| `bls_flagship_series.py` | Curated canonical series catalog (~200 entries, 12 surveys). Keyword-intersection search engine powering discovery. | No |
| `bls_series_schema.py` | Structural schema for 13 BLS survey ID formats. Provides `decode_id`, `build_id`, `get_schema`. Deferred catalog import avoids circular dependency. | No |
| `catalog.py` | Module singleton. Loads 100+ local reference files at import time. O(n) substring search over code/name pairs; never reads files at query time. | No |
| `utils.py` | All HTTP I/O. `fetch_bls()` auto-selects v1/v2, injects registration key, enforces 5 MB limit, sanitises errors. `fetch_json()` has path-traversal guard. | **YES** (only file) |
| `tools/` (10 tools) | Thin MCP presentation layer. Each tool maps to one file; wires inputs to domain functions and returns structured dicts. | Only `answer_bls_question` and `get_series_data` (via `fetch_bls`) |
| `eval/` pipeline | Offline evaluation harness. Two agent variants (chat-completions vs. SSE-stream) targeting the deployed Orchestrate agent. Two LLM-as-judge evaluators via watsonx.ai / litellm. | Yes (Orchestrate + BLS + watsonx.ai) |

---

## Key Runtime Dependencies

| Package | Version | Role |
|---|---|---|
| `fastmcp` | ≥ 2.0.0 | MCP protocol server, tool/resource/prompt registration, transports |
| `httpx` | ≥ 0.27.0 | Async HTTP client for BLS API calls |
| `pydantic` | ≥ 2.0.0 | Input validation and data models |
| `pydantic-settings` | ≥ 2.0.0 | Settings from `.env` / environment variables |
| `pandas` | ≥ 3.1.1 | **Declared but unused in server package** — only used in eval notebooks and sandbox (see tech debt below) |
| `arize-phoenix` | ≥ 18.0.0 | Eval harness: dataset and experiment tracking (dev group only) |
| `litellm` | ≥ 1.0.0 | LLM-as-judge calls to watsonx.ai (dev group only) |

---

## Critical Execution Paths

### 1. `answer_bls_question` (8 steps)

The primary orchestrator. The only network call is step 7.

```
parse_intent (local)
  → search_flagship (local)
  → filter_candidates (local)
  → detect_unresolved_dims (local)
  → apply_safe_defaults (local)
  → _validate_locally (local)
  → fetch_bls (NETWORK — POST api.bls.gov)
  → _build_summary / return structured response
```

Steps 1–6 and step 8 are synchronous and involve no I/O. The ambiguity gate
at step 4 short-circuits the pipeline and returns a clarification question
to the agent without ever touching the BLS API.

### 2. `get_series_data` (4 steps)

Direct retrieval path, skips the ambiguity layer entirely.

```
BLSSeriesRequest Pydantic validation
  → validate_series_request (v1/v2 limits)
  → fetch_bls (NETWORK)
  → enrich with decode_id + get_flagship → return
```

### 3. Local catalog search path

All lookup and search tools (`lookup_area_code`, `lookup_industry_code`,
`search_series`, `suggest_series`, `decode_series_id`, `validate_series_id`,
`get_series_metadata`, `build_series_id`) are entirely local — no network I/O.

```
catalog.search() → O(n) substring scan of pre-loaded dict
```

---

## Technical Debt Observations

### 1. `pandas` declared as a runtime dependency but unused in the server

`pandas ≥ 3.1.1` appears in the `[project]` dependencies section of
`pyproject.toml`, but is never imported anywhere in `src/example_server/`.
It is only used in eval notebooks (`bls_api_tester_aw.ipynb`) and the
`sandbox/` directory. This adds approximately 30 MB to every Docker image
unnecessarily.

**Recommendation:** Move `pandas` to the `[dependency-groups]` dev section,
or to a separate `notebooks` extra.

### 2. `get_series_metadata` missing `None` guard on `total_length`

In [`src/example_server/tools/get_series_metadata.py`](../src/example_server/tools/get_series_metadata.py)
at line 71:

```python
if len(sid) != schema.total_length:
```

This raises `TypeError: '<' not supported between instances of 'int' and 'NoneType'`
when `schema.total_length is None` — which is the case for variable-length survey
prefixes: `CU`, `JT`, `CW`, `WP`, `EI`, `PC`.

[`validate_series_id.py`](../src/example_server/tools/validate_series_id.py) correctly
guards this:

```python
if schema.total_length is not None and len(sid) != schema.total_length:
```

**Recommendation:** Apply the same guard in `get_series_metadata.py`.

### 3. Circular import avoidance pattern creates invisible coupling

`bls_series_schema.py` imports `catalog` inside the body of `decode_id()` with a
`# noqa: PLC0415` suppression comment. `utils.py` imports `BLSSeriesRequest` only
under `TYPE_CHECKING`. Both workarounds are correct, but they document an
architectural coupling that could be resolved by making `catalog` a parameter
(dependency injection) rather than a module-level import.

### 4. `search_series` tool complexity without test coverage

`tools/search_series.py` contains 12 survey-specific `_search_*` helper functions
(~550 lines total) but has no dedicated unit test file in `tests/`. It is covered
only indirectly by integration tests.

**Recommendation:** Add `tests/test_tools_search_series.py` with unit tests for
each per-survey search helper and the `_detect_survey()` routing function.

### 5. Eval environment variables undiscoverable from one place

Required env vars for the eval pipeline are scattered across five files:
`agent.py`, `agent_v2.py`, `run_experiment.py`, `run_multi_eval.py`, and
`judges/correctness_judge.py`. There is no single reference document or
`env.example` file for the eval stack.

**Recommendation:** Create `eval/phoenix/.env.example` listing all required
variables (`ORCHESTRATE_BASE_URL`, `ORCHESTRATE_AGENT_ID`, `IBM_CLOUD_API_KEY`,
`PHOENIX_ENDPOINT`, `PHOENIX_PROJECT_NAME`, `JUDGE_MODEL`, and any
`WATSONX_*` vars required by litellm).

---

## Recommended Documentation Improvements

1. **Add an ADR** explaining why the flagship series table is a static Python file
   rather than an external catalog or database (maintainability vs. runtime
   dependency trade-off).

2. **Document `_CONCEPT_PHRASES`** in `ambiguity.py` — the 50+ phrase-to-concept
   mapping table is the core concept-extraction heuristic but has no inline
   explanation of its coverage gaps or the process for adding new concepts.

3. **Add a survey coverage matrix** for `search_series` per-survey search functions
   vs. which dimensions each survey supports, so it is clear which surveys have
   partial search support.

4. **Promote the `bls_top_picks` refresh procedure** from the module docstring in
   `bls_top_picks.py` to the main `README.md` or `CONTRIBUTING.md`.

5. **Create `eval/phoenix/.env.example`** as described in Tech Debt §5 above.

---

*Full diagram set: [`docs/architecture.md`](architecture.md)*
