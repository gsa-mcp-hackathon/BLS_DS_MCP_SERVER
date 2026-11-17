"""create_dataset.py — upload a BLS eval CSV dataset to a Phoenix instance.

Usage:
    # validate only (no upload):
    uv run create_dataset.py --dataset-name bls-eval-0 --dry-run

    # upload to local Phoenix:
    uv run create_dataset.py --dataset-name bls-eval-0

    # list registered datasets:
    uv run create_dataset.py --list

Run from eval/phoenix/.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_DATASETS_YAML = _HERE / "datasets.yaml"


def _load_registry() -> dict:
    with _DATASETS_YAML.open() as f:
        return yaml.safe_load(f)["datasets"]


def _validate_csv(csv_path: Path, input_keys: list[str], output_keys: list[str]) -> int:
    """Validate the CSV has the required columns. Returns the row count."""
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        raise SystemExit(1)

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)

    required = set(input_keys) | set(output_keys)
    missing = required - set(columns)
    if missing:
        print(
            f"ERROR: CSV is missing required columns: {sorted(missing)}\n"
            f"       Found columns: {sorted(columns)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    empty = [
        i + 2  # 1-based, +1 for header
        for i, row in enumerate(rows)
        if any(not row.get(k, "").strip() for k in required)
    ]
    if empty:
        print(
            f"WARNING: {len(empty)} row(s) have empty required fields "
            f"(rows: {empty[:10]}{'...' if len(empty) > 10 else ''})"
        )

    return len(rows)


def cmd_list(args: argparse.Namespace) -> None:  # noqa: ARG001
    registry = _load_registry()
    print("Registered datasets:")
    for name, meta in registry.items():
        print(f"  {name}: {meta.get('description', '').strip()}")


def cmd_upload(args: argparse.Namespace) -> None:
    registry = _load_registry()

    if args.dataset_name not in registry:
        print(
            f"ERROR: '{args.dataset_name}' not found in datasets.yaml.\n"
            f"       Available: {list(registry)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    meta = registry[args.dataset_name]
    csv_path = _HERE / meta["csv_path"]
    input_keys: list[str] = meta["input_keys"]
    output_keys: list[str] = meta["output_keys"]
    phoenix_name = getattr(args, "phoenix_name", None) or args.dataset_name

    row_count = _validate_csv(csv_path, input_keys, output_keys)

    if args.dry_run:
        print(
            f"DRY RUN — dataset '{args.dataset_name}'\n"
            f"  CSV path:    {csv_path}\n"
            f"  Rows:        {row_count}\n"
            f"  Columns:     {input_keys + output_keys}\n"
            f"  Phoenix name: {phoenix_name}\n"
            "  (no upload performed)"
        )
        return

    endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    print(f"Uploading '{args.dataset_name}' to Phoenix at {endpoint} ...")

    try:
        import pandas as pd
        from phoenix.client import Client

        df = pd.read_csv(csv_path)
        client = Client(base_url=endpoint)
        dataset = client.datasets.create_dataset(
            name=phoenix_name,
            dataframe=df,
            input_keys=input_keys,
            output_keys=output_keys,
        )
        print(f"Uploaded: {dataset.name} ({row_count} rows)")
    except Exception as exc:
        print(f"ERROR uploading to Phoenix: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a BLS eval CSV dataset to Phoenix."
    )
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="List registered datasets.")

    # upload (default command when --dataset-name is given)
    parser.add_argument("--list", action="store_true", help="List registered datasets.")
    parser.add_argument("--dataset-name", metavar="NAME", help="Dataset to upload.")
    parser.add_argument(
        "--phoenix-name",
        metavar="NAME",
        help="Name to use in Phoenix (defaults to --dataset-name).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the CSV without uploading.",
    )

    args = parser.parse_args()

    if args.list or args.command == "list":
        cmd_list(args)
    elif args.dataset_name:
        cmd_upload(args)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
