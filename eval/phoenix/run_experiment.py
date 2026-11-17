"""run_experiment.py — run a Phoenix evaluation experiment against the
deployed gsa_ds_bls_agent in IBM watsonx Orchestrate.

Usage:
    uv run run_experiment.py --dataset-name bls-eval-0
    uv run run_experiment.py --dataset-name bls-eval-0 --system-prompt-version v2
    uv run run_experiment.py --dataset-name bls-eval-0 \
        --experiment-description "after schema fix"

Run from eval/phoenix/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_DATASETS_YAML = _HERE / "datasets.yaml"
_PROMPTS_DIR = _HERE / "prompts"
_PROMPT_VERSIONS = ["v1", "v2"]


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a Phoenix evaluation experiment against the BLS Orchestrate agent."
        )
    )
    parser.add_argument(
        "--dataset-name",
        required=True,
        metavar="NAME",
        help="Dataset name from datasets.yaml (e.g. bls-eval-0).",
    )
    parser.add_argument(
        "--system-prompt-version",
        choices=_PROMPT_VERSIONS,
        default="v1",
        metavar="VERSION",
        help=f"System prompt version to use: {_PROMPT_VERSIONS}. Default: v1.",
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
        "--experiment-description",
        default="",
        metavar="TEXT",
        help="Optional description for this experiment run.",
    )
    parser.add_argument(
        "--dataset-version-id",
        default=None,
        metavar="ID",
        help="Pin a specific Phoenix dataset version ID.",
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

    # ── Imports (deferred so --help works without full dep stack) ──────────
    try:
        from agent import OrchestrateAgent
        from judges import check_answer_scope, match_expected_response
        from phoenix.client import Client
    except ImportError as exc:
        print(
            f"ERROR: Missing dependency: {exc}\nRun: uv sync --group dev",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    # ── Initialise agent ───────────────────────────────────────────────────
    agent = OrchestrateAgent(system_prompt_version=args.system_prompt_version)
    os.environ["PHOENIX_PROJECT_NAME"] = args.project_name
    os.environ["PHOENIX_ENDPOINT"] = args.phoenix_endpoint
    agent.initialize()

    # ── Load Phoenix dataset ───────────────────────────────────────────────
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
            "       Did you run: "
            f"uv run create_dataset.py --dataset-name {args.dataset_name}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    # ── Build experiment metadata ──────────────────────────────────────────
    slug = (
        args.experiment_description.replace(" ", "_")
        if args.experiment_description
        else ""
    )
    experiment_name = f"{args.dataset_name}-{args.system_prompt_version}" + (
        f"-{slug}" if slug else ""
    )

    n_examples = len(dataset)
    print(
        f"\nRunning experiment:\n"
        f"  Dataset:        {args.dataset_name} ({n_examples} questions)\n"
        f"  Prompt version: {args.system_prompt_version}\n"
        f"  Experiment:     {experiment_name}\n"
        f"  Phoenix:        {args.phoenix_endpoint}\n"
    )

    # ── Run ────────────────────────────────────────────────────────────────
    task = agent.create_experiment_task()

    experiment = client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators=[check_answer_scope, match_expected_response],
        experiment_name=experiment_name,
        experiment_description=args.experiment_description or None,
    )

    # ── Print summary ──────────────────────────────────────────────────────
    print(f"\nExperiment complete: {experiment['experiment_id']}")
    print(f"View results at: {args.phoenix_endpoint}/projects/{args.project_name}")


if __name__ == "__main__":
    main()
