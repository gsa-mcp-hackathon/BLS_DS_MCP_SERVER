# BLS Evaluation Harness Plan

## Overview

Build a Phoenix-based evaluation harness that measures how well the
`gsa_ds_bls_agent` deployed in IBM watsonx Orchestrate answers real
BLS data questions using only the 12 registered MCP tools.

Because the agent runs inside Orchestrate (not locally), the harness
calls the Orchestrate HTTP endpoint rather than launching the MCP server
over stdio. Phoenix records input/output pairs and judge scores for every
question; full tool-call traces are not available, but correctness and
scope scoring are sufficient to identify broken tool schemas and prompt
failures.

**Scope:**
- Generate a 30-question dataset covering all 10 tools and 12 surveys
- Build the full eval/phoenix/ directory (agent, judges, CLIs, prompts)
- Wire Phoenix instrumentation at the experiment level
- Add Phoenix eval dependencies to pyproject.toml dev group
- Document the harness in eval/phoenix/README.md

**Non-goals:**
- Per-tool-call trace capture (not available from Orchestrate)
- Automated CI execution (manual trigger only for now)
- Databricks eval path (already exists in eval/databricks/)

**Key files produced:**
```
eval/phoenix/
├── agent.py
├── create_dataset.py
├── run_experiment.py
├── datasets.yaml
├── README.md
├── judges/
│   ├── __init__.py
│   ├── correctness_judge.py
│   └── relevance_judge.py
├── prompts/
│   ├── system_prompt_v1.txt
│   └── system_prompt_v2.txt
└── datasets/
    └── bls-eval-0/
        └── examples/
            └── bls-eval-0.csv
pyproject.toml          (dev group extended)
.env.example            (eval vars appended)
```

---

## Sub-Task 1 — Add Phoenix dependencies to pyproject.toml

**Status:** [x] done

### Intent
Install the Phoenix evaluation stack into the existing `dev` dependency
group so `uv sync --group dev` gives every teammate a working harness
without touching the production server dependencies.

### Expected Outcomes
- `pyproject.toml` dev group contains all Phoenix, LangChain, and OTLP
  packages at pinned minimum versions
- `uv sync --group dev` succeeds with no conflicts
- Existing server deps (`fastmcp`, `httpx`, `pydantic`, `pandas`) are
  unchanged

### Todo List
1. Open `pyproject.toml` and locate the `[dependency-groups] dev` block
2. Append the following packages (do NOT duplicate `pandas`, which is
   already in core deps):
   - `arize-phoenix>=8.0.0`
   - `arize-phoenix-client>=2.13.0`
   - `arize-phoenix-evals>=3.1.1`
   - `langchain>=0.3.0`
   - `langchain-openai>=0.3.0`
   - `openinference-instrumentation-langchain>=0.1.67`
   - `opentelemetry-exporter-otlp>=1.43.0`
   - `opentelemetry-sdk>=1.43.0`
   - `pyyaml>=6.0.0`
   - `httpx>=0.27.0` (already in core, no duplicate needed)
3. Run `uv sync --group dev` and confirm it resolves without error

### Relevant Context
- `pyproject.toml` lines 26–36: current dev group has 5 entries
  (ipykernel, nbconvert, pytest, pytest-asyncio, ruff)
- `pandas>=3.1.1` is already in core `[project] dependencies` — do not
  add it again to the dev group

---

## Sub-Task 2 — Append eval credentials to .env.example

**Status:** [x] done

### Intent
Document the four new environment variables the harness needs so any
teammate can replicate the setup. `.env.example` is committed; `.env`
is gitignored.

### Expected Outcomes
- `.env.example` gains a clearly separated `EVALUATION HARNESS` section
- Variables for Orchestrate endpoint, IBM Cloud API key, and judge model
  gateway are documented with comments explaining each one
- Existing BLS_API_KEY and transport sections are untouched

### Todo List
1. Open `.env.example` (repo root, 25 lines currently)
2. Append a new section after the existing BLS block:

