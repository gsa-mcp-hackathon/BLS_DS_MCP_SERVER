# BLS MCP Server Integration Plan

## Top-Level Overview

**Goal:** Integrate independently-developed components — the BLS API integration
(`utils.py`, `config.py`, `models.py`), the MCP tools for series ID construction
and data retrieval (`tools/`), and the MCP resources (`resources/`) — into one
functioning FastMCP server using STDIO transport, ready to connect to IBM watsonx
Orchestrate.

**Scope:**
- Confirm `app.py` registration wiring is complete and correct
- Identify any broken imports, mismatched function references, or missing
  connections between `utils.py` and tool consumers
- Use the FastMCP `resource_as_tool` server-level transform to expose resources
  to agents that don't natively browse the MCP resources endpoint
- Make only the minimal changes needed; no refactoring, no decorator changes,
  no new tools

**Non-goals:** No new tools, no architectural refactor, no changes to the BLS API
logic in `utils.py`, no changes to `@mcp.resource` decorators, no changes to the
local-cache catalog files.

**Transport:** STDIO throughout (default for local clients and for the watsonx
Orchestrate local MCP toolkit path).

**FastMCP version installed:** 4.0.11

---

## Findings from Code Review

### ✅ Registration is Complete and Correct

`app.py` (server name: `"BLS Public Data Server"`, updated in latest git pull)
correctly calls all four aggregators:

```
register_tools(mcp)     → tools/__init__.py    → 10 tool files, all imported and registered
register_prompts(mcp)   → prompts/__init__.py  → 2 prompt files, both registered
register_resources(mcp) → resources/__init__.py → 2 resource files, both registered
register_routes(mcp)    → routes.py            → /health, /version
```

There are **no missing imports, no incorrect function references, and no
registration conflicts** in the current architecture.

### ✅ BLS Utilities Are Properly Connected to Tools

Every tool correctly references the relevant helpers from `utils.py`, `catalog.py`,
`bls_series_schema.py`, and `bls_flagship_series.py`:

| Tool | Utilities / Helpers Used |
|---|---|
| `get_series_data` | `fetch_bls`, `unwrap_bls_response`, `validate_series_request` |
| `search_series` | `catalog.search`, `paginate`, `build_id`, `decode_id` |
| `lookup_area_code` / `lookup_industry_code` | `catalog.search` |
| `build_series_id` / `decode_series_id` / `validate_series_id` | `bls_series_schema.*`, `catalog.*` |
| `get_series_metadata` | `decode_id`, `get_schema`, `get_flagship`, `catalog.get` |
| `suggest_series` | `search_flagship`, `decode_id` |
| `example_tool` | `fetch_json`, `paginate` (stub — not live BLS) |

### ✅ Server Name and Description Already Updated

The latest git pull already updated `app.py` to `name="BLS Public Data Server"`
with accurate BLS instructions. No further changes needed here.

### ⚠️ One Gap in `app.py` Instructions

`app.py` line 38–40 reads:
`"Start by reading bls://surveys/overview ..."` — this URI works for
resource-aware clients (Claude Desktop, Claude Code) but once the
`resource_as_tool` transform is applied, the same content becomes callable as a
tool. The instructions should also mention using the tool name so agents that don't
browse resources know how to access it. This is a one-line text update inside the
`instructions=` argument.

### ⚠️ Resources Need to Be Accessible as Tools for watsonx Orchestrate

The two BLS resources currently registered are:

| Resource URI | Content |
|---|---|
| `bls://surveys/overview` | Full index of all 5 surveys — dimensions, update frequency, tool guidance |
| `bls://surveys/{survey_code}` | Parameterized detail page for one survey (SM/CE/LA/JT/CU) |

IBM watsonx Orchestrate's local MCP toolkit (stdio) advertises **"Full MCP
protocol support"** including resources, but in practice the Orchestrate LLM
agent invokes **tools** — not `resources/read`. The survey reference content is
most useful when the LLM can call it on demand.

