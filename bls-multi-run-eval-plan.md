# Multi-Run Evaluation Script Plan
## `eval/phoenix/run_multi_eval.py`

### Top-Level Overview

**Goal:** Write a new script, `eval/phoenix/run_multi_eval.py`, that runs the BLS agent
evaluation N times (default 5), captures correctness rate, scope-adherence rate, and
operational metrics (latency, tool-call count) for each run, then writes a CSV with all
per-run rows plus a final AVERAGE summary row.

**Scope:**
- One new file only: `eval/phoenix/run_multi_eval.py`
- No changes to any existing file (`run_experiment.py`, `run_baseline.py`, `agent.py`, judges)
- Borrows patterns from `run_experiment.py` (env check, dataset load, deferred imports)
  but implements its own loop and metric extraction — no subprocess calls
- Reuses `OrchestrateAgent`, `check_answer_scope`, `match_expected_response`, and
  `phoenix.client.Client` as-is
- Output: a CSV at a user-configurable path (default `eval_results.csv`) with one row per
  run plus an AVERAGE summary row
- Run from `eval/phoenix/` exactly like the other scripts: `uv run run_multi_eval.py ...`

**Non-goals:**
- No changes to `run_experiment.py`, `run_baseline.py`, or any judge
- No Markdown report output — CSV only
- No subprocess calls to other scripts
- No new Python dependencies — only stdlib + packages already in the `dev` group

---

## Sub-Tasks

---

### Sub-Task 1 — CLI Interface and Environment Validation

**Intent:**
Create the script skeleton with argument parsing and env-var checking so it fails fast with
clear messages if credentials are missing, mirroring the established pattern in
`run_experiment.py`.

**Expected Outcomes:**
- `uv run run_multi_eval.py --help` prints all options with defaults, with no import errors
- Running without required env vars prints one clear error per missing variable and exits
  with code 1
- The following arguments are accepted:
  - `--runs INT` (default 5): how many times to repeat the full evaluation
  - `--dataset-name STR` (required): name from `datasets.yaml` (e.g. `bls-eval-0`)
  - `--system-prompt-version {v1,v2}` (default `v1`): passed to `OrchestrateAgent`
  - `--output STR` (default `eval_results.csv`): output CSV path
  - `--project-name STR` (default `bls-eval`): Phoenix project name
  - `--phoenix-endpoint URL` (default from env `PHOENIX_ENDPOINT` or `http://localhost:6006`)
  - `--no-validate` flag: skip env-var check (matches `run_experiment.py` behaviour)

**Todo List:**
1. Create `eval/phoenix/run_multi_eval.py` with module docstring and usage examples,
   using the same style as `run_experiment.py` lines 1–11
2. Add `from __future__ import annotations` header and all stdlib imports
3. Copy `_load_registry()` and `_check_env()` from `run_experiment.py` lines 31–51 —
   these are identical needs, no reimplementation required
4. Add `argparse` block with the seven arguments listed above
5. Add deferred imports block (same pattern as `run_experiment.py` lines 117–127):
   `from agent import OrchestrateAgent`, `from judges import check_answer_scope,
   match_expected_response`, `from phoenix.client import Client`
6. Validate the dataset name against the registry (same guard as `run_experiment.py`
   lines 108–115)

