"""Per-session OAuth 2.0 token broker.

The broker acquires, stores (encrypted, per session), and refreshes access
tokens on behalf of each MCP session. Tokens are NEVER returned to the model or
included in tool outputs — only :meth:`OAuthBroker.get_valid_token` returns a
raw token, and it is intended solely for the API client's ``Authorization``
header.

Security properties:
  * Tokens are stored per ``session_id`` and encrypted at rest (Fernet).
  * One session cannot read another session's token.
  * Expired access tokens are refreshed automatically.

The exact Webex/WxCC OAuth endpoints and scopes are supplied via ``config.py``
placeholders and MUST be verified against https://developer.webex.com.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from cryptography.fernet import Fernet, InvalidToken

from ..config import Settings, get_settings
from ..errors import AuthError
from ..logging_config import get_logger

logger = get_logger(__name__)

# Refresh a token this many seconds before its actual expiry, to avoid races.
_EXPIRY_SKEW_SECONDS = 60


@dataclass
class TokenSet:
    """A brokered set of OAuth tokens for one session.

    This object stays server-side. It is never serialized into tool output.
    """

    access_token: str
    refresh_token: str | None = None
    expires_at: float = 0.0  # epoch seconds
    scopes: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def is_expired(self, skew: int = _EXPIRY_SKEW_SECONDS) -> bool:
        """Return True if the access token is expired (within ``skew`` seconds)."""
        return time.time() >= (self.expires_at - skew)

    def to_json(self) -> str:
        """Serialize to JSON for encrypted storage."""
        return json.dumps(
            {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.expires_at,
                "scopes": self.scopes,
                "extra": self.extra,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> TokenSet:
        """Deserialize from stored JSON."""
        data = json.loads(raw)
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=data.get("expires_at", 0.0),
            scopes=data.get("scopes", ""),
            extra=data.get("extra", {}),
        )


class EncryptedTokenStore:
    """Per-session token store, encrypted at rest with Fernet.

    Each session's token is written to its own file, encrypted with a symmetric
    key. Reads are keyed by ``session_id`` so one session can never read
    another's token. If no persistence directory/key is configured, an
    in-memory-only fallback is used (tokens do not survive restart).
    """

    def __init__(self, key: str | None, store_dir: str | None) -> None:
        """Initialize the store with an encryption key and optional directory."""
        self._lock = threading.Lock()
        self._memory: dict[str, bytes] = {}
        self._dir: Path | None = Path(store_dir) if store_dir else None
        self._fernet = self._build_fernet(key)
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _build_fernet(key: str | None) -> Fernet:
        """Build a Fernet cipher from the configured key, or an ephemeral one."""
        if key:
            try:
                # Accept a urlsafe-base64 32-byte key (a Fernet key).
                Fernet(key.encode())
                return Fernet(key.encode())
            except (ValueError, TypeError):
                # Accept a raw base64 32-byte secret and adapt it to a Fernet key.
                try:
                    raw = base64.urlsafe_b64decode(key)
                    return Fernet(base64.urlsafe_b64encode(raw[:32].ljust(32, b"0")))
                except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
                    raise AuthError("Invalid token encryption key configured.") from exc
        # No key configured: generate an ephemeral, process-local key.
        logger.warning("no_token_encryption_key_configured", fallback="ephemeral in-memory key")
        return Fernet(Fernet.generate_key())

    def _path_for(self, session_id: str) -> Path | None:
        if self._dir is None:
            return None
        # Session ids are namespaced by an opaque, filesystem-safe digest.
        safe = base64.urlsafe_b64encode(session_id.encode()).decode().rstrip("=")
        return self._dir / f"{safe}.token"

    def save(self, session_id: str, token_set: TokenSet) -> None:
        """Encrypt and store the token set for a session."""
        blob = self._fernet.encrypt(token_set.to_json().encode())
        with self._lock:
            path = self._path_for(session_id)
            if path is not None:
                path.write_bytes(blob)
                os.chmod(path, 0o600)
            else:
                self._memory[session_id] = blob

    def load(self, session_id: str) -> TokenSet | None:
        """Load and decrypt the token set for a session, if present."""
        with self._lock:
            path = self._path_for(session_id)
            if path is not None:
                if not path.exists():
                    return None
                blob = path.read_bytes()
            else:
                blob = self._memory.get(session_id)  # type: ignore[assignment]
                if blob is None:
                    return None
        try:
            return TokenSet.from_json(self._fernet.decrypt(blob).decode())
        except InvalidToken as exc:
            raise AuthError("Stored token could not be decrypted.") from exc

    def delete(self, session_id: str) -> None:
        """Remove a session's stored token."""
        with self._lock:
            path = self._path_for(session_id)
            if path is not None and path.exists():
                path.unlink()
            self._memory.pop(session_id, None)