```
# ─── Evaluation Harness (eval/phoenix/) ──────────────────────────────────────
# IBM watsonx Orchestrate — deployed agent endpoint
# Found in Orchestrate UI: Deployments → your deployment → API endpoint
ORCHESTRATE_BASE_URL=https://us-south.ml.cloud.ibm.com
ORCHESTRATE_DEPLOYMENT_ID=your-deployment-id-here

# IBM Cloud API key — used to exchange for a short-lived IAM bearer token
# Never use a BLS_API_KEY here; this is a separate IBM Cloud credential
# Generate at: https://cloud.ibm.com/iam/apikeys
IBM_CLOUD_API_KEY=your-ibm-cloud-api-key-here

# Judge model gateway (keep distinct from the agent model in Orchestrate)
# The judge should be a different/stronger model to reduce self-preference bias
USAI_API_KEY=your-judge-gateway-key-here
USAI_BASE_URL=https://your-gateway.example.com
JUDGE_MODEL=claude_4_6_sonnet
```

### Relevant Context
- `.env.example` currently ends with the BLS_API_KEY comment block
- IAM token exchange is required: Orchestrate uses Bearer tokens, not
  raw API keys on the wire. `IBM_CLOUD_API_KEY` is the seed credential;
  `agent.py` calls the IAM token endpoint to exchange it at runtime.
- `JUDGE_MODEL` default in judges code: `os.getenv("JUDGE_MODEL", "claude_4_6_sonnet")`

---

## Sub-Task 3 — Generate the question dataset (bls-eval-0.csv)

**Status:** [x] done

### Intent
Create a 30-question evaluation dataset that covers all 10 MCP tools
across all 12 supported surveys. Each question must require at least
one tool call to answer, have a single stable verifiable answer, and
be written in natural language as a user would ask it.

Questions are organized into five categories that match the tool
groupings:
- **Discovery** (suggest_series, search_series) — 6 questions
- **Series identity** (decode_series_id, validate_series_id,
  get_series_metadata) — 6 questions
- **Construction** (build_series_id, lookup_area_code,
  lookup_industry_code) — 6 questions
- **Live data** (get_series_data, answer_bls_question) — 8 questions
- **Out-of-scope** (refusal / scope boundary) — 4 questions

The CSV has two columns: `query` (the question) and `responses`
(the ground-truth answer the judge compares against).

### Expected Outcomes
- `eval/phoenix/datasets/bls-eval-0/examples/bls-eval-0.csv` exists
  with exactly 30 rows plus a header
- Every row has a non-empty `query` and `responses` value
- Answers are sourced from known BLS catalog facts (series IDs,
  survey names, segment labels) or from verified live API values
  for a pinned historical period (e.g. a specific month in 2023
  that will not be revised)
- The dataset is registered in `eval/phoenix/datasets.yaml`

### Todo List
1. Create the directory `eval/phoenix/datasets/bls-eval-0/examples/`
2. Verify all live data answers against the BLS Public Data API using
   `get_series_data` before writing the CSV. The values below have been
   confirmed against the live API (end_year=2026) on the date this plan
   was written. All values are final (no `P` preliminary footnote) for
   the pinned historical periods used. Re-verify before the dataset is
   committed if more than 12 months have passed, as BLS may issue
   annual benchmark revisions that change historical values.
3. Write `bls-eval-0.csv` with the following 30 rows:

**Discovery questions (6):**
| query | responses |
|-------|-----------|
| What BLS series covers the national unemployment rate? | LNS14000000 |
| Suggest a BLS series for tracking U.S. consumer prices | CUUR0000SA0 |
| What series tracks total nonfarm payroll employment nationally? | CES0000000001 |
| Find a BLS series for job openings in the United States | JTS000000000000000JOL |
| What series measures U.S. labor force participation rate? | LNS11300000 |
| Suggest a series for tracking U.S. producer prices | WPUFD49104 |

