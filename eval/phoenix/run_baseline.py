"""run_baseline.py — run a no-tool baseline experiment against the BLS dataset.

Sends each question directly to a plain LLM (no tools, no Orchestrate) and
scores the answers with the same two judges used in run_experiment.py.  The
resulting experiment appears in Phoenix alongside the tool-augmented run so
you can compare correctness lift directly.

Usage:
    uv run run_baseline.py --dataset-name bls-eval-0
    uv run run_baseline.py --dataset-name bls-eval-0 \
        --experiment-description "no-tool baseline"

Run from eval/phoenix/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import litellm
import yaml
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_DATASETS_YAML = _HERE / "datasets.yaml"

_DEFAULT_MODEL = "meta-llama/llama-3-3-70b-instruct"

_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about U.S. Bureau of "
    "Labor Statistics (BLS) data. Answer as accurately as you can from your "
    "training knowledge. If you do not know the answer, say so."
)


def _load_registry() -> dict:
    with _DATASETS_YAML.open() as f:
        return yaml.safe_load(f)["datasets"]


def _make_task(model_id: str):
    """Return a Phoenix-compatible sync task that calls the LLM with no tools."""

    def task(example) -> str:
        query = example.input["query"]
        try:
            response = litellm.completion(
                model=f"watsonx/{model_id}",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                max_tokens=256,
                temperature=0,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            return f"[BaselineError] {exc}"

    return task


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a no-tool baseline experiment against a BLS dataset."
    )
    parser.add_argument("--dataset-name", required=True, metavar="NAME")
    parser.add_argument(
        "--baseline-model",
        default=os.getenv("JUDGE_MODEL", _DEFAULT_MODEL),
        metavar="MODEL_ID",
        help=f"watsonx.ai model ID for the baseline LLM. Default: {_DEFAULT_MODEL}",
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
    )
    parser.add_argument("--experiment-description", default="", metavar="TEXT")
    parser.add_argument("--dataset-version-id", default=None, metavar="ID")
    args = parser.parse_args()

    # Validate dataset exists in registry
    registry = _load_registry()
    if args.dataset_name not in registry:
        print(
            f"ERROR: '{args.dataset_name}' not found in datasets.yaml.\n"
            f"       Available: {list(registry)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Deferred imports
    try:
        from judges import check_answer_scope, match_expected_response
        from phoenix.client import Client
    except ImportError as exc:
        print(
            f"ERROR: Missing dependency: {exc}\nRun: uv sync --group dev",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    os.environ["PHOENIX_PROJECT_NAME"] = args.project_name
    os.environ["PHOENIX_ENDPOINT"] = args.phoenix_endpoint

    client = Client(base_url=args.phoenix_endpoint)
    try:
        dataset = client.datasets.get_dataset(
            dataset=args.dataset_name,
            version_id=args.dataset_version_id,
        )
    except Exception as exc:
        print(
            f"ERROR: Could not load dataset '{args.dataset_name}' from Phoenix.\n"
            f"       {exc}\n"
            f"       Did you run: uv run create_dataset.py "
            f"--dataset-name {args.dataset_name}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    slug = (
        args.experiment_description.replace(" ", "_")
        if args.experiment_description
        else "no-tool-baseline"
    )
    experiment_name = f"{args.dataset_name}-baseline-{slug}"

    n_examples = len(dataset)
    print(
        f"\nRunning no-tool baseline experiment:\n"
        f"  Dataset:  {args.dataset_name} ({n_examples} questions)\n"
        f"  Model:    {args.baseline_model}\n"
        f"  Experiment: {experiment_name}\n"
        f"  Phoenix:  {args.phoenix_endpoint}\n"
    )

    task = _make_task(args.baseline_model)

    experiment = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[check_answer_scope, match_expected_response],
        experiment_name=experiment_name,
        experiment_description=args.experiment_description or "no-tool baseline",
    )

    print(f"\nExperiment complete: {experiment['experiment_id']}")
    print(f"View results at: {args.phoenix_endpoint}/projects/{args.project_name}")


if __name__ == "__main__":
    main()
