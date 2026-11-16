"""OrchestrateAgent — sends questions to the deployed gsa_ds_bls_agent via
the watsonx.ai deployments REST API and returns plain-text answers.

Replaces the MultiServerMCPClient stdio pattern used in local harnesses.
Orchestrate handles tool routing internally; only the final answer is visible.

Usage (standalone smoke test):
    python agent.py

Usage (from run_experiment.py):
    agent = OrchestrateAgent()
    await agent.initialize()
    task = agent.create_experiment_task()
    # pass task to phoenix run_experiment
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx
import phoenix as px
from dotenv import load_dotenv
from openinference.instrumentation.langchain import LangChainInstrumentor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IAM token exchange endpoint (IBM Cloud, all regions)
# ---------------------------------------------------------------------------
_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# BLS deployment chat endpoint template (watsonx.ai ML API v1)
_CHAT_PATH = "/ml/v1/deployments/{deployment_id}/text/chat"
_CHAT_VERSION = "2024-05-31"


class OrchestrateError(RuntimeError):
    """Sanitized error from the Orchestrate/watsonx.ai endpoint.

    Never includes the IAM bearer token or IBM Cloud API key.
    """


class OrchestrateAgent:
    """Agent under test: the deployed gsa_ds_bls_agent in IBM watsonx Orchestrate.

    Authenticates via IAM token exchange (IBM_CLOUD_API_KEY → bearer token),
    then POSTs questions to the watsonx.ai deployments chat endpoint.
    Tokens are cached and re-used until they have fewer than 60 seconds left,
    at which point a fresh token is fetched automatically.
    """

    def __init__(self, system_prompt_version: str = "v1") -> None:
        load_dotenv()
        self._base_url: str = os.environ["ORCHESTRATE_BASE_URL"].rstrip("/")
        self._deployment_id: str = os.environ["ORCHESTRATE_DEPLOYMENT_ID"]
        self._api_key: str = os.environ["IBM_CLOUD_API_KEY"]
        self._system_prompt_version = system_prompt_version
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # IAM token exchange
    # ------------------------------------------------------------------

    async def _get_iam_token(self) -> str:
        """Return a valid IAM bearer token, refreshing if needed."""
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
        # BLS tokens are valid for `expiration` seconds from epoch
        self._token_expires_at = float(body.get("expiration", time.time() + 3600))
        return self._cached_token

    # ------------------------------------------------------------------
    # Agent call
    # ------------------------------------------------------------------

    async def run(self, query: str) -> str:
        """Send a question to the deployed Orchestrate agent and return the answer.

        Args:
            query: Natural-language question to ask the agent.

        Returns:
            The agent's plain-text response string.

        Raises:
            OrchestrateError: on HTTP errors or unexpected response shapes.
                              Never includes the bearer token or API key.
        """
        token = await self._get_iam_token()
        url = (
            self._base_url
            + _CHAT_PATH.format(deployment_id=self._deployment_id)
            + f"?version={_CHAT_VERSION}"
        )

        payload: dict[str, Any] = {
            "messages": [{"role": "user", "content": query}],
        }

        try:
            async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise OrchestrateError(
                f"Network error reaching Orchestrate endpoint: {type(exc).__name__}"
            ) from None

        if resp.status_code in (401, 403):
            raise OrchestrateError(
                f"Orchestrate returned HTTP {resp.status_code}. "
                "Check ORCHESTRATE_DEPLOYMENT_ID and that the IAM key has access."
            )
        if resp.status_code != 200:
            raise OrchestrateError(f"Orchestrate returned HTTP {resp.status_code}.")

        try:
            body = resp.json()
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise OrchestrateError(
                f"Unexpected response shape from Orchestrate: {exc}"
            ) from None

    # ------------------------------------------------------------------
    # Phoenix instrumentation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Register Phoenix OTLP tracer and instrument LangChain.

        Call once before running experiments. Safe to call multiple times
        (Phoenix and LangChain instrumentation are idempotent).
        """
        project_name = os.getenv("PHOENIX_PROJECT_NAME", "bls-eval")
        endpoint = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
        otlp_endpoint = endpoint.rstrip("/") + "/v1/traces"

        tracer_provider = px.otel.register(
            project_name=project_name,
            endpoint=otlp_endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(
            "Phoenix instrumentation registered: project=%s endpoint=%s",
            project_name,
            endpoint,
        )

    # ------------------------------------------------------------------
    # Experiment task factory
    # ------------------------------------------------------------------

    def create_experiment_task(self):
        """Return a sync task closure for use with phoenix run_experiment.

        Phoenix experiments expect a synchronous callable with signature
        ``task(example) -> str``.  The closure calls asyncio.run() so the
        async agent can be driven from the sync Phoenix runner.
        """

        def task(example) -> str:
            query = example.input["query"]
            try:
                return asyncio.run(self.run(query))
            except OrchestrateError as exc:
                # Return the error as a string so the judge can score it
                # (it will score as incorrect / out_of_scope, surfacing failures)
                return f"[OrchestrateError] {exc}"

        return task


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------


def main() -> None:
    """Smoke test: ask one question and print the response."""
    logging.basicConfig(level=logging.INFO)
    agent = OrchestrateAgent()
    question = "What was the U.S. national unemployment rate in January 2024?"
    print(f"Question: {question}")
    try:
        answer = asyncio.run(agent.run(question))
        print(f"Answer:   {answer}")
    except OrchestrateError as exc:
        print(f"Error:    {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
