# BLS Evaluation Harness

Phoenix-based evaluation harness for the `gsa_ds_bls_agent` deployed in
IBM watsonx Orchestrate. Measures how well the agent answers Bureau of
Labor Statistics (BLS) data questions using its 12 registered MCP tools.

Evaluation is performed at the **question/answer level**: the harness
sends each question to the deployed Orchestrate agent via the watsonx.ai
REST API, scores the answer with two LLM-as-judge evaluators, and logs
results to Phoenix.

---

## Directory layout

```
eval/phoenix/
├── agent.py                # OrchestrateAgent — HTTP client for the deployed agent
├── create_dataset.py       # CLI: upload a CSV dataset to Phoenix
├── run_experiment.py       # CLI: run an experiment (agent + judges)
├── datasets.yaml           # Dataset registry
├── judges/
│   ├── __init__.py
│   ├── correctness_judge.py   # match_expected_response (correct / incorrect)
│   └── relevance_judge.py     # check_answer_scope (within_scope / out_of_scope)
├── prompts/
│   ├── system_prompt_v1.txt   # BLS analyst — tool conventions only
│   └── system_prompt_v2.txt   # + explicit scope boundaries and refusal language
└── datasets/
    └── bls-eval-0/
        └── examples/
            └── bls-eval-0.csv  # 30-question verified dataset
```

---

## Prerequisites

- Python 3.11+, `uv`
- IBM Cloud account with an active watsonx Orchestrate deployment
  (`gsa_ds_bls_agent` or equivalent)
- IBM Cloud API key (for IAM bearer token exchange)
- Judge model gateway credentials (a separate model from the agent)

---

## Setup

**1. Install dependencies**

From the repo root:

```bash
uv sync --group dev
```

**2. Configure credentials**

Copy `.env.example` from the repo root to `.env` and fill in the
eval-specific variables:

```bash
cp .env.example .env
# edit .env and set:
#   ORCHESTRATE_BASE_URL       your watsonx.ai regional endpoint
#   ORCHESTRATE_DEPLOYMENT_ID  deployment ID from Orchestrate UI
#   IBM_CLOUD_API_KEY          IBM Cloud API key
#   USAI_API_KEY               judge gateway key
#   USAI_BASE_URL              judge gateway base URL
#   JUDGE_MODEL                judge model name (default: claude_4_6_sonnet)
```

Your `ORCHESTRATE_DEPLOYMENT_ID` is visible in the Orchestrate UI under
**Deployments → your deployment → API endpoint**.

---

## Running an experiment

All commands are run from `eval/phoenix/`.

**Step 1 — Start Phoenix** (UI at http://localhost:6006)

```bash
uv run arize-phoenix serve
```

**Step 2 — Upload the dataset** (one-time per dataset)

```bash
uv run create_dataset.py --dataset-name bls-eval-0
```

Validate without uploading:

```bash
uv run create_dataset.py --dataset-name bls-eval-0 --dry-run
```

List registered datasets:

```bash
uv run create_dataset.py --list
```

**Step 3 — Run an experiment**

```bash
uv run run_experiment.py --dataset-name bls-eval-0
```

With options:

```bash
# use v2 prompt (adds explicit scope boundary instructions)
uv run run_experiment.py --dataset-name bls-eval-0 --system-prompt-version v2

# tag the run with a description
uv run run_experiment.py --dataset-name bls-eval-0 \
  --experiment-description "after decode_series_id docstring fix"
```

**Step 4 — Review results**

Open http://localhost:6006, navigate to the **bls-eval** project, and
open your experiment. Each row shows:

| Column | Meaning |
|--------|---------|
| `correctness` | `correct` / `incorrect` — does the answer match ground truth? |
| `scope` | `within_scope` / `out_of_scope` — did the agent handle scope correctly? |

Click any failing row to see the full question, agent answer, and judge
reasoning. Use this to decide whether the fix belongs in:

- **Tool schema / docstring** — the agent called the wrong tool or
  misread a parameter description
- **System prompt** — the agent didn't follow a convention (units, footnotes)
- **The question itself** — the ground-truth answer needs updating

---

## Scores guide

| Correctness | Scope | Interpretation |
|---|---|---|
| high | high | Agent is working well |
| low | high | Agent finds the right data but returns wrong values — check tool schemas |
| high | low | Agent answers correctly but also answers things it should refuse |
| low | low | Fundamental tool-use or prompt problem |

---

## Adding more questions

1. Edit `datasets/bls-eval-0/examples/bls-eval-0.csv` — add rows with
   `query` and `responses` columns.
2. Verify any live data answers against the BLS API using `get_series_data`
   before committing (annual benchmark revisions can change historical values).
3. Re-upload: `uv run create_dataset.py --dataset-name bls-eval-0`
4. Re-run: `uv run run_experiment.py --dataset-name bls-eval-0`

To register a new dataset entirely, add an entry to `datasets.yaml` and
place the CSV at the path specified in `csv_path`.

---

## Updating the Orchestrate agent prompt

Prompt versions are stored in `prompts/`:
- `system_prompt_v1.txt` — basic BLS analyst with tool conventions
- `system_prompt_v2.txt` — adds explicit scope boundary and refusal language

To A/B test a prompt change:
1. Edit the relevant `system_prompt_v{n}.txt` file.
2. Paste the updated text into the Orchestrate agent definition
   (`deploy/ibm/agents/gsa_ds_bls_agent.yaml`, `instructions` field).
3. Redeploy the agent in Orchestrate.
4. Re-run with `--system-prompt-version v{n} --experiment-description "prompt change description"`.
5. Compare scores between runs in the Phoenix UI.

---

## Smoke testing the agent connection

Before running a full experiment, test that the Orchestrate endpoint is
reachable:

```bash
uv run python agent.py
```

This asks one question ("What was the U.S. national unemployment rate in
January 2024?") and prints the agent's answer. Expected output: `3.7`.
