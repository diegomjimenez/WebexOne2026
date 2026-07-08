"""Typed exception hierarchy for the WxCC MCP server.

These exceptions are raised at the API client / auth boundary and translated by
tools into plain-language, token-free messages. No exception here should ever
carry access tokens, refresh tokens, or raw Authorization headers.
"""

from __future__ import annotations


class WxccError(Exception):
    """Base class for all WxCC MCP server errors."""


class AuthError(WxccError):
    """Raised when a session is not authorized or a token cannot be obtained/refreshed.

    This indicates the session must (re)complete the OAuth flow. It never
    contains token material.
    """


class WxccApiError(WxccError):
    """Base class for errors returned by a WxCC API call.

    Attributes:
        status_code: The HTTP status code, if available.
        detail: A safe, human-readable description (no secrets).
        family: The API family involved (config or reporting), if known.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        detail: str | None = None,
        family: str | None = None,
    ) -> None:
        """Initialize the error with safe, token-free context."""
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or message
        self.family = family


class NotFoundError(WxccApiError):
    """Raised when a requested resource does not exist (HTTP 404)."""


class InsufficientPermissionsError(WxccApiError):
    """Raised when the caller lacks rights for the operation (HTTP 403).

    Tools translate this into a plain-language statement of what the caller does
    not have permission to do.
    """


class RateLimitError(WxccApiError):
    """Raised when the API is rate limiting and retries are exhausted (HTTP 429)."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize with the optional ``Retry-After`` hint, in seconds."""
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.retry_after = retry_after
