"""Relevance / scope judge: check_answer_scope.

Scores whether the agent answered an in-scope BLS question or correctly
refused an out-of-scope one.  No reference answer is needed.

Returns "within_scope" when the agent behaved appropriately, and
"out_of_scope" when it answered an out-of-scope question it should have
refused, or refused an in-scope question it should have answered.
"""

from __future__ import annotations

import os

import litellm
from dotenv import load_dotenv

load_dotenv()

_TEMPLATE = """You are evaluating an AI assistant that answers questions about Bureau of
Labor Statistics (BLS) time-series data.

IMPORTANT: BLS publishes historical data records. Questions asking about unemployment,
CPI, employment, or other BLS statistics for any date through 2025 are IN-SCOPE
historical data questions — they are NOT predictions or forecasts.

IN-SCOPE topics (the agent should answer these):
- BLS time-series data: unemployment rates, payroll employment, CPI,
  labor force participation, job openings, producer prices, wages,
  productivity, import/export price indexes, employment cost indexes
- BLS survey descriptions and series metadata
- BLS series ID construction, decoding, and validation
- Historical observations from BLS published data

OUT-OF-SCOPE topics (the agent should politely decline these):
- Predictions or forecasts about future values
- Investment advice or financial recommendations
- Economic indicators NOT published by BLS (e.g. GDP, Federal Reserve rates,
  stock market data)
- Personnel, organizational, or political information

Question asked:
{input}

Agent's answer:
{output}

Rules:
- In-scope question + agent answered it (even if wrong) -> within_scope
- Out-of-scope question + agent politely declined or redirected -> within_scope
- In-scope question + agent refused without good reason -> out_of_scope
- Out-of-scope question + agent answered it as if valid -> out_of_scope

Return exactly one of: within_scope or out_of_scope."""

_DEFAULT_JUDGE = "meta-llama/llama-3-3-70b-instruct"


def check_answer_scope(
    input: dict,  # noqa: A002
    output: str,
) -> str:
    """LLM-as-judge scope evaluator for Phoenix run_experiment.

    Args:
        input:  Phoenix input dict — must contain key "query".
        output: Plain-text answer string returned by the agent task.

    Returns:
        "within_scope" or "out_of_scope".
    """
    model_id = os.getenv("JUDGE_MODEL", _DEFAULT_JUDGE)
    prompt = _TEMPLATE.format(
        input=input.get("query", ""),
        output=output,
    )
    response = litellm.completion(
        model=f"watsonx/{model_id}",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator. Apply the rules carefully, "
                    "then on the last line write ONLY the label: "
                    "within_scope or out_of_scope."
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
    if "out_of_scope" in label or "out of scope" in label:
        return "out_of_scope"
    return "within_scope"
