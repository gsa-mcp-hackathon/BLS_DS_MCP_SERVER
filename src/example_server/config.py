"""Server configuration loaded from environment variables or a .env file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP server settings. Override any field via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Transport ─────────────────────────────────────────────────────────────
    # "stdio"           — local subprocess (Claude Desktop / Claude Code / Zed)
    # "streamable-http" — remote HTTP server (containers, cloud deploys)
    #
    # NOTE: app.py also auto-selects HTTP when a platform injects DATABRICKS_APP_PORT
    # or PORT, so you usually do NOT need to set this on a cloud host.
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # ── BLS Public Data API ───────────────────────────────────────────────────
    # Optional registration key for the BLS Public Data API v2.
    # When set, the server automatically uses v2 (higher limits).
    # When absent, the server uses v1 (unauthenticated, lower limits).
    # Register at: https://data.bls.gov/registrationEngine/
    # Never commit a real key — set BLS_API_KEY in the environment or .env.
    bls_api_key: SecretStr = SecretStr("")


settings = Settings()

# ── BLS API endpoint base URLs ────────────────────────────────────────────────
BLS_V1_BASE_URL = "https://api.bls.gov/publicAPI/v1/"
BLS_V2_BASE_URL = "https://api.bls.gov/publicAPI/v2/"

# ── BLS API per-version limits ────────────────────────────────────────────────
# v1 (unauthenticated):  25 series/request, 10-year range, 25 requests/day
# v2 (registered key):   50 series/request, 20-year range, 500 requests/day
BLS_V1_MAX_SERIES = 25
BLS_V1_MAX_YEAR_RANGE = 10
BLS_V1_DAILY_LIMIT = 25

BLS_V2_MAX_SERIES = 50
BLS_V2_MAX_YEAR_RANGE = 20
BLS_V2_DAILY_LIMIT = 500


# ── Ambiguity policy constants ────────────────────────────────────────────────
# Per-survey seasonal-adjustment defaults.  These mirror SAFE_DEFAULTS in
# ambiguity.py and are the single authoritative source imported by both modules.
SEASONAL_DEFAULTS: dict[str, str] = {
    "CE": "S",  # CE headline is seasonally adjusted
    "LA": "S",  # LA national/state headline is SA
    "LN": "S",  # LN CPS headline series are SA
    "JT": "S",  # JOLTS headline figures are SA
    "PR": "S",  # Productivity headline is SA
    "CU": "U",  # CPI-U NSA is the reference series (CUUR0000SA0)
    "CW": "U",  # CPI-W NSA is the COLA reference
    "SM": "U",  # State/metro data is predominantly NSA
    "MP": "U",  # Multifactor productivity is annual, NSA
    "EI": "U",  # International price — NSA
    "WP": "U",  # PPI commodity — NSA
    "CI": "S",  # ECEC headline is SA
}

# Feature flags — set via environment variables or .env to change behavior.
CLARIFY_ON_MEASURE_AMBIGUITY: bool = True
"""Block BLS API call when eligible candidates have different measure types."""
CLARIFY_ON_GEOGRAPHY_AMBIGUITY: bool = True
"""Ask for clarification when multiple geographic areas match the query."""


def get_bls_api_version() -> str:
    """Return the BLS API version to use based on the configured key.

    Returns "v2" when BLS_API_KEY is configured (non-empty), "v1" otherwise.
    The key value is never read outside of the HTTP client that injects it.
    """
    return "v2" if settings.bls_api_key.get_secret_value() else "v1"
