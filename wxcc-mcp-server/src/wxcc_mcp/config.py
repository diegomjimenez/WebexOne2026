"""Central configuration and verifiable placeholder constants.

This module is the single source of truth for every externally-defined
identifier the server depends on: OAuth endpoints, the API base URL, scopes, and
endpoint paths. Nothing here is guaranteed correct — every value that must be
confirmed against https://developer.webex.com is annotated with ``# VERIFY`` or
``# TODO`` so it can be found with a simple grep before going live.

This lab is scoped to a SINGLE Webex Contact Center API family — the **Config
API** (`cjp:config_read` / `cjp:config_write`). Address Books, Address Book
Entries, Desktop Profiles, and Users all live here. There is no Reporting/Search
or Platform/People usage.

Secrets (client id/secret, encryption key) are NEVER hardcoded here — they are
loaded from the environment / ``.env`` via :class:`Settings`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The project root (the directory that contains ``.env``).  Resolved from this
# module's location so paths are stable regardless of the process working
# directory.  Claude Desktop (and other MCP clients) may start the server with
# a CWD that is unrelated to the project root, which would otherwise cause
# relative paths (``.env``, ``.tokens``) to be silently missed or created in
# the wrong place.
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_ENV_FILE = str(_PROJECT_ROOT / ".env")


def _resolve_path(value: str) -> str:
    """Resolve a possibly-relative path against the project root.

    Absolute paths and empty values are returned unchanged. Relative paths are
    anchored to the project root so they never depend on the process CWD.
    """
    if not value:
        return value
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(_PROJECT_ROOT / path)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables / ``.env``.

    All fields are sourced from the environment. Secret values must be provided
    by the operator and are never committed to source control.
    """

    model_config = SettingsConfigDict(
        env_prefix="WXCC_",
        env_file=_ENV_FILE,
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
    # a WxCC integration token with cjp:config_read + cjp:config_write scopes.
    access_token: str = Field(
        default="",
        description="Static access token (bypasses OAuth). Leave blank in production.",
    )

    # --- API base URL (single Config family) --------------------------------
    config_api_base: str = Field(
        default="https://api.wxcc-REGION.cisco.com",  # VERIFY
        description="Base URL for the WxCC Admin/Config API family. VERIFY.",
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
    # Address Book, Entry, and Desktop Profile management all require the Config
    # API read and write scopes. Reads use cjp:config_read; writes use
    # cjp:config_write.
    config_api_scopes: str = Field(
        default="cjp:config_read cjp:config_write",  # VERIFY
        description="Scopes granting Config API reads and writes.",
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
    log_file: str = Field(
        default="",
        description="Path to a log file. When set, log events are also written here as JSON.",
    )

    @field_validator("token_store_dir", "log_file")
    @classmethod
    def _anchor_to_project_root(cls, value: str) -> str:
        """Anchor relative filesystem paths to the project root.

        Ensures the token store and log file land in a deterministic location
        even when the server is launched with an unrelated working directory
        (e.g. by Claude Desktop, which ignores the ``cwd`` setting on Windows).
        """
        return _resolve_path(value)

    @property
    def combined_scopes(self) -> str:
        """Return the Config API scopes (the only family this server uses)."""
        seen: dict[str, None] = {}
        for part in self.config_api_scopes.split():
            seen.setdefault(part, None)
        return " ".join(seen)


# ---------------------------------------------------------------------------
# API FAMILIES
# ---------------------------------------------------------------------------
class ApiFamily:
    """Logical API families. This lab uses only the Config family."""

    CONFIG = "config"


# ---------------------------------------------------------------------------
# ENDPOINT PATH CONSTANTS
#
# Every path below is a PLACEHOLDER. Confirm the exact path, path params, and
# query parameters against https://developer.webex.com before live use.
# Paths are relative to the Config API base URL.
# ---------------------------------------------------------------------------

# --- Address Book (target v2; v1 is removed 2026-10-15) ----------------------
# Ref: https://developer.webex.com/webex-contact-center/docs/api/v1/address-book
ADDRESS_BOOKS_PATH = "/organization/{org_id}/address-book"  # VERIFY (v2)
ADDRESS_BOOK_BY_ID_PATH = "/organization/{org_id}/address-book/{address_book_id}"  # VERIFY (v2)

# --- Address Book Entries ----------------------------------------------------
# The entry sub-resource path shape (.../entry vs .../entries) is a VERIFY item.
ADDRESS_BOOK_ENTRIES_PATH = "/organization/{org_id}/address-book/{address_book_id}/entry"  # VERIFY
ADDRESS_BOOK_ENTRY_BY_ID_PATH = (
    "/organization/{org_id}/address-book/{address_book_id}/entry/{entry_id}"  # VERIFY
)
# Bulk save entries — VERIFY the exact path and payload shape (upsert vs replace).
ADDRESS_BOOK_ENTRIES_BULK_PATH = (
    "/organization/{org_id}/address-book/{address_book_id}/entry/bulk"  # VERIFY
)

# --- Desktop Profile (use Desktop Profile, NOT the superseded Agent Profile) --
# The addressBookId field carries the address-book assignment. Do NOT read or
# write the deprecated fields dialPlans / agentDNValidationCriteria /
# agentDNValidationCriterions (removed 2026-09-15).
DESKTOP_PROFILES_PATH = "/organization/{org_id}/agent-profile"  # VERIFY (desktop profile)
DESKTOP_PROFILE_BY_ID_PATH = "/organization/{org_id}/agent-profile/{profile_id}"  # VERIFY

# --- Users (agents) — read-only discovery of the profile↔agent mapping -------
USERS_PATH = "/organization/{org_id}/user"  # VERIFY
USER_BY_ID_PATH = "/organization/{org_id}/user/{user_id}"  # VERIFY


# Mapping of endpoint constants to their owning family, used by the client to
# select the correct base URL. Every path is in the Config family.
ENDPOINT_FAMILY: dict[str, str] = {
    ADDRESS_BOOKS_PATH: ApiFamily.CONFIG,
    ADDRESS_BOOK_BY_ID_PATH: ApiFamily.CONFIG,
    ADDRESS_BOOK_ENTRIES_PATH: ApiFamily.CONFIG,
    ADDRESS_BOOK_ENTRY_BY_ID_PATH: ApiFamily.CONFIG,
    ADDRESS_BOOK_ENTRIES_BULK_PATH: ApiFamily.CONFIG,
    DESKTOP_PROFILES_PATH: ApiFamily.CONFIG,
    DESKTOP_PROFILE_BY_ID_PATH: ApiFamily.CONFIG,
    USERS_PATH: ApiFamily.CONFIG,
    USER_BY_ID_PATH: ApiFamily.CONFIG,
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
