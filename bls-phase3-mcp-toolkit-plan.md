# BLS Phase 3 — Local MCP Toolkit for watsonx Orchestrate

## Top-Level Overview

**Goal:** Package the 9 existing BLS tools (all fully implemented in `src/example_server/`) as a
self-contained local MCP toolkit using **STDIO transport**, test it thoroughly (initialization,
tool discovery, every tool call) using the MCP protocol locally, import it into the active
watsonx Orchestrate environment via the ADK, verify all 9+ tools appear, and ensure all code
passes `ruff` lint.

**Approach:**

1. **Ruff fix pass** — run `ruff check` and `ruff format` and resolve any issues.
2. **Local functional test script** — write `deploy/ibm/local-mcp-toolkit/test_local.py`, a
   Python script that speaks raw MCP-over-stdio (via FastMCP's in-process `stdio` client) to
   verify: initialization handshake, `tools/list` discovers all expected tools, and every tool
   is callable with representative inputs and returns a valid response.
3. **Toolkit import** — use the ADK MCP tool (`add_toolkit`) to upload the staged package_root
   (the existing `deploy/ibm/local-mcp-toolkit/` scaffold) and import it into the active WxO
   environment with `tools: ["*"]`.
4. **Verification** — call `list_toolkits` and confirm the toolkit is present, then
   `list_tools` and confirm all expected tool names appear.

**What already exists and must NOT change:**
- All 9 tool implementations: `lookup_area_code`, `lookup_industry_code`, `build_series_id`,
  `decode_series_id`, `validate_series_id`, `search_series`, `suggest_series`,
  `get_series_metadata`, `get_series_data` — in `src/example_server/tools/`
- `deploy/ibm/local-mcp-toolkit/server.py` — stdio entrypoint (`mcp.run(transport="stdio")`)
- `deploy/ibm/local-mcp-toolkit/requirements.txt` — runtime deps
- `deploy/ibm/local-mcp-toolkit/toolkit.yaml` — import config template
- The entire `src/example_server/` package (catalog, schema, flagship series, config, utils, models)
- All existing test files in `tests/`

**Non-goals:**
- No changes to any existing tool implementation or test file.
- No HTTP server, no Code Engine, no container.
- No new tool functionality.

---

## Existing Tool Registry (all 9 must appear in WxO after import)

| Tool name | File |
|---|---|
| `example_search_datasets` | `tools/example_tool.py` |
| `lookup_area_code` | `tools/lookup_area_code.py` |
| `lookup_industry_code` | `tools/lookup_industry_code.py` |
| `build_series_id` | `tools/build_series_id.py` |
| `decode_series_id` | `tools/decode_series_id.py` |
| `validate_series_id` | `tools/validate_series_id.py` |
| `search_series` | `tools/search_series.py` |
| `suggest_series` | `tools/suggest_series.py` |
| `get_series_metadata` | `tools/get_series_metadata.py` |
| `get_series_data` | `tools/get_series_data.py` |

---

## Sub-Tasks

---

### Sub-Task 1 — Ruff Lint and Format Pass

**Intent:** Guarantee that every Python file in the project passes `ruff check` and
`ruff format --check` with no errors or warnings before any new files are written.
New files written in later sub-tasks must also pass.

**Expected Outcomes:**
- `uv run ruff check src/ tests/ deploy/` exits 0 with no violations
- `uv run ruff format --check src/ tests/ deploy/` exits 0 with no issues
- Any existing violations are fixed in-place (imports reordered, unused imports removed, etc.)

**Todo List:**
1. Run `uv run ruff check src/ tests/ deploy/ --output-format=concise` and capture output
2. Apply `uv run ruff check src/ tests/ deploy/ --fix` to auto-fix safe violations
3. Apply `uv run ruff format src/ tests/ deploy/` to enforce formatting
4. Manually fix any remaining violations flagged as "unfixable" (rare in this codebase)
5. Re-run both commands to confirm clean exit

**Relevant Context:**
- `pyproject.toml` `[tool.ruff.lint]`: `select = ["E", "F", "I"]` (errors, pyflakes, isort)
- `[tool.ruff]`: `line-length = 88`, `target-version = "py311"`, `exclude = [".venv", ".agents"]`
- New files written in Sub-Tasks 2–3 must also pass on first write

**Status:** [ ] pending

---

### Sub-Task 2 — Local Toolkit Test Script

**Intent:** Create `deploy/ibm/local-mcp-toolkit/test_local.py`, a standalone test script that
runs `server.py` as a subprocess (STDIO transport), performs the MCP initialization handshake,
discovers all tools, and calls each tool with representative inputs — proving the full
server→protocol→tool pipeline works before touching WxO.

**Expected Outcomes:**
- New file: `deploy/ibm/local-mcp-toolkit/test_local.py`
- Script can be run from the repo root: `uv run python deploy/ibm/local-mcp-toolkit/test_local.py`
- Uses FastMCP's `Client` (or its MCP in-process client) to create a stdio connection to
  `server.py` — no manual JSON framing needed
- Checks printed with ✓/✗ markers and final PASS/FAIL summary
- Validates all of the following:
  - **Initialization**: server responds with name `"BLS Public Data Server"` and instructions
  - **Tool discovery**: `tools/list` returns all 10 expected tool names
  - **`lookup_area_code`**: query `"Chicago"` returns ≥ 1 result with `code` and `name` fields
  - **`lookup_industry_code`**: query `"construction"` returns ≥ 1 result
  - **`decode_series_id`**: `"CUUR0000SA0"` returns `prefix == "CU"` and `"segments"` list
  - **`validate_series_id`**: `"CUUR0000SA0"` returns `valid == true`
  - **`build_series_id`**: known valid SM kwargs builds a series_id string
  - **`search_series`**: query `"Chicago employment"` with survey `"SM"` returns results or
    empty results with `suggestion` key (both valid outcomes)
  - **`suggest_series`**: topic `"consumer price"` returns ≥ 1 suggestion with
    `series_id`, `survey_name`, `description`, `rationale`
  - **`get_series_metadata`**: `"CUUR0000SA0"` returns `valid == true` and a `notes` field
  - **`get_series_data`**: `"CUUR0000SA0"` with year range `2024–2024` returns either a
    `series` list (success) or an `error` dict (network failure) — both are acceptable;
    the tool must not raise an exception

**Implementation notes:**
- The FastMCP `Client` constructor can be called with `ClientStdioTransport` pointing at
  `python server.py` (run from repo root with `PYTHONPATH=src`). Check FastMCP docs/source
  for the exact API (`fastmcp.client` module).
- Alternative: use `fastmcp.client.StdioTransport` or equivalent; if not available, use
  `mcp.client.stdio` from the base `mcp` package (which FastMCP depends on).
- The script uses `asyncio.run()` and structured `async with` context managers for the client.
- Each check prints its result regardless of pass/fail so all failures are visible at once.
- Exit code 0 on all pass, non-zero on any fail.
- File must pass `ruff check` and `ruff format --check`.

**Relevant Context:**
- `deploy/ibm/local-mcp-toolkit/server.py`: the target process (`python server.py`)
- `deploy/ibm/local-mcp-toolkit/requirements.txt`: lists `fastmcp>=2.0.0` which includes the client
- `src/example_server/app.py`: confirms server name is `"BLS Public Data Server"`
- `src/example_server/tools/__init__.py`: lists all 10 registered tool names
- FastMCP client transport: `from fastmcp import Client` or check `fastmcp.client`

**Status:** [ ] pending

---

### Sub-Task 3 — Toolkit YAML Update

**Intent:** Update `deploy/ibm/local-mcp-toolkit/toolkit.yaml` to use the BLS-specific toolkit
name and description that reflect the actual server, rather than the placeholder "Example MCP
server" defaults from the starter template.

**Expected Outcomes:**
- `toolkit.yaml` updated:
  - `name`: `bls_public_data_local`
  - `description`: `"BLS Public Data MCP server (local stdio). Provides 10 tools for BLS series lookup, construction, decoding, validation, search, and live data retrieval."`
- `toolkit.yaml` `command`, `env`, `tools` fields unchanged (`python server.py`, `[]`, `["*"]`)
- `deploy/ibm/local-mcp-toolkit/.env.example` `TOOLKIT_NAME` updated to `bls_public_data_local`

**Todo List:**
1. Edit `deploy/ibm/local-mcp-toolkit/toolkit.yaml`: update `name` and `description`
2. Edit `deploy/ibm/local-mcp-toolkit/.env.example`: update `TOOLKIT_NAME`

**Relevant Context:**
- Current `toolkit.yaml` `name`: `example_mcp_local` (placeholder from template)
- Current `.env.example` `TOOLKIT_NAME`: `example_mcp_local`

**Status:** [ ] pending

---

### Sub-Task 4 — Import Toolkit into watsonx Orchestrate

**Intent:** Import the local MCP toolkit into the active watsonx Orchestrate environment using
the ADK `add_toolkit` MCP tool, providing the flattened `package_root` staging directory,
the startup command, and all tool metadata.

**Expected Outcomes:**
- The toolkit `bls_public_data_local` appears in `list_toolkits` with status indicating it
  was successfully imported
- No import error

**Implementation notes:**
- The staging directory is `deploy/ibm/local-mcp-toolkit/_stage/` which needs to be built
  first (copy `src/example_server` → `_stage/example_server`, copy `server.py`,
  `requirements.txt` to `_stage/`)
- The `add_toolkit` call uses `kind: "mcp"`, `package_root: <path to _stage>`,
  `command: "python server.py"`, `tools: ["*"]`
- If a toolkit with that name already exists, remove it first then re-add
- The staging and import must be done as part of the agent's execution (not via the shell script,
  since Bob doesn't have shell execution in plan mode)

**Todo List:**
1. Check `list_toolkits` to see if `bls_public_data_local` already exists; if so, remove it
2. Build the staging directory: copy `src/example_server/` to `deploy/ibm/local-mcp-toolkit/_stage/example_server/`; copy `server.py` and `requirements.txt` to `_stage/`; remove `__pycache__` dirs
3. Call `add_toolkit` with `kind: mcp`, `name: bls_public_data_local`,
   `description: ...`, `package_root: deploy/ibm/local-mcp-toolkit/_stage`,
   `command: "python server.py"`, `tools: ["*"]`
4. Call `list_toolkits` to confirm the toolkit appears

**Relevant Context:**
- `deploy/ibm/local-mcp-toolkit/toolkit.yaml`: template for import config
- `deploy/ibm/local-mcp-toolkit/register-toolkit.sh`: the shell script that does the staging;
  its staging logic must be replicated in the agent step

**Status:** [ ] pending

---

### Sub-Task 5 — Verify Toolkit and All Tools in WxO

**Intent:** Confirm that the imported toolkit exposes all 10 expected tool names in the
watsonx Orchestrate platform.

**Expected Outcomes:**
- `list_toolkits` shows `bls_public_data_local`
- `list_tools` shows all 10 tool names from the toolkit:
  `example_search_datasets`, `lookup_area_code`, `lookup_industry_code`, `build_series_id`,
  `decode_series_id`, `validate_series_id`, `search_series`, `suggest_series`,
  `get_series_metadata`, `get_series_data`
- All 10 tool names present — report any that are missing

**Todo List:**
1. Call `list_toolkits` and confirm `bls_public_data_local` is present
2. Call `list_tools` and extract all tool names from the toolkit
3. Check all 10 expected names are present; report discrepancies

**Relevant Context:**
- `src/example_server/tools/__init__.py`: canonical list of registered tools

**Status:** [ ] pending

---

## Implementation Order

```
1 (ruff)
  └─ 2 (local test script)
       └─ 3 (toolkit.yaml update)
            └─ 4 (import to WxO)
                 └─ 5 (verify)
```

---

## Files to Create or Modify

| File | Action | Sub-Task |
|---|---|---|
| `deploy/ibm/local-mcp-toolkit/test_local.py` | Create — local MCP stdio test script | 2 |
| `deploy/ibm/local-mcp-toolkit/toolkit.yaml` | Modify — name + description | 3 |
| `deploy/ibm/local-mcp-toolkit/.env.example` | Modify — TOOLKIT_NAME | 3 |
| Any `src/`, `tests/`, `deploy/` files with ruff violations | Modify — lint/format fixes only | 1 |

---

## Notes on FastMCP Client API

FastMCP `>=2.0.0` ships a Python client. The typical pattern:

```python
from fastmcp import Client

async with Client("path/to/server.py") as client:
    tools = await client.list_tools()
    result = await client.call_tool("lookup_area_code", {"query": "Chicago"})
```

Or using a subprocess transport explicitly:

```python
from fastmcp.client.transports import StdioTransport

transport = StdioTransport(command=["python", "server.py"], env={"PYTHONPATH": "src"})
async with Client(transport) as client:
    ...
```

The exact API depends on the installed version — the test script should import and introspect
what's available, falling back to the `mcp` base package's `stdio_client` if needed.
