# GSA DS BLS Agent — `gsa_ds_bls_agent`

## Top-Level Overview

**Goal:** Create a native watsonx Orchestrate agent named `gsa_ds_bls_agent` that is wired to
all 12 tools from the `gsa_ds_bls_toolkit`, includes clear instructions that direct the agent to
call the appropriate tool for each type of user request, import the agent, and verify it is
available in the platform. Generate representative test questions.

**Scope:**
- One native agent: `gsa_ds_bls_agent`
- Tool binding: all tools currently registered under the `gsa_ds_bls_toolkit` toolkit
- Agent spec file: `deploy/ibm/agents/gsa_ds_bls_agent.yaml`
- Import via ADK `import_agent` (YAML file)
- Verification via `list_agents`
- Test questions generated and saved to `deploy/ibm/agents/gsa_ds_bls_agent_test_questions.md`

**Assumptions / pre-conditions:**
- The `gsa_ds_bls_toolkit` is already imported and its 12 tools are available in WxO
  (`list_tools` must be checked at implementation time to get the exact tool names).
- The active WxO environment is `bls-mcp-test1`.
- The LLM to use is `ibm/granite-3-8b-instruct` (standard default for this project; can be
  adjusted at implementation time if `list_models` returns a different preferred model).

**Non-goals:**
- No changes to any tool implementation or the MCP toolkit itself.
- No new tools are created.
- No changes to existing agents (if any).

---

## Known Tools (from codebase — verify names via `list_tools` at implementation time)

The server registers these 10 tools from `src/example_server/tools/`:

| Tool name | Purpose |
|---|---|
| `lookup_area_code` | Find BLS area codes by place name |
| `lookup_industry_code` | Find BLS industry codes by name |
| `build_series_id` | Construct a valid BLS series ID from survey components |
| `decode_series_id` | Decode a series ID into its human-readable segments |
| `validate_series_id` | Validate a BLS series ID locally |
| `search_series` | Full-text search across BLS series catalog |
| `suggest_series` | Suggest curated flagship series for a topic |
| `get_series_metadata` | Retrieve metadata for a series ID |
| `get_series_data` | Fetch live BLS time-series observations |
| `answer_bls_question` | One-call orchestrator: discover → validate → fetch |

The user states there are **12** tools in `gsa_ds_bls_toolkit`. The codebase shows 10 tools plus
`example_search_datasets` (from `example_tool.py`). The 12th tool must be confirmed via
`list_tools` at implementation time. All tools returned by `list_tools` for this toolkit must be
attached to the agent.

---

## Sub-Tasks

---

### Sub-Task 1 — Discover Actual Tool Names from WxO

**Intent:** Query `list_tools` and `list_toolkits` to determine the exact names of all 12 tools
registered under `gsa_ds_bls_toolkit`. The codebase gives us ~10 known names; the platform is the
authoritative source for what's actually imported.

**Expected Outcomes:**
- A confirmed list of exactly 12 tool names from the `gsa_ds_bls_toolkit` toolkit.
- Confirmation that the toolkit name in WxO is `gsa_ds_bls_toolkit` (not `bls_public_data_local`
  or `example_mcp_local`).
- Chosen LLM model name confirmed from `list_models`.

**Todo List:**
1. Call `list_toolkits` — note the exact toolkit name and confirm it is `gsa_ds_bls_toolkit`
2. Call `list_tools` — filter to only tools from `gsa_ds_bls_toolkit`; record all tool names
3. Call `list_models` — confirm which model is available (prefer `ibm/granite-3-8b-instruct`
   or `ibm/granite-3-3-8b-instruct`); record the exact model identifier to use

**Relevant Context:**
- Active environment: `bls-mcp-test1`
- Expected tool names: see table above
- WxO MCP server version: `v2.19.1`

**Status:** [ ] pending

---

### Sub-Task 2 — Write Agent YAML Spec

**Intent:** Create `deploy/ibm/agents/gsa_ds_bls_agent.yaml` — a complete native agent spec
with rich instructions that tell the agent when to call each tool, how to chain them, and how to
respond to users.

