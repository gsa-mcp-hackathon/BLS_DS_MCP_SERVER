"""run_multi_eval.py — run the BLS Phoenix evaluation N times and report aggregated
metrics.

Runs the full evaluation against the deployed gsa_ds_bls_agent N times (default 5),
captures correctness rate, scope-adherence rate, and operational metrics (latency,
tool-call count) for each run, then writes a CSV with per-run rows plus a final
AVERAGE summary row.

Usage:
    uv run run_multi_eval.py --dataset-name bls-eval-0
    uv run run_multi_eval.py --dataset-name bls-eval-0 --runs 5
    uv run run_multi_eval.py --dataset-name bls-eval-0 --runs 3 --output my_results.csv
    uv run run_multi_eval.py --dataset-name bls-eval-0 --system-prompt-version v2

Run from eval/phoenix/.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_DATASETS_YAML = _HERE / "datasets.yaml"
_PROMPT_VERSIONS = ["v1", "v2"]

_CSV_FIELDNAMES = [
    "run",
    "experiment_id",
    "n_questions",
    "n_correct",
    "correctness_rate",
    "n_within_scope",
    "scope_adherence_rate",
    "avg_latency_s",
    "p95_latency_s",
    "avg_tool_calls",
    "error",
]


# ---------------------------------------------------------------------------
# Helpers — identical pattern to run_experiment.py
# ---------------------------------------------------------------------------


def _load_registry() -> dict:
    with _DATASETS_YAML.open() as f:
        return yaml.safe_load(f)["datasets"]


def _check_env() -> None:
    """Fail fast with clear messages if required env vars are missing."""
    required = {
        "ORCHESTRATE_BASE_URL": "Orchestrate instance base URL",
        "ORCHESTRATE_AGENT_ID": "UUID of the deployed Orchestrate agent",
        "IBM_CLOUD_API_KEY": "IBM Cloud API key for IAM token exchange",
    }
    missing = {k: v for k, v in required.items() if not os.getenv(k)}
    if missing:
        for var, desc in missing.items():
            print(f"ERROR: {var} is not set ({desc})", file=sys.stderr)
        print(
            "\nSet these in your .env file (see .env.example for reference).",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------


def _extract_metrics(exp: dict, run_index: int, tool_counts: list[int] | None = None) -> dict:
    """Compute per-run correctness, scope, latency, and tool-call metrics from a
    Phoenix experiment.

    Replicates the build_table join logic from phoenix_query.py inline so there
    is no cross-file dependency on that script.

    Args:
        exp:         Full experiment dict from client.experiments.get_experiment().
        run_index:   The 1-based run number, stored in the returned dict.
        tool_counts: Per-question tool call counts collected from agent_v2.
                     When None or empty, avg_tool_calls is reported as "N/A".

    Returns:
        A dict with all _CSV_FIELDNAMES populated.
    """
    # ── Join evaluation labels onto task runs ─────────────────────────────
    # evaluation_runs: list of objects with .experiment_run_id, .name, .result
    evals: dict[str, dict] = {}
    for ev in exp.get("evaluation_runs", []):
        run_id = ev.experiment_run_id
        label = (ev.result or {}).get("label", "")
        evals.setdefault(run_id, {})[ev.name] = label

    rows = []
    latencies: list[float] = []

    for tr in exp.get("task_runs", []):
        run_id = tr["id"]
        scores = evals.get(run_id, {})

        correctness = scores.get("match_expected_response", "")
        scope = scores.get("check_answer_scope", "")
        rows.append({"correctness": correctness, "scope": scope})

        # Latency from Phoenix ISO 8601 start_time / end_time fields
        start = tr.get("start_time")
        end = tr.get("end_time")
        if start is not None and end is not None:
            try:
                t0 = datetime.fromisoformat(str(start)).replace(tzinfo=timezone.utc)
                t1 = datetime.fromisoformat(str(end)).replace(tzinfo=timezone.utc)
                latencies.append((t1 - t0).total_seconds())
            except (TypeError, ValueError):
                pass  # unparseable timestamp — skip silently

    n_questions = len(rows)
    n_correct = sum(1 for r in rows if r["correctness"] == "correct")
    n_within_scope = sum(1 for r in rows if r["scope"] == "within_scope")

    correctness_rate = n_correct / n_questions if n_questions else 0.0
    scope_adherence_rate = n_within_scope / n_questions if n_questions else 0.0

    if latencies:
        avg_latency_s: float | str = statistics.mean(latencies)
        # statistics.quantiles requires at least 2 data points for n=100
        if len(latencies) >= 2:
            p95_latency_s: float | str = statistics.quantiles(latencies, n=100)[94]
        else:
            p95_latency_s = latencies[0]
    else:
        avg_latency_s = "N/A"
        p95_latency_s = "N/A"

    avg_tool_calls: float | str = (
        round(statistics.mean(tool_counts), 2)
        if tool_counts
        else "N/A"
    )

    return {
        "run": run_index,
        "experiment_id": exp.get("id", exp.get("experiment_id", "")),
        "n_questions": n_questions,
        "n_correct": n_correct,
        "correctness_rate": correctness_rate,
        "n_within_scope": n_within_scope,
        "scope_adherence_rate": scope_adherence_rate,
        "avg_latency_s": avg_latency_s,
        "p95_latency_s": p95_latency_s,
        "avg_tool_calls": avg_tool_calls,
        "error": False,
    }


def _build_average_row(successful: list[dict]) -> dict:
    """Compute mean values across all successful runs."""
    avg: dict = {
        "run": "AVERAGE",
        "experiment_id": "",
        "error": "",
    }

    if not successful:
        for key in (
            "n_questions",
            "n_correct",
            "correctness_rate",
            "n_within_scope",
            "scope_adherence_rate",
            "avg_latency_s",
            "p95_latency_s",
        ):
            avg[key] = "N/A"
        return avg

    avg["n_questions"] = round(statistics.mean(r["n_questions"] for r in successful))
    avg["n_correct"] = round(statistics.mean(r["n_correct"] for r in successful))
    avg["n_within_scope"] = round(
        statistics.mean(r["n_within_scope"] for r in successful)
    )
    avg["correctness_rate"] = statistics.mean(r["correctness_rate"] for r in successful)
    avg["scope_adherence_rate"] = statistics.mean(
        r["scope_adherence_rate"] for r in successful
    )

    lat_values = [r["avg_latency_s"] for r in successful if r["avg_latency_s"] != "N/A"]
    p95_values = [r["p95_latency_s"] for r in successful if r["p95_latency_s"] != "N/A"]
    avg["avg_latency_s"] = statistics.mean(lat_values) if lat_values else "N/A"
    avg["p95_latency_s"] = statistics.mean(p95_values) if p95_values else "N/A"

    tc_values = [r["avg_tool_calls"] for r in successful if r["avg_tool_calls"] != "N/A"]
    avg["avg_tool_calls"] = round(statistics.mean(tc_values), 2) if tc_values else "N/A"

    return avg


def _format_row(row: dict) -> dict:
    """Return a copy of *row* with floats formatted for CSV output."""
    out = dict(row)
    for key in ("correctness_rate", "scope_adherence_rate"):
        if isinstance(out[key], float):
            out[key] = f"{out[key]:.4f}"
    for key in ("avg_latency_s", "p95_latency_s"):
        if isinstance(out[key], float):
            out[key] = f"{out[key]:.2f}"
    return out


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------


def _print_summary_table(results: list[dict]) -> None:
    """Print a fixed-width summary table to stdout."""
    header = (
        f"{'Run':<10} {'Correctness':>13} {'Scope':>13} "
        f"{'Avg Lat(s)':>12} {'P95 Lat(s)':>12} {'Avg Tools':>11}  {'Experiment ID'}"
    )
    print("\n" + header)
    print("-" * len(header))
    for r in results:
        run_label = str(r["run"])
        correctness = (
            f"{r['correctness_rate']:.1%}"
            if isinstance(r["correctness_rate"], float)
            else str(r["correctness_rate"])
        )
        scope = (
            f"{r['scope_adherence_rate']:.1%}"
            if isinstance(r["scope_adherence_rate"], float)
            else str(r["scope_adherence_rate"])
        )
        avg_lat = (
            f"{r['avg_latency_s']:.2f}"
            if isinstance(r["avg_latency_s"], float)
            else str(r["avg_latency_s"])
        )
        p95_lat = (
            f"{r['p95_latency_s']:.2f}"
            if isinstance(r["p95_latency_s"], float)
            else str(r["p95_latency_s"])
        )
        avg_tc = (
            f"{r['avg_tool_calls']:.2f}"
            if isinstance(r["avg_tool_calls"], float)
            else str(r["avg_tool_calls"])
        )
        exp_id = str(r.get("experiment_id", ""))
        print(
            f"{run_label:<10} {correctness:>13} {scope:>13} "
            f"{avg_lat:>12} {p95_lat:>12} {avg_tc:>11}  {exp_id}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the BLS Phoenix evaluation N times and report aggregated metrics."
        )
    )
    parser.add_argument(
        "--dataset-name",
        required=True,
        metavar="NAME",
        help="Dataset name from datasets.yaml (e.g. bls-eval-0).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        metavar="N",
        help="Number of times to repeat the evaluation. Default: 5.",
    )
    parser.add_argument(
        "--system-prompt-version",
        choices=_PROMPT_VERSIONS,
        default="v1",
        metavar="VERSION",
        help=f"System prompt version to use: {_PROMPT_VERSIONS}. Default: v1.",
    )
    parser.add_argument(
        "--output",
        default="eval_results.csv",
        metavar="FILE",
        help="Output CSV path. Default: eval_results.csv.",
    )
    parser.add_argument(
        "--project-name",
        default="bls-eval",
        metavar="NAME",
        help="Phoenix project name. Default: bls-eval.",
    )
    parser.add_argument(
        "--phoenix-endpoint",
        default=os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006"),
        metavar="URL",
        help="Phoenix server URL. Default: http://localhost:6006.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip env var validation (use if you know what you are doing).",
    )
    args = parser.parse_args()

    if not args.no_validate:
        _check_env()

    # ── Resolve dataset ────────────────────────────────────────────────────
    registry = _load_registry()
    if args.dataset_name not in registry:
        print(
            f"ERROR: '{args.dataset_name}' not found in datasets.yaml.\n"
            f"       Available: {list(registry)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # ── Deferred imports (so --help works without the full dep stack) ──────
    try:
        from agent_v2 import OrchestrateAgentV2
        from judges import check_answer_scope, match_expected_response
        from phoenix.client import Client
    except ImportError as exc:
        print(
            f"ERROR: Missing dependency: {exc}\nRun: uv sync --group dev",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    # ── Initialise Phoenix env vars, agent, and tracer ─────────────────────
    os.environ["PHOENIX_PROJECT_NAME"] = args.project_name
    os.environ["PHOENIX_ENDPOINT"] = args.phoenix_endpoint

    agent = OrchestrateAgentV2(system_prompt_version=args.system_prompt_version)
    agent.initialize()

    # ── Load Phoenix client and dataset (once, reused across all runs) ─────
    client = Client(base_url=args.phoenix_endpoint)
    try:
        dataset = client.datasets.get_dataset(dataset=args.dataset_name)
    except Exception as exc:
        print(
            f"ERROR: Could not load dataset '{args.dataset_name}' from Phoenix.\n"
            f"       {exc}\n"
            f"       Did you run: uv run create_dataset.py "
            f"--dataset-name {args.dataset_name}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    n_examples = len(dataset)
    print(
        f"\nMulti-run evaluation:\n"
        f"  Dataset:        {args.dataset_name} ({n_examples} questions)\n"
        f"  Prompt version: {args.system_prompt_version}\n"
        f"  Runs:           {args.runs}\n"
        f"  Phoenix:        {args.phoenix_endpoint}\n"
        f"  Output CSV:     {args.output}\n"
    )

    # ── Run loop ───────────────────────────────────────────────────────────
    results: list[dict] = []

    for i in range(1, args.runs + 1):
        experiment_name = f"{args.dataset_name}-{args.system_prompt_version}-run{i}"
        print(f"\nRun {i}/{args.runs}: {experiment_name}")

        try:
            run_tool_counts: list[int] = []
            inner_task = agent.create_experiment_task()

            def task_with_counts(
                example,
                _inner=inner_task,
                _counts=run_tool_counts,
            ) -> str:
                result = _inner(example)
                if agent.last_run_result is not None:
                    _counts.append(agent.last_run_result.tool_call_count)
                return result

            raw_exp = client.experiments.run_experiment(
                dataset=dataset,
                task=task_with_counts,
                evaluators=[check_answer_scope, match_expected_response],
                experiment_name=experiment_name,
            )
            exp_id = raw_exp.get("experiment_id", raw_exp.get("id", ""))
            full_exp = client.experiments.get_experiment(experiment_id=exp_id)
            metrics = _extract_metrics(full_exp, run_index=i, tool_counts=run_tool_counts)
            results.append(metrics)

            lat_display = (
                f"{metrics['avg_latency_s']:.2f}s"
                if isinstance(metrics["avg_latency_s"], float)
                else metrics["avg_latency_s"]
            )
            print(
                f"  Done — correctness: {metrics['correctness_rate']:.1%}  "
                f"scope: {metrics['scope_adherence_rate']:.1%}  "
                f"latency: {lat_display}"
            )

        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING: run {i} failed — {exc}")
            results.append(
                {
                    "run": i,
                    "experiment_id": "",
                    "n_questions": "",
                    "n_correct": "",
                    "correctness_rate": "",
                    "n_within_scope": "",
                    "scope_adherence_rate": "",
                    "avg_latency_s": "",
                    "p95_latency_s": "",
                    "avg_tool_calls": "N/A",
                    "error": True,
                }
            )

    # ── Aggregate and write CSV ────────────────────────────────────────────
    successful = [r for r in results if not r["error"]]
    avg_row = _build_average_row(successful)
    results.append(avg_row)

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(_format_row(row))

    print(f"\nWrote {len(results)} rows to {args.output}")

    # ── Print summary table ────────────────────────────────────────────────
    _print_summary_table(results)
    print(f"\nResults written to: {args.output}")


if __name__ == "__main__":
    main()
