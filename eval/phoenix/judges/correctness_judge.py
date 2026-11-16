"""Correctness judge: match_expected_response.

Compares the agent's answer against a ground-truth reference.  Returns
"correct" when the core fact matches (allowing for formatting differences
such as units, surrounding prose, or extra context), and "incorrect"
otherwise.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from phoenix.evals import ClassificationEvaluator

load_dotenv()

_TEMPLATE = """
You are evaluating an AI assistant that answers questions about Bureau of
Labor Statistics (BLS) time-series data.

Question asked:
{input}

Agent's answer:
{output}

Expected answer (ground truth):
{reference}

Decide whether the agent's answer is CORRECT or INCORRECT.

Rules:
- A numeric value is correct if it matches the reference number, even if
  the agent includes units, percent signs, or surrounding context
  (e.g. "3.7 percent" is correct when the reference is "3.7").
- A series ID is correct if it matches exactly (case-insensitive).
- A survey name is correct if the key identifying words match
  (e.g. "Current Employment Statistics" matches "CES").
- "Yes" / "No" answers are correct only if they match the reference.
- If the agent refuses to answer or says the data is unavailable when
  the reference provides a concrete answer, mark INCORRECT.
- If the agent provides additional correct context beyond the reference,
  still mark CORRECT.

Return exactly one word: correct or incorrect.
""".strip()


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("JUDGE_MODEL", "claude_4_6_sonnet"),
        api_key=os.getenv("USAI_API_KEY", ""),
        base_url=os.getenv("USAI_BASE_URL", ""),
        temperature=0.0,
    )


def match_expected_response(
    input: dict,  # noqa: A002
    output: dict,
    expected: dict,
) -> str:
    """LLM-as-judge correctness evaluator for Phoenix run_experiment.

    Args:
        input:    Phoenix input dict — must contain key "query".
        output:   Phoenix output dict — must contain key "output".
        expected: Phoenix expected dict — must contain key "responses".

    Returns:
        "correct" or "incorrect".
    """
    evaluator = ClassificationEvaluator(
        llm=_make_llm(),
        template=_TEMPLATE,
        choices={"correct": 1, "incorrect": 0},
    )
    result = evaluator.evaluate(
        input=input.get("query", ""),
        output=output.get("output", ""),
        reference=expected.get("responses", ""),
    )
    return result[0]