**Relevant Context:**
- `run_experiment.py` lines 31–51: `_load_registry` and `_check_env` to replicate
- `run_experiment.py` lines 54–102: argparse block structure to follow
- `run_experiment.py` lines 117–127: deferred import pattern
- Required env vars: `ORCHESTRATE_BASE_URL`, `ORCHESTRATE_AGENT_ID`, `IBM_CLOUD_API_KEY`
- Optional but needed for judges: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`

**Status:** [x] done

---

### Sub-Task 2 — Per-Run Experiment Loop

**Intent:**
Initialise the agent and dataset once, then run the Phoenix experiment N times in a loop,
creating a fresh task closure each iteration and naming experiments predictably so they appear
alongside each other in the Phoenix UI.

**Expected Outcomes:**
- Running with `--runs 5` produces 5 distinct Phoenix experiments under the same project
- Each experiment is named `{dataset_name}-{prompt_version}-run{i}`
  (e.g. `bls-eval-0-v1-run1`)
- `OrchestrateAgent` is instantiated once and `agent.initialize()` is called once before
  the loop starts
- The same Phoenix `dataset` object is reused across all runs (loaded once)
- Exceptions from individual runs are caught, logged as warnings, and recorded as
  `{"run": i, "error": True, ...}` without stopping the loop

**Todo List:**
1. Set `PHOENIX_PROJECT_NAME` and `PHOENIX_ENDPOINT` env vars, then instantiate
   `OrchestrateAgent(system_prompt_version=args.system_prompt_version)` and call
   `agent.initialize()` — same sequence as `run_experiment.py` lines 130–133
2. Load the Phoenix `dataset` once via `Client.datasets.get_dataset()` with the same
   error handling as `run_experiment.py` lines 136–150
3. Print a run plan header: dataset name, question count, prompt version, number of runs,
   Phoenix URL, and output CSV path
4. Build a `for i in range(1, args.runs + 1)` loop:
   - Print `\nRun {i}/{args.runs}: {experiment_name}` before each run
   - Call `agent.create_experiment_task()` fresh each iteration (returns a new closure)
   - Call `client.experiments.run_experiment(dataset, task, evaluators=[check_answer_scope,
     match_expected_response], experiment_name=experiment_name)`
   - On success: append the returned experiment dict (augmented with `run=i`) to a results list
   - On exception: print a warning, append `{"run": i, "error": True, "experiment_id": ""}`,
     and continue to the next iteration

**Relevant Context:**
- `agent.py` line 198: `initialize()` docstring says it is idempotent, safe to call once
- `agent.py` lines 223–240: `create_experiment_task()` returns a new sync closure each call,
  safe to call fresh per iteration
- `run_experiment.py` lines 130–184: exact initialise → load → run sequence to follow
- Note: `agent.py` was recently updated to load and pass the system prompt through the API
  (`_load_system_prompt()` at line 46, `messages` construction at lines 140–143) —
  `OrchestrateAgent(system_prompt_version=...)` already handles this correctly, no extra
  work needed in the new script

**Status:** [x] done

---

### Sub-Task 3 — Metric Extraction per Run

**Intent:**
After each experiment completes, fetch its full detail from Phoenix and compute the three
metric categories the submission document requires: correctness rate, scope-adherence rate,
and operational metrics (latency, tool-call count).

**Expected Outcomes:**
- For each successful run a dict is produced with these exact keys:
  - `run` (int): run index 1–N
  - `experiment_id` (str): Phoenix UUID
  - `n_questions` (int): total items evaluated
  - `n_correct` (int): count of `"correct"` labels from `match_expected_response`
  - `correctness_rate` (float): `n_correct / n_questions`
  - `n_within_scope` (int): count of `"within_scope"` labels from `check_answer_scope`
  - `scope_adherence_rate` (float): `n_within_scope / n_questions`
  - `avg_latency_s` (float or string `"N/A"`): mean per-question wall-clock seconds
  - `p95_latency_s` (float or string `"N/A"`): 95th-percentile latency
  - `avg_tool_calls` (string `"N/A"`): always N/A — Orchestrate hides internal tool calls
  - `error` (bool): `False` for successful runs

**Todo List:**
1. After each `run_experiment` call, fetch the full experiment:
   `exp = client.experiments.get_experiment(experiment_id=result["experiment_id"])`
2. Re-implement the `build_table` join logic from `phoenix_query.py` lines 21–46 inline
   (do NOT import or modify `phoenix_query.py`) — join `evaluation_runs` (keyed by
   `experiment_run_id`) with `task_runs` to get per-row correctness and scope labels
3. Count `n_correct` from rows where `correctness == "correct"`; count `n_within_scope`
   where `scope == "within_scope"`; compute rates as floats
4. For latency: check each `task_run` dict for `start_time` and `end_time` fields; if
   present, compute duration in seconds; collect all durations, then compute mean using
   `statistics.mean()` and 95th percentile using `statistics.quantiles(data, n=100)[94]`;
   if the fields are absent on all runs set both latency fields to the string `"N/A"`
5. Set `avg_tool_calls = "N/A"` with an inline comment explaining Orchestrate does not
   expose per-call tool counts via the chat completions endpoint
6. Append the completed per-run dict to the results list

**Relevant Context:**
- `phoenix_query.py` lines 21–46: `build_table` logic to replicate inline
- `task_runs` list in the Phoenix experiment dict: each entry has `id`,
  `dataset_example_id`, `output`, `error`, and potentially `start_time` / `end_time`
- `evaluation_runs` list: each entry has `.experiment_run_id`, `.name`, `.result`
  attributes where `.result` is a dict containing `{"label": "correct"|"incorrect"}`
- `statistics` is stdlib — no extra install needed

**Status:** [x] done

---

### Sub-Task 4 — Aggregate Summary Row and CSV Output

**Intent:**
Compute an AVERAGE row across all successful runs and write everything to CSV, giving the
submission document its aggregated numbers alongside the per-run evidence.

**Expected Outcomes:**
- CSV written to `args.output` (default `eval_results.csv`)
- Fixed column order:
  `run, experiment_id, n_questions, n_correct, correctness_rate, n_within_scope,
   scope_adherence_rate, avg_latency_s, p95_latency_s, avg_tool_calls, error`
- One row per run (indices 1–N); failed runs included with their `error` flag and empty metrics
- Final row: `run = "AVERAGE"`, means of numeric columns computed only from successful runs;
  `"N/A"` propagated for latency if no successful run had timing data
- Rates formatted to 4 decimal places; latency formatted to 2 decimal places
- `"N/A"` string values written as-is (not blank cells)
- Success message printed: `Wrote {N+1} rows to {output_path}`

**Todo List:**
1. Filter `results` to `successful = [r for r in results if not r["error"]]`
2. Build the AVERAGE row dict:
   - `run = "AVERAGE"`, `experiment_id = ""`, `error = ""`
   - `avg_tool_calls = "N/A"`
   - Mean of `correctness_rate` and `scope_adherence_rate` from successful rows
   - Mean of `avg_latency_s` and `p95_latency_s` from successful rows where the value is
     not `"N/A"`; fall back to `"N/A"` if no timing data exists
   - Integer means for `n_questions`, `n_correct`, `n_within_scope` rounded to nearest int
3. Append the AVERAGE row to the results list
4. Format numeric floats before writing: `f"{v:.4f}"` for rates, `f"{v:.2f}"` for latency;
   leave `"N/A"` strings and integers as-is
5. Write CSV using `csv.DictWriter` with `extrasaction="ignore"` and the fixed fieldnames list,
   following the pattern in `phoenix_query.py` lines 94–101

**Relevant Context:**
- `phoenix_query.py` lines 94–101: existing CSV write pattern
- `statistics.mean()` for averages; guard with `if successful` before calling to avoid
  empty-sequence errors
- Root-level `results.csv` is a legacy file — default output is `eval_results.csv` to avoid
  collision

**Status:** [x] done

---

### Sub-Task 5 — Stdout Progress and Final Summary Table

**Intent:**
Provide live feedback during the run and a readable terminal summary after all runs complete,
so the results are visible without opening the CSV.

**Expected Outcomes:**
- Before each run: `\nRun {i}/{N}: {experiment_name}` printed
- After each successful run: one-line summary showing correctness rate, scope rate, latency
- After a failed run: warning line showing which run failed and the exception message
- After all runs: a fixed-width summary table with all per-run rows and the AVERAGE row
- Final line: the full path to the output CSV

**Todo List:**
1. Add `print(f"\nRun {i}/{args.runs}: {experiment_name}")` before each `run_experiment`
   call in the loop
2. After extracting metrics for a successful run, print:
   `  Done — correctness: {rate:.1%}  scope: {rate:.1%}  latency: {lat}`
3. After a failed run, print: `  WARNING: run {i} failed — {exc}`
4. After the loop and CSV write, print a fixed-width table using `str.ljust()` /
   `str.rjust()` (no external tabulate dependency — consistent with `phoenix_query.py`
   lines 114–119) with columns: `Run`, `Correctness`, `Scope`, `Avg Latency`,
   `P95 Latency`, `Experiment ID`
5. Print `\nResults written to: {args.output}` as the final line

**Relevant Context:**
- Table formatting pattern: `phoenix_query.py` lines 114–119
- Use stdlib string formatting only — no `tabulate`, no `pandas`

**Status:** [x] done

---

## Implementation Notes

- **File location:** `eval/phoenix/run_multi_eval.py` — run from that directory with
  `uv run run_multi_eval.py --dataset-name bls-eval-0 --runs 5`
- **Python conventions:** `from __future__ import annotations` header; `ruff` is the
  project linter; follow the import and docstring style of `run_experiment.py` and
  `run_baseline.py`
- **No new dependencies:** `statistics`, `csv`, `argparse`, `os`, `sys`, `pathlib` are
  stdlib; `phoenix.client`, `litellm`, `httpx`, `yaml` are already in the `dev` group
- **agent.py update awareness:** `agent.py` now loads and passes the system prompt via
  `_load_system_prompt()` (line 46) and builds the `messages` list at lines 140–143.
  Instantiating `OrchestrateAgent(system_prompt_version=args.system_prompt_version)`
  already handles this correctly — no special handling needed in the new script
- **Idempotent experiments:** Phoenix appends a UUID suffix to experiment names, so
  re-running the script never overwrites a previous experiment
- **Existing `results.csv`:** legacy manual file at repo root — default output is
  `eval_results.csv` to avoid collision
