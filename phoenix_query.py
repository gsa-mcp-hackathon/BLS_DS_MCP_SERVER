"""Query Phoenix experiment results and print incorrect / out-of-scope rows.

Usage:
    uv run phoenix_query.py                        # most recent experiment
    uv run phoenix_query.py --experiment-id <id>   # specific experiment ID
    uv run phoenix_query.py --list                  # list all experiments
    uv run phoenix_query.py --csv results.csv       # export all rows to CSV
"""

from __future__ import annotations

import argparse
import csv

from phoenix.client import Client

PHOENIX_URL = "http://localhost:6006"
DATASET_NAME = "bls-eval-0"


def build_table(exp: dict, examples: dict) -> list[dict]:
    """Join task runs with their evaluation scores and dataset examples."""
    # Index eval runs by experiment_run_id
    evals: dict[str, dict] = {}
    for ev in exp.get("evaluation_runs", []):
        run_id = ev.experiment_run_id
        label = (ev.result or {}).get("label", "")
        evals.setdefault(run_id, {})[ev.name] = label

    rows = []
    for tr in exp.get("task_runs", []):
        run_id = tr["id"]
        example_id = tr["dataset_example_id"]
        example = examples.get(example_id, {})
        scores = evals.get(run_id, {})
        rows.append(
            {
                "example_id": example_id,
                "question": example.get("input", {}).get("query", ""),
                "expected": example.get("output", {}).get("responses", ""),
                "agent_response": tr.get("output", "") or tr.get("error", ""),
                "correctness": scores.get("match_expected_response", "—"),
                "scope": scores.get("check_answer_scope", "—"),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument(
        "--list", action="store_true", help="List all experiments and exit"
    )
    parser.add_argument(
        "--filter",
        choices=["incorrect", "out_of_scope", "all"],
        default="incorrect",
        help="Which rows to show (default: incorrect)",
    )
    parser.add_argument(
        "--csv",
        metavar="FILE",
        default=None,
        help="Export results to a CSV file (exports all rows, ignores --filter)",
    )
    args = parser.parse_args()

    client = Client(base_url=PHOENIX_URL)
    ds = client.datasets.get_dataset(dataset=DATASET_NAME)
    examples = {ex["id"]: ex for ex in ds.examples}
    experiments = client.experiments.list(dataset_id=ds.id)

    if args.list:
        print(f"{'Name':<45} {'ID'}")
        print("-" * 80)
        for e in experiments:
            print(f"{e.get('name', '?'):<45} {e.get('id', '?')}")
        return

    # Pick experiment
    if args.experiment_id:
        exp_id = args.experiment_id
    else:
        # Most recent is first in the list
        exp_id = experiments[0]["id"]
        exp_name = experiments[0].get("name")
        print(f"Using most recent experiment: {exp_name} ({exp_id})\n")

    exp = client.experiments.get_experiment(experiment_id=exp_id)
    rows = build_table(exp, examples)

    # CSV export — all rows, no filter
    if args.csv:
        fieldnames = ["question", "expected", "agent_response", "correctness", "scope"]
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {len(rows)} rows to {args.csv}")
        return

    # Apply filter for console output
    if args.filter == "incorrect":
        rows = [r for r in rows if r["correctness"] == "incorrect"]
    elif args.filter == "out_of_scope":
        rows = [r for r in rows if r["scope"] == "out_of_scope"]
    # "all" keeps everything

    if not rows:
        print("No rows match the filter.")
        return

    print(f"{'#':<4} {'Correctness':<13} {'Scope':<14} {'Question (truncated)'}")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        preview = (r["question"] or r["agent_response"])[:70].replace("\n", " ")
        print(f"{i:<4} {r['correctness']:<13} {r['scope']:<14} {preview}")

    print(f"\nTotal: {len(rows)} row(s)")


if __name__ == "__main__":
    main()