**Series identity questions (6):**
| query | responses |
|-------|-----------|
| What survey does the series CES0000000001 belong to? | Current Employment Statistics |
| Is the series LNS14000000 seasonally adjusted? | Yes |
| What is the unit of measurement for series CUUR0000SA0? | index 1982-84=100 |
| Is the series ID XYZ123 valid? | No |
| What does the series LAUST060000000000003 measure? | unemployment rate |
| What is the measure type for series LNS11300000? | rate |

**Construction questions (6):**
| query | responses |
|-------|-----------|
| What is the BLS area code for Chicago in the SM survey? | 16980 |
| What industry code represents Total Nonfarm in the CE survey? | 00000000 |
| Build the BLS series ID for seasonally adjusted total nonfarm employment nationally in the CE survey | CES0000000001 |
| What area code does BLS use for Los Angeles in the SM survey? | 31080 |
| What is the NAICS industry code for Healthcare and Social Assistance? | 620000 |
| Look up the BLS area code for New York City metro in the SM survey | 35620 |

**Live data questions (8) — verified against BLS API:**
| query | responses | series | verified value |
|-------|-----------|--------|----------------|
| What was the U.S. national unemployment rate in January 2024? | 3.7 | LNS14000000 2024-M01 | ✅ 3.7 |
| How many nonfarm payroll jobs were reported for December 2023? | 156857 | CES0000000001 2023-M12 | ✅ 156857 (corrected from 157736) |
| What was the CPI for All Urban Consumers in June 2023? | 305.109 | CUUR0000SA0 2023-M06 | ✅ 305.109 |
| What was the labor force participation rate in March 2024? | 62.7 | LNS11300000 2024-M03 | ✅ 62.7 |
| What was the U.S. unemployment rate in January 2020? | 3.6 | LNS14000000 2020-M01 | ✅ 3.6 |
| What was the CPI for All Urban Consumers in February 2020? | 258.678 | CUUR0000SA0 2020-M02 | ✅ 258.678 (question updated to February — January value is 257.971) |
| What were total nonfarm payrolls in January 2023? | 154776 | CES0000000001 2023-M01 | ✅ 154776 (corrected from 155944) |
| What was the U.S. unemployment rate in December 2019? | 3.6 | LNS14000000 2019-M12 | ✅ 3.6 (corrected from 3.5) |

**Out-of-scope questions (4):**
| query | responses |
|-------|-----------|
| What will the unemployment rate be next year? | I cannot predict future values; BLS only publishes historical data |
| Should I invest in stocks based on the latest CPI reading? | I cannot provide investment advice |
| What is the GDP of the United States? | GDP is not a BLS metric; it is published by the Bureau of Economic Analysis |
| Can you give me the name of the current U.S. Secretary of Labor? | Personnel information is outside the scope of BLS statistical data |

3. Register the dataset in `eval/phoenix/datasets.yaml`:
```yaml
datasets:
  bls-eval-0:
    csv_path: datasets/bls-eval-0/examples/bls-eval-0.csv
    input_keys:
      - query
    output_keys:
      - responses
    description: >
      30-question BLS evaluation set covering all 10 MCP tools across
      12 surveys. Includes discovery, identity, construction, live data,
      and out-of-scope refusal categories.
```

### Relevant Context
- Flagship series confirmed from `bls_flagship_series.py`:
  LNS14000000, CUUR0000SA0, CES0000000001, LNS11300000 all present
- Live data answers verified against the BLS Public Data API (end_year=2026).
  Three values were corrected from the initial draft:
  - Nonfarm payrolls Dec 2023: 157736 → **156857**
  - Nonfarm payrolls Jan 2023: 155944 → **154776**
  - Unemployment rate Dec 2019: 3.5 → **3.6**
  - CPI question updated from January to February 2020 (Jan=257.971,
    Feb=258.678 is a cleaner round number for grading purposes)
  Re-verify if more than 12 months have passed since this plan was written,
  as annual BLS benchmark revisions can revise historical values.
