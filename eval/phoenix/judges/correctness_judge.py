"""Correctness judge: match_expected_response.

Compares the agent's answer against a ground-truth reference.  Returns
"correct" when the core fact matches (allowing for formatting differences
such as units, surrounding prose, or extra context), and "incorrect"
otherwise.
"""

from __future__ import annotations

import os

import litellm
from dotenv import load_dotenv

load_dotenv()

_TEMPLATE = """You are evaluating an AI assistant that answers questions about Bureau of
Labor Statistics (BLS) time-series data.

IMPORTANT: BLS publishes historical data records. All questions about dates through
2025 refer to published historical data.

Question asked:
{input}

Agent's answer:
{output}

Expected answer (ground truth):
{reference}

Rules:
- Numeric: correct if the number matches the reference, regardless of units or
  surrounding context ("3.7 percent" is correct when reference is "3.7").
- Series ID: correct if it matches exactly (case-insensitive).
- Description / name: correct if the core identifying words match — extra
  qualifiers ("seasonally adjusted"), abbreviations in parentheses, or minor
  wording differences do NOT make an answer incorrect
  ("Current Employment Statistics" is correct when reference is
  "Current Employment Statistics (CES)", and vice-versa).
- Yes / No: correct only if they match the reference.
- If the agent refuses to answer when the reference provides a concrete answer,
  mark incorrect.
- If the agent gives additional correct context beyond the reference, mark correct.

Return exactly one word: correct or incorrect."""

_DEFAULT_JUDGE = "meta-llama/llama-3-3-70b-instruct"


def match_expected_response(
    input: dict,  # noqa: A002
    output: str,
    expected: dict,
) -> str:
    """LLM-as-judge correctness evaluator for Phoenix run_experiment.

    Args:
        input:    Phoenix input dict — must contain key "query".
        output:   Plain-text answer string returned by the agent task.
        expected: Phoenix expected dict — must contain key "responses".

    Returns:
        "correct" or "incorrect".
    """
    model_id = os.getenv("JUDGE_MODEL", _DEFAULT_JUDGE)
    prompt = _TEMPLATE.format(
        input=input.get("query", ""),
        output=output,
        reference=expected.get("responses", ""),
    )
    response = litellm.completion(
        model=f"watsonx/{model_id}",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator. Apply the rules carefully, "
                    "then on the last line write ONLY the label: "
                    "correct or incorrect."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=100,
        temperature=0,
    )
    # Use last non-empty line so the model can reason before labelling
    lines = [
        ln.strip().lower()
        for ln in response.choices[0].message.content.splitlines()
        if ln.strip()
    ]
    label = lines[-1] if lines else ""
    if "incorrect" in label:
        return "incorrect"
    return "correct"