class OAuthBroker:
    """Brokers OAuth tokens for MCP sessions."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the broker with settings and an encrypted token store."""
        self._settings = settings or get_settings()
        self._store = EncryptedTokenStore(
            key=self._settings.token_encryption_key,
            store_dir=self._settings.token_store_dir,
        )

    # -- Authorization Code flow --------------------------------------------

    def build_authorization_url(self, session_id: str, state: str) -> str:
        """Build the authorization URL a user visits to grant access.

        The token must cover BOTH the Config and Reporting/Search scopes.

        NOTE: The authorization endpoint and scope strings come from
        ``config.py`` and MUST be verified against developer.webex.com.
        """
        params = httpx.QueryParams(
            {
                "response_type": "code",
                "client_id": self._settings.client_id,
                "redirect_uri": self._settings.redirect_uri,
                "scope": self._settings.combined_scopes,  # both families
                "state": state,
            }
        )
        # TODO: VERIFY authorization endpoint / parameter names against developer.webex.com.
        return f"{self._settings.oauth_authorize_url}?{params}"

    async def exchange_code(self, session_id: str, code: str) -> None:
        """Exchange an authorization code for tokens and store them per session.

        NOTE: The token endpoint and request shape come from ``config.py`` and
        MUST be verified against developer.webex.com.
        """
        # TODO: VERIFY token endpoint, grant params, and response fields.
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._settings.redirect_uri,
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }
        token_set = await self._request_token(payload)
        self._store.save(session_id, token_set)
        logger.info("oauth_code_exchanged", session_id=session_id)

    async def get_valid_token(self, session_id: str) -> str:
        """Return a live access token for a session, refreshing if needed.

        If ``WXCC_ACCESS_TOKEN`` is set in the environment / ``.env``, it is
        used directly (personal-access-token / dev mode) and the OAuth store is
        bypassed entirely.  This avoids the browser-based authorization code
        flow for local development or when a long-lived token is available.

        Raises:
            AuthError: If the session has no token or refresh fails.
        """
        pat = self._settings.access_token
        if pat:
            logger.info("using_static_access_token", session_id=session_id)
            return pat

        token_set = self._store.load(session_id)
        if token_set is None:
            raise AuthError(
                "Not authorized: this session must complete the Webex OAuth sign-in before "
                "WxCC data can be read."
            )
        if token_set.is_expired():
            token_set = await self._refresh(session_id, token_set)
        return token_set.access_token

    async def _refresh(self, session_id: str, token_set: TokenSet) -> TokenSet:
        """Refresh an expired access token using the stored refresh token."""
        if not token_set.refresh_token:
            raise AuthError("Access token expired and no refresh token is available.")
        # TODO: VERIFY refresh grant params/response against developer.webex.com.
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": token_set.refresh_token,
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
        }
        try:
            refreshed = await self._request_token(payload)
        except httpx.HTTPError as exc:
            raise AuthError("Failed to refresh access token.") from exc
        # Carry the prior refresh token forward if the IdP did not return a new one.
        if not refreshed.refresh_token:
            refreshed.refresh_token = token_set.refresh_token
        self._store.save(session_id, refreshed)
        logger.info("oauth_token_refreshed", session_id=session_id)
        return refreshed

    async def _request_token(self, payload: dict[str, str]) -> TokenSet:
        """POST to the token endpoint and parse the response into a TokenSet."""
        async with httpx.AsyncClient(timeout=self._settings.http_timeout_seconds) as client:
            resp = await client.post(self._settings.oauth_token_url, data=payload)
        if resp.status_code != 200:
            # Do not log the response body; it may contain sensitive material.
            raise AuthError(f"Token endpoint returned HTTP {resp.status_code}.")
        data = resp.json()
        # TODO: VERIFY response field names (expires_in, scope, etc.).
        expires_in = float(data.get("expires_in", 0))
        return TokenSet(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=time.time() + expires_in,
            scopes=data.get("scope", ""),
        )