- `validate_series_id` tool confirms XYZ123 is invalid (no recognised prefix)
- Out-of-scope refusals test the agent's scope boundary behaviour,
  scored by `check_answer_scope` judge

---

## Sub-Task 4 — Write the OrchestrateAgent (agent.py)

**Status:** [x] done

### Intent
Implement `OrchestrateAgent` — the class that sends a question to the
deployed `gsa_ds_bls_agent` via the watsonx.ai deployment REST API and
returns the agent's plain-text answer. This replaces the
`MultiServerMCPClient` stdio pattern from the Phoenix skill default.

### Expected Outcomes
- `eval/phoenix/agent.py` exists and is importable
- `OrchestrateAgent.run(query)` POSTs to the Orchestrate endpoint and
  returns a string answer
- IAM token exchange happens automatically and tokens are cached for
  their lifetime (up to 1 hour) to avoid a token fetch per question
- Phoenix experiment-level instrumentation is registered in `initialize()`
- A `create_experiment_task()` method returns a sync task closure for
  `run_experiment.py`
- `python agent.py` runs a smoke test against a single known question

### Todo List
1. Create `eval/phoenix/agent.py`
2. Implement `_get_iam_token()` as an async method:
   - POST to `https://iam.cloud.ibm.com/identity/token`
   - Body: `grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={IBM_CLOUD_API_KEY}`
   - Cache the returned `access_token` and its `expiration` timestamp
   - Re-fetch only when fewer than 60 seconds remain on the cached token
3. Implement `run(query: str) -> str`:
   - Call `_get_iam_token()` to get a fresh-enough token
   - POST to `{ORCHESTRATE_BASE_URL}/ml/v1/deployments/{ORCHESTRATE_DEPLOYMENT_ID}/text/chat?version=2024-05-31`
   - Headers: `Authorization: Bearer {token}`, `Content-Type: application/json`
   - Body: `{"messages": [{"role": "user", "content": query}]}`
   - Extract and return `response["choices"][0]["message"]["content"]`
   - Raise `OrchestrateError` (a custom `RuntimeError` subclass) on
     HTTP errors; never expose the token or API key in the error message
4. Implement `initialize()`:
   - Call `load_dotenv()`
   - Register Phoenix OTLP tracer via `phoenix.otel.register()`
   - Instrument LangChain via `LangChainInstrumentor().instrument()`
     (experiment-level spans only; no tool-call detail available from
     Orchestrate)
5. Implement `create_experiment_task()`:
   - Returns a sync `task(example)` closure that calls
     `asyncio.run(self.run(example.input["query"]))`
6. Implement `main()` for standalone smoke testing:
   - Ask "What was the U.S. national unemployment rate in January 2024?"
   - Print the response

### Relevant Context
- `deploy/ibm/agents/gsa_ds_bls_agent.yaml` agent name: `gsa_ds_bls_agent`
- Orchestrate deployment endpoint shape confirmed from watsonx.ai docs:
  `/ml/v1/deployments/{deployment_id}/text/chat?version=2024-05-31`
- `ORCHESTRATE_BASE_URL`, `ORCHESTRATE_DEPLOYMENT_ID`, `IBM_CLOUD_API_KEY`
  read from `.env` via `load_dotenv()`
- Do NOT hardcode the deployment ID — always read from env

---

## Sub-Task 5 — Write the LLM-as-judge evaluators (judges/)

**Status:** [x] done

### Intent
Implement two judges that score agent answers without needing to know
how the answer was produced. Both are plain functions usable as Phoenix
`ClassificationEvaluator` evaluators.

### Expected Outcomes
- `eval/phoenix/judges/__init__.py` re-exports both judges
- `correctness_judge.py` exports `match_expected_response(input, output, expected)`
  returning `"correct"` or `"incorrect"`
- `relevance_judge.py` exports `check_answer_scope(input, output)`
  returning `"within_scope"` or `"out_of_scope"`
- Both judges read `JUDGE_MODEL`, `USAI_API_KEY`, `USAI_BASE_URL` from env
- Both judges set `temperature=0.0`
- Judge prompt templates explicitly state BLS as the agent's domain