**The fix:** Use the FastMCP built-in server transform
`resource_as_tool` (documented at
https://gofastmcp.com/servers/transforms/resources-as-tools).
This is applied in `app.py` **after** `register_resources(mcp)` using:

```python
from fastmcp.server.middleware import ResourceAsToolMiddleware
# or, per FastMCP v4 docs, using the transform API:
mcp = mcp.with_resources_as_tools()
# OR as a server-level config
mcp = FastMCP(..., resource_as_tool=True)
```

The exact API depends on the FastMCP v4 release. The implementation sub-task
below calls for verifying the correct call against the installed 4.0.11 source
before applying it. The `@mcp.resource` decorators in `bls_surveys.py` and
`example.py` are **not touched** — the transform handles exposure at the server
level.

### Optional: Remove Example Stubs from Registration

`tools/example_tool.py` (mock data stub) and `resources/example.py` (template
placeholder) add noise to the tool list. They cause no functional errors but do
increase the number of tools the LLM sees. Removing them from registration is
optional but recommended.

---

## Sub-Tasks

---

### Sub-Task 1 — Apply `resource_as_tool` Transform in `app.py`

**Status:** `[ ] pending`

**Intent:**
Use the FastMCP server-level `resource_as_tool` transform to expose the registered
BLS resources (`bls://surveys/overview` and `bls://surveys/{survey_code}`) as
callable tools — without modifying any `@mcp.resource` decorator or moving code
between files. The resources continue to work as resources for clients that support
them; they are additionally exposed as tools for clients (like the Orchestrate
agent) that only invoke tools.

**Expected Outcomes:**
- The BLS resources are accessible both as MCP resources **and** as tools named
  after their URIs (as FastMCP names them via the transform)
- No changes to `resources/bls_surveys.py` or `resources/example.py`
- No changes to `resources/__init__.py`
- `app.py` `instructions=` text updated to also mention calling the tool name for
  agents that don't browse resources (so the LLM has both the URI and tool name)
- All existing tests pass; new smoke-test confirms the tool is visible

**Todo List:**
1. Check the FastMCP 4.0.11 source to confirm the exact `resource_as_tool`
   transform API (e.g. `mcp.resource_as_tool(...)`, `FastMCP(..., resource_as_tool=True)`,
   or a server middleware call — the docs at
   https://gofastmcp.com/servers/transforms/resources-as-tools are the canonical
   reference)
2. Open `src/example_server/app.py`
3. Apply the transform **after** `register_resources(mcp)` using the confirmed API
4. Update the `instructions=` string to additionally mention calling the survey
   overview tool by name (e.g. `"call get_bls_surveys_overview or read
   bls://surveys/overview"`) so both resource-aware and tool-only clients know
   how to access it
5. Run `uv run pytest` to confirm all existing tests pass
6. Add a quick smoke-test: confirm the resource is listed as a tool in the server's
   tool list (e.g. via `uv run python -c "from example_server.app import mcp; ..."`)

**Relevant Context:**
- `src/example_server/app.py` — `register_resources(mcp)` on line 47, `instructions=` on lines 33–41
- `src/example_server/resources/bls_surveys.py` — unchanged; `@mcp.resource` decorators stay
- FastMCP v4 transform docs: https://gofastmcp.com/servers/transforms/resources-as-tools
- Installed version: fastmcp==4.0.11

---

### Sub-Task 2 — Remove Example Stubs from Registration

**Status:** `[ ] pending`

**Intent:**
`tools/example_tool.py` (a stub returning mock data) and `resources/example.py`
(static template placeholder strings) are not part of the BLS functionality.
Deregistering them reduces tool list noise for the Orchestrate agent without
removing the files (they stay as reference).

**Expected Outcomes:**
- `example_search_datasets` no longer appears in the tool list
- `example://info/server` and `example://docs/{topic}` no longer appear in resources
- No BLS tools, resources, or prompts are affected
- Tests covering example stubs are removed or skipped
- All BLS tests continue to pass

**Todo List:**
1. Open `src/example_server/tools/__init__.py` — remove the `example_tool` import
   and its `example_tool.register(mcp)` call
2. Open `src/example_server/resources/__init__.py` — remove the `example` import
   and its `example.register(mcp)` call
3. Check `tests/` for any test covering `example_tool` or the `example.py`
   resource and remove or skip those tests
4. Run `uv run pytest` to confirm no regressions

**Relevant Context:**
- `src/example_server/tools/__init__.py` — `example_tool` import line ~12, register call line ~27
- `src/example_server/resources/__init__.py` — `example` import line ~12, register call line ~17
- `src/example_server/tools/example_tool.py` — safe to leave on disk, just deregister
- `src/example_server/resources/example.py` — safe to leave on disk, just deregister

---

## Architecture After Changes

```
app.py  ("BLS Public Data Server")
 ├── register_tools()
 │    ├── lookup_area_code
 │    ├── lookup_industry_code
 │    ├── build_series_id
 │    ├── decode_series_id
 │    ├── validate_series_id
 │    ├── search_series
 │    ├── suggest_series
 │    ├── get_series_metadata
 │    └── get_series_data          ← only tool making live API calls
 ├── register_prompts()
 │    ├── bls_assistant
 │    └── (example.py removed in Sub-Task 2)
 ├── register_resources()
 │    └── bls_surveys              ← @mcp.resource decorators unchanged
 │         ├── bls://surveys/overview
 │         └── bls://surveys/{survey_code}
 ├── register_routes()
 │    └── /health, /version
 └── resource_as_tool transform    ← NEW: applied after register_resources (Sub-Task 1)
      ├── bls://surveys/overview   → also callable as a tool
      └── bls://surveys/{survey_code} → also callable as a tool

deploy/ibm/local-mcp-toolkit/
 └── server.py  → imports app.mcp, runs mcp.run(transport="stdio")  (unchanged)
```

**Execution order:** Sub-Tasks 1 and 2 are independent and can be done in either order.
