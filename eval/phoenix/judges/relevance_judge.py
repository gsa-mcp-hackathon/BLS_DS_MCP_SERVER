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

IN-SCOPE topics (the agent should answer these):
- BLS time-series data: unemployment rates, payroll employment, CPI,
  labor force participation, job openings, producer prices, wages,
  productivity, import/export price indexes, employment cost indexes
- BLS survey descriptions and series metadata
- BLS series ID construction, decoding, and validation
- Historical observations from BLS published data

OUT-OF-SCOPE topics (the agent should politely decline these):
- Predictions, forecasts, or future values
- Investment advice or financial recommendations
- Economic indicators NOT published by BLS (e.g. GDP published by BEA,
  Federal Reserve interest rates, stock market data)
- Personnel, organizational, or political information
- Any question that cannot be answered using BLS statistical data

Question asked:
{input}

Agent's answer:
{output}

Decide whether the agent's response is WITHIN_SCOPE or OUT_OF_SCOPE.

Rules:
- If the question is in-scope AND the agent answered it (even if wrong),
  return within_scope.
- If the question is out-of-scope AND the agent politely declined or
  redirected to BLS data, return within_scope.
- If the question is in-scope AND the agent refused without good reason,
  return out_of_scope.
- If the question is out-of-scope AND the agent answered it as if it
  were a BLS question (e.g. made up a prediction, gave investment advice),
  return out_of_scope.

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
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
        temperature=0,
    )
    label = response.choices[0].message.content.strip().lower()
    # Normalise to one of the two expected labels
    if "out_of_scope" in label or "out of scope" in label:
        return "out_of_scope"
    return "within_scope"