### Todo List
1. Create `eval/phoenix/judges/__init__.py` re-exporting both functions
2. Write `eval/phoenix/judges/correctness_judge.py`:
   - Use `phoenix.evals.ClassificationEvaluator` with an `LLM` wrapper
   - Prompt template must:
     - Identify the agent as a BLS (Bureau of Labor Statistics) data
       assistant
     - Accept `{input}` (the question), `{output}` (agent answer),
       `{reference}` (ground truth from `expected["responses"]`)
     - Allow reasonable formatting differences: a value of "3.7" and
       "3.7 percent" are both correct if the number matches
     - Return `"correct"` only when the core fact matches
     - Return `"incorrect"` when the agent refuses, hallucinates, or
       gives the wrong number/series/survey
   - `choices={"correct": 1, "incorrect": 0}`
   - Return `result[0]` (Phoenix returns a list)
3. Write `eval/phoenix/judges/relevance_judge.py`:
   - Same `ClassificationEvaluator` pattern
   - Prompt template must:
     - State that in-scope = factual BLS statistical data questions
     - State that out-of-scope = predictions, investment advice,
       non-BLS economic indicators (e.g. GDP), personnel information
     - Score refusals to in-scope questions as `"out_of_scope"`
     - Score correct refusals to out-of-scope questions as `"within_scope"`
   - `choices={"within_scope": 1, "out_of_scope": 0}`

### Relevant Context
- `JUDGE_MODEL` default: `"claude_4_6_sonnet"`
- Judges run in the same process as `run_experiment.py` so `.env` is
  already loaded by the time they execute
- Out-of-scope refusal questions in the dataset:
  futures/predictions, investment advice, GDP (BEA not BLS),
  personnel info

---

## Sub-Task 6 — Write system prompts (prompts/)

**Status:** [x] done

### Intent
Write two versioned system prompts for the agent-under-test. Even
though the prompt is configured inside Orchestrate rather than injected
at call time, keeping versioned copies here lets the team A/B test
prompt strategies by updating the Orchestrate agent definition between
experiment runs.

### Expected Outcomes
- `eval/phoenix/prompts/system_prompt_v1.txt` describes the agent as a
  BLS data analyst with critical tool-use conventions
- `eval/phoenix/prompts/system_prompt_v2.txt` adds explicit scope
  boundaries (what to answer vs. what to refuse)
- Both files are plain text, no f-strings or templating

### Todo List
1. Write `eval/phoenix/prompts/system_prompt_v1.txt`:
   - Role: BLS data analyst
   - Available tools: all 10 (list by name)
   - Critical conventions:
     - Always call `suggest_series` or `search_series` before
       `get_series_data` unless a series ID is already known
     - Report values exactly as returned (strings, not floats)
     - Surface footnote codes: P = preliminary, R = revised
     - Never replace missing observations ("-" or ".") with zero
     - For current-year data, pass `end_year` as the current year
2. Write `eval/phoenix/prompts/system_prompt_v2.txt`:
   - Everything from v1
   - Add explicit scope section:
     - In scope: factual BLS time-series data, survey descriptions,
       series ID construction/validation, historical observations
     - Out of scope: predictions, forecasts, investment advice,
       non-BLS indicators (GDP, Federal Reserve rates), personnel
       or organisational information
     - Refusal language: "That question is outside the scope of BLS
       statistical data. I can help with..."

### Relevant Context
- Registered tools (all 10): lookup_area_code, lookup_industry_code,
  build_series_id, decode_series_id, validate_series_id, search_series,
  suggest_series, get_series_metadata, get_series_data,
  answer_bls_question
- Server instructions from `app.py` provide a template for the v1 prompt

---

## Sub-Task 7 — Write the Phoenix CLIs (create_dataset.py, run_experiment.py)

**Status:** [x] done

### Intent
Provide two runnable CLI scripts that complete the Phoenix workflow:
upload the dataset once, then run experiments on demand.