**Expected Outcomes:**
- New file: `deploy/ibm/agents/gsa_ds_bls_agent.yaml`
- `name: gsa_ds_bls_agent`
- `kind: native`
- `llm` set to the confirmed model from Sub-Task 1
- `tools` list contains all 12 tool names confirmed in Sub-Task 1
- `instructions` cover:
  - **Primary entry point:** Use `answer_bls_question` for any natural-language question about
    BLS data (unemployment, inflation, employment, wages, job openings, CPI, PPI, etc.).
  - **Discovery:** Use `suggest_series` when the user asks "what data does BLS have about X"
    or wants to explore series options before committing to a specific one.
  - **Search:** Use `search_series` when the user supplies specific keywords or a survey code.
  - **Series ID construction:** Use `build_series_id` when the user knows the survey components
    (prefix, area, industry, data type) and wants to build an ID manually.
  - **Decoding / explaining:** Use `decode_series_id` when the user has a series ID and wants
    to understand what it means.
  - **Validation:** Use `validate_series_id` when the user asks whether a series ID is valid
    or before passing an ID to `get_series_data`.
  - **Code lookups:** Use `lookup_area_code` for geography questions; `lookup_industry_code`
    for NAICS/industry questions.
  - **Metadata:** Use `get_series_metadata` when the user wants to know survey details,
    footnotes, or catalog information about a series without fetching observations.
  - **Raw data:** Use `get_series_data` when the user explicitly wants observation data for a
    known series ID, or when batching multiple series.
  - **Output formatting:** Present data in a clear, concise format; cite the series ID and
    source in every data answer; note when values are preliminary (P) or revised (R).
  - **Error handling:** If `answer_bls_question` returns an error, try `suggest_series` to find
    alternatives and explain the situation to the user.

**Spec structure (YAML fields):**
```
spec_version: v1
kind: native
name: gsa_ds_bls_agent
description: ...
llm: <model from Sub-Task 1>
style: default
instructions: |
  <full instruction block>
tools:
  - <tool_1>
  - ...   # all 12 tools
config:
  hidden: false
  enable_cot: false
```

**Relevant Context:**
- Tool descriptions: `src/example_server/tools/` (one file per tool)
- `answer_bls_question` is the orchestrator tool — prefer it for end-to-end questions
- Agent YAML location: `deploy/ibm/agents/` (create directory if needed)

**Status:** [ ] pending

---

### Sub-Task 3 — Import Agent into WxO and Verify

**Intent:** Import the agent spec into the active WxO environment and confirm it appears in
`list_agents` with all tools wired correctly.

**Expected Outcomes:**
- `import_agent` succeeds with no errors
- `list_agents` shows `gsa_ds_bls_agent` under native agents
- (Optional) `export_agent` to confirm tool bindings are stored correctly

**Todo List:**
1. Call `import_agent` with `path: deploy/ibm/agents/gsa_ds_bls_agent.yaml`
2. Call `list_agents` (kind: native) — confirm `gsa_ds_bls_agent` appears
3. If import fails due to existing agent, call `remove_agent` first, then retry import

**Relevant Context:**
- `import_agent` takes `path` and `app_id` (None — no auth connection needed)
- Error: if a tool name doesn't exist in WxO the import will fail → fix tool list in YAML

**Status:** [ ] pending

---

### Sub-Task 4 — Generate Test Questions

**Intent:** Produce a curated set of test questions that cover every tool and validate that the
agent's routing instructions are exercised correctly. Save as a Markdown file.

**Expected Outcomes:**
- New file: `deploy/ibm/agents/gsa_ds_bls_agent_test_questions.md`
- Minimum 15 questions covering:
  - Natural-language data queries (→ `answer_bls_question`)
  - Series discovery queries (→ `suggest_series`)
  - Keyword search (→ `search_series`)
  - Series ID construction requests (→ `build_series_id`)
  - Series ID decoding (→ `decode_series_id`)
  - Validation requests (→ `validate_series_id`)
  - Geographic code lookup (→ `lookup_area_code`)
  - Industry code lookup (→ `lookup_industry_code`)
  - Metadata requests (→ `get_series_metadata`)
  - Batch data retrieval (→ `get_series_data`)
- Each question annotated with the expected primary tool and expected output shape

**Relevant Context:**
- Tool capabilities: `src/example_server/tools/` docstrings
- Flagship series: `src/example_server/bls_flagship_series.py` (CPI, unemployment, payrolls, etc.)

**Status:** [ ] pending

---

## Implementation Order

```
1 — Discover tool names from WxO
  └─ 2 — Write agent YAML spec (uses confirmed tool names + model)
       └─ 3 — Import agent + verify
            └─ 4 — Generate test questions
```

---

## Files to Create or Modify

| File | Action | Sub-Task |
|---|---|---|
| `deploy/ibm/agents/gsa_ds_bls_agent.yaml` | Create — agent spec | 2 |
| `deploy/ibm/agents/gsa_ds_bls_agent_test_questions.md` | Create — test questions | 4 |

---

## Notes

- The WxO MCP list calls (`list_toolkits`, `list_tools`, `list_agents`) are experiencing
  timeouts in the current session (likely transient platform latency). Sub-Task 1 must be
  retried at implementation time.
- If the toolkit is named differently than `gsa_ds_bls_toolkit` in WxO, the tool names will
  still be available globally — `list_tools` will show all tools regardless of toolkit grouping.
- The `example_search_datasets` tool (from `example_tool.py`) may or may not be in the
  imported toolkit; confirm via `list_tools`.
