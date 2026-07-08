"""Central configuration and verifiable placeholder constants.

This module is the single source of truth for every externally-defined
identifier the server depends on: OAuth endpoints, API base URLs, scopes, and
endpoint paths. Nothing here is guaranteed correct — every value that must be
confirmed against https://developer.webex.com is annotated with ``# VERIFY`` or
``# TODO`` so it can be found with a simple grep before going live.

The Config API and the Reporting/Search API are DISTINCT families with separate
base URLs and scopes. Keep them separate; do not merge them.

Secrets (client id/secret, encryption key) are NEVER hardcoded here — they are
loaded from the environment / ``.env`` via :class:`Settings`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables / ``.env``.

    All fields are sourced from the environment. Secret values must be provided
    by the operator and are never committed to source control.
    """

    model_config = SettingsConfigDict(
        env_prefix="WXCC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- OAuth client credentials (secrets; supplied via env only) ----------
    client_id: str = Field(default="", description="OAuth client id.")
    client_secret: str = Field(default="", description="OAuth client secret.")
    redirect_uri: str = Field(
        default="http://localhost:8765/oauth/callback",
        description="Registered OAuth redirect URI.",
    )

    # --- Org context --------------------------------------------------------
    org_id: str = Field(default="", description="Default org id (optional).")

    # --- Personal access token (dev / bypass mode) --------------------------
    # If set, the OAuth broker uses this token directly and skips the full
    # Authorization Code flow. Obtain from https://developer.webex.com or from
    # a WxCC integration token with cjp:config_read + cjp:analytics_read scopes.
    access_token: str = Field(
        default="",
        description="Static access token (bypasses OAuth). Leave blank in production.",
    )

    # --- API base URLs (two distinct families) ------------------------------
    config_api_base: str = Field(
        default="https://api.wxcc-REGION.cisco.com",  # VERIFY
        description="Base URL for the WxCC Admin/Config API family. VERIFY.",
    )
    reporting_api_base: str = Field(
        default="https://api.wxcc-REGION.cisco.com",
        description="Base URL for the WxCC Reporting/Search API family. VERIFY.",
    )

    # --- OAuth endpoints ----------------------------------------------------
    oauth_authorize_url: str = Field(
        default="https://webexapis.com/v1/authorize",  # VERIFY
        description="OAuth authorization endpoint. VERIFY.",
    )
    oauth_token_url: str = Field(
        default="https://webexapis.com/v1/access_token",  # VERIFY
        description="OAuth token endpoint. VERIFY.",
    )

    # --- OAuth scopes (space-separated) -------------------------------------
    config_api_scopes: str = Field(
        default="cjp:config_read",  # TODO VERIFY
        description="Scopes granting Config API reads.",
    )
    reporting_api_scopes: str = Field(
        default="cjp:analytics_read",  # TODO VERIFY
        description="Scopes granting Reporting/Search API reads.",
    )

    # --- Token store --------------------------------------------------------
    token_store_dir: str = Field(
        default=".tokens", description="Directory for encrypted per-session tokens."
    )
    token_encryption_key: str = Field(
        default="",
        description="Base64 urlsafe 32-byte key for encrypting tokens at rest.",
    )

    # --- HTTP client tuning -------------------------------------------------
    http_timeout_seconds: float = Field(default=30.0)
    http_max_retries: int = Field(default=4)

    # --- Logging ------------------------------------------------------------
    log_level: str = Field(default="INFO")

    @property
    def combined_scopes(self) -> str:
        """Return the union of Config and Reporting scopes, space-separated.

        A brokered token must cover BOTH families so a single diagnostic
        session can read config and reporting data without re-authorizing.
        """
        parts = f"{self.config_api_scopes} {self.reporting_api_scopes}".split()
        # Preserve order, drop duplicates.
        seen: dict[str, None] = {}
        for part in parts:
            seen.setdefault(part, None)
        return " ".join(seen)


# ---------------------------------------------------------------------------
# API FAMILIES
# ---------------------------------------------------------------------------
class ApiFamily:
    """Logical API families. Each maps to a distinct base URL + scope set."""

    CONFIG = "config"
    REPORTING = "reporting"


# ---------------------------------------------------------------------------
# ENDPOINT PATH CONSTANTS
#
# Every path below is a PLACEHOLDER. Confirm the exact path, path params, and
# query parameters against https://developer.webex.com before live use.
# Paths are relative to the base URL of their family.
# ---------------------------------------------------------------------------

# --- Config API family --------------------------------------------------------
# VERIFY against developer.webex.com
USERS_PATH = "/organization/{org_id}/user"  # VERIFY
USER_BY_ID_PATH = "/organization/{org_id}/user/{user_id}"  # VERIFY
USER_BY_EMAIL_QUERY_PARAM = "email"  # VERIFY (param name used to search by email)

TEAM_BY_ID_PATH = "/organization/{org_id}/team/{team_id}"  # VERIFY

QUEUE_BY_ID_PATH = "/organization/{org_id}/contact-service-queue/{queue_id}"  # VERIFY

SKILL_PROFILE_BY_ID_PATH = "/organization/{org_id}/skill-profile/{profile_id}"  # VERIFY

# The user's full config (teams, skill profile, agent profile, multimedia
# profile) may be assembled from the user record and related resources, or from
# a dedicated endpoint. VERIFY the correct source.
USER_CONFIG_PATH = "/organization/{org_id}/user/{user_id}"  # VERIFY

# --- Reporting / Search API family -------------------------------------------
# VERIFY against developer.webex.com
AGENT_STATE_HISTORY_PATH = "/organization/{org_id}/agent-state/search"  # VERIFY
AGENT_SESSION_PATH = "/organization/{org_id}/agent-session/search"  # VERIFY


# Mapping of endpoint constants to their owning family, used by the client to
# select the correct base URL. VERIFY membership as paths are confirmed.
ENDPOINT_FAMILY: dict[str, str] = {
    USERS_PATH: ApiFamily.CONFIG,
    USER_BY_ID_PATH: ApiFamily.CONFIG,
    USER_CONFIG_PATH: ApiFamily.CONFIG,
    TEAM_BY_ID_PATH: ApiFamily.CONFIG,
    QUEUE_BY_ID_PATH: ApiFamily.CONFIG,
    SKILL_PROFILE_BY_ID_PATH: ApiFamily.CONFIG,
    AGENT_STATE_HISTORY_PATH: ApiFamily.REPORTING,
    AGENT_SESSION_PATH: ApiFamily.REPORTING,
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