### Expected Outcomes
- `create_dataset.py --dataset-name bls-eval-0` uploads the CSV to a
  running Phoenix instance
- `create_dataset.py --dataset-name bls-eval-0 --dry-run` validates
  the CSV locally without uploading (safe for CI pre-flight)
- `run_experiment.py --dataset-name bls-eval-0` runs the full
  experiment (agent calls + both judges) and prints per-question scores
- `run_experiment.py` supports `--system-prompt-version v1|v2` and
  `--experiment-description` flags
- Both scripts call `load_dotenv()` and handle missing env vars with a
  clear error message before making any network calls

### Todo List
1. Write `eval/phoenix/create_dataset.py`:
   - Load `datasets.yaml` to resolve `csv_path` for the given name
   - Validate that `query` and `responses` columns exist in the CSV
   - On `--dry-run`: print row count and column names, exit 0
   - On normal run: upload via
     `phoenix.client.Client().datasets.create_dataset(...)`
   - Support `--list` to print all registered dataset names from YAML
2. Write `eval/phoenix/run_experiment.py`:
   - Accept `--dataset-name`, `--system-prompt-version` (choices: v1, v2),
     `--project-name`, `--phoenix-endpoint`, `--experiment-description`,
     `--no-validate`
   - Load the Phoenix dataset by name
   - Instantiate `OrchestrateAgent` and call `initialize()`
   - Call `client.experiments.run_experiment(dataset, task,
     evaluators=[check_answer_scope, match_expected_response], ...)`
   - Print a summary table of scores after completion

### Relevant Context
- `datasets.yaml` path relative to both CLIs: same directory
- Phoenix client default endpoint: `http://localhost:6006`
- `OrchestrateAgent.create_experiment_task()` returns the task closure

---

## Sub-Task 8 — Write eval/phoenix/README.md

**Status:** [x] done

### Intent
Document the harness so any teammate can run it without reading source
code. The README covers setup, the full run workflow, and how to
interpret results.

### Expected Outcomes
- `eval/phoenix/README.md` covers: prerequisites, env setup, starting
  Phoenix, uploading the dataset, running an experiment, and reading scores
- Includes a "how to add more questions" section
- Includes a "how to update the Orchestrate prompt" section linking to
  the prompts/ directory

### Todo List
1. Write `eval/phoenix/README.md` with these sections:
   - **Prerequisites**: Python 3.11+, uv, IBM Cloud API key,
     Orchestrate deployment ID, judge gateway credentials
   - **Setup**: `uv sync --group dev`, populate `.env` from `.env.example`
   - **Start Phoenix**: `uv run arize-phoenix serve`
   - **Upload dataset**: `uv run create_dataset.py --dataset-name bls-eval-0`
   - **Run experiment**: `uv run run_experiment.py --dataset-name bls-eval-0`
   - **Read results**: what correctness score means, what scope score means,
     how to find failing questions in the Phoenix UI
   - **Adding questions**: edit the CSV, re-upload with `create_dataset.py`
   - **Updating the agent prompt**: edit `prompts/system_prompt_v{n}.txt`,
     paste into the Orchestrate agent definition, re-run experiment with
     `--system-prompt-version v{n}`

### Relevant Context
- `eval/databricks/README.md` exists and is a good reference for tone
  and format conventions in this repo
- Run all commands from `eval/phoenix/` after `cd eval/phoenix`

---

## Implementation Order

Sub-tasks are designed to be completed sequentially:

```
1 → pyproject.toml deps     (no dependencies)
2 → .env.example             (no dependencies)
3 → dataset CSV + YAML       (no dependencies)
4 → agent.py                 (needs .env.example for var names)
5 → judges/                  (needs .env.example for var names)
6 → prompts/                 (needs tool list from app.py — already known)
7 → CLIs                     (needs agent.py, judges/, datasets.yaml)
8 → README.md                (needs everything above)
```

Sub-tasks 1, 2, and 3 have no dependencies on each other and can be
done in any order or in parallel.
