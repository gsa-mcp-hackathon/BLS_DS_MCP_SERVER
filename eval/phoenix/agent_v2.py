"""agent_v2.py — OrchestrateAgentV2: same interface as agent.py but uses the
/v1/orchestrate/runs/stream SSE endpoint instead of
/v1/orchestrate/{id}/chat/completions.

Benefits over agent.py:
- Captures tool_calls from run.step.delta events (name, args, tool_call_id)
- Captures tool responses from run.step.delta events (name, output)
- Assembles the final answer from message.delta chunks
- Returns a RunResult dataclass with both the answer text and tool call metadata

Usage (standalone smoke test):
    uv run agent_v2.py

Usage (from run_experiment.py or run_multi_eval.py):
    agent = OrchestrateAgentV2()
    agent.initialize()
    task = agent.create_experiment_task()
    # task(example) -> str   (same interface as agent.py)
    # agent.last_run_tool_calls -> list[dict]  (populated after each call)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register as phoenix_register

logger = logging.getLogger(__name__)

_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
_STREAM_PATH = "/v1/orchestrate/runs/stream"
_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_system_prompt(version: str) -> str:
    prompt_path = _PROMPTS_DIR / f"system_prompt_{version}.txt"
    if not prompt_path.exists():
        logger.warning("System prompt file not found: %s", prompt_path)
        return ""
    return prompt_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Result of a single agent invocation via the streaming runs endpoint."""

    answer: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_responses: list[dict[str, Any]] = field(default_factory=list)

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class OrchestrateError(RuntimeError):
    """Sanitized error — never includes bearer token or API key."""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class OrchestrateAgentV2:
    """Agent under test using the /v1/orchestrate/runs/stream SSE endpoint.

    Provides the same public interface as OrchestrateAgent in agent.py so it
    can be used as a drop-in replacement in run_multi_eval.py.

    Required env vars:
        ORCHESTRATE_BASE_URL   e.g. https://ca-tor.watson-orchestrate.cloud.ibm.com
        ORCHESTRATE_AGENT_ID   UUID of the deployed agent
        IBM_CLOUD_API_KEY      IBM Cloud API key for IAM token exchange
    """

    def __init__(self, system_prompt_version: str = "v1") -> None:
        # Resolve .env from the repo root (two levels up from eval/phoenix/).
        # load_dotenv() without an argument searches upward from cwd, which
        # may not reach the repo root when called from a Jupyter kernel.
        _repo_root = Path(__file__).parent.parent.parent
        load_dotenv(_repo_root / ".env", override=False)
        load_dotenv()  # also honour a local .env if present in cwd
        self._base_url: str = os.environ["ORCHESTRATE_BASE_URL"].rstrip("/")
        self._agent_id: str = os.environ["ORCHESTRATE_AGENT_ID"]
        self._api_key: str = os.environ["IBM_CLOUD_API_KEY"]
        self._system_prompt_version = system_prompt_version
        self._system_prompt: str = _load_system_prompt(system_prompt_version)
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0
        # Populated after each run() call — read by create_experiment_task
        self.last_run_result: RunResult | None = None

    # ------------------------------------------------------------------
    # IAM token exchange (identical to agent.py)
    # ------------------------------------------------------------------

    async def _get_iam_token(self) -> str:
        if self._cached_token and time.time() < self._token_expires_at - 60:
            return self._cached_token
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.post(
                _IAM_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self._api_key,
                },
            )
            if resp.status_code != 200:
                raise OrchestrateError(
                    f"IAM token exchange failed with HTTP {resp.status_code}. "
                    "Check IBM_CLOUD_API_KEY."
                )
            body = resp.json()
        self._cached_token = body["access_token"]
        self._token_expires_at = float(body.get("expiration", time.time() + 3600))
        return self._cached_token

    # ------------------------------------------------------------------
    # SSE stream parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_sse_events(raw_lines: list[str]) -> list[dict]:
        """Parse raw SSE lines into a list of {event, data} dicts."""
        events = []
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "event" in obj and "data" in obj:
                    events.append(obj)
            except (json.JSONDecodeError, ValueError):
                pass
        return events

    # ------------------------------------------------------------------
    # Agent call
    # ------------------------------------------------------------------

    async def run(self, query: str) -> RunResult:
        """Send a question to the Orchestrate streaming runs endpoint.

        Args:
            query: Natural-language question.

        Returns:
            RunResult with answer text, tool_calls, and tool_responses.

        Raises:
            OrchestrateError: on HTTP errors or unexpected response shapes.
        """
        token = await self._get_iam_token()
        url = self._base_url + _STREAM_PATH

        # Build message payload — system prompt injected as first message
        # when the runs/stream endpoint supports a messages list; otherwise
        # the prompt version is informational here (agent uses its own prompt).
        payload: dict[str, Any] = {
            "agent_id": self._agent_id,
            "message": {
                "role": "user",
                "content": query,
            },
        }

        result = RunResult()
        raw_lines: list[str] = []

        try:
            async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as resp:
                    if resp.status_code in (401, 403):
                        raise OrchestrateError(
                            f"Orchestrate returned HTTP {resp.status_code}. "
                            "Check ORCHESTRATE_AGENT_ID and IBM_CLOUD_API_KEY."
                        )
                    if resp.status_code != 200:
                        raise OrchestrateError(
                            f"Orchestrate returned HTTP {resp.status_code}."
                        )
                    async for line in resp.aiter_lines():
                        if line.strip():
                            raw_lines.append(line)
        except httpx.RequestError as exc:
            raise OrchestrateError(
                f"Network error reaching Orchestrate: {type(exc).__name__}"
            ) from None

        # ── Parse SSE events ───────────────────────────────────────────
        answer_chunks: list[str] = []

        for event in self._parse_sse_events(raw_lines):
            etype = event.get("event", "")
            data = event.get("data", {})

            if etype == "message.delta":
                # Accumulate streaming text chunks into the final answer
                for block in data.get("delta", {}).get("content", []):
                    if isinstance(block, dict) and block.get("response_type") == "text":
                        answer_chunks.append(block.get("text", ""))

            elif etype == "run.step.delta":
                # Extract tool calls and tool responses
                for step in data.get("delta", {}).get("step_details", []):
                    step_type = step.get("type", "")

                    if step_type == "tool_calls":
                        for tc in step.get("tool_calls", []):
                            result.tool_calls.append(
                                {
                                    "name": tc.get("name", ""),
                                    "args": tc.get("args", {}),
                                    "tool_call_id": tc.get("id", ""),
                                }
                            )

                    elif step_type == "tool_response":
                        result.tool_responses.append(
                            {
                                "name": step.get("name", ""),
                                "tool_call_id": step.get("tool_call_id", ""),
                                "output": step.get("content", ""),
                            }
                        )

        result.answer = "".join(answer_chunks)
        self.last_run_result = result
        return result

    # ------------------------------------------------------------------
    # Phoenix instrumentation (identical to agent.py)
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Register Phoenix OTLP tracer. Call once before running experiments."""
        project_name = os.getenv("PHOENIX_PROJECT_NAME", "bls-eval")
        endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        otlp_endpoint = endpoint.rstrip("/") + "/v1/traces"
        tracer_provider = phoenix_register(
            project_name=project_name,
            endpoint=otlp_endpoint,
            auto_instrument=True,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(
            "Phoenix instrumentation registered: project=%s endpoint=%s",
            project_name,
            endpoint,
        )

    # ------------------------------------------------------------------
    # Experiment task factory (same interface as agent.py)
    # ------------------------------------------------------------------

    def create_experiment_task(self):
        """Return a sync task closure for use with phoenix run_experiment.

        The closure returns the plain answer string (same as agent.py) so
        it is a drop-in replacement. Tool call data is accessible via
        agent.last_run_result after each call.
        """

        def task(example) -> str:
            query = example.input["query"]
            try:
                result = asyncio.run(self.run(query))
                return result.answer
            except OrchestrateError as exc:
                return f"[OrchestrateError] {exc}"

        return task


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------


def main() -> None:
    """Smoke test: ask one question, print the answer and tool calls."""
    logging.basicConfig(level=logging.INFO)
    agent = OrchestrateAgentV2()
    question = "What BLS series covers the national unemployment rate?"
    print(f"Question: {question}\n")
    try:
        result = asyncio.run(agent.run(question))
        print(f"Answer:\n{result.answer}\n")
        print(f"Tool calls ({result.tool_call_count}):")
        for tc in result.tool_calls:
            print(f"  {tc['name']}({tc['args']})")
        print(f"\nTool responses ({len(result.tool_responses)}):")
        for tr in result.tool_responses:
            preview = str(tr["output"])[:120].replace("\n", " ")
            print(f"  {tr['name']}: {preview}...")
    except OrchestrateError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
