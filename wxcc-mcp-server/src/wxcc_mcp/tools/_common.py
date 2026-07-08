"""Shared helpers for tool implementations.

Includes safe datetime parsing and translation of typed API errors into
plain-language, token-free messages suitable for returning to the model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..errors import (
    AuthError,
    InsufficientPermissionsError,
    NotFoundError,
    RateLimitError,
    WxccApiError,
)


def parse_dt(value: Any) -> datetime | None:
    """Parse a timestamp into a datetime, tolerating common shapes.

    Accepts ISO-8601 strings (with a trailing ``Z``) and epoch millis/seconds.
    Returns ``None`` when the value is missing or unparseable.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # Heuristic: treat large numbers as epoch millis. VERIFY units per API.
        seconds = value / 1000.0 if value > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def translate_error(exc: Exception) -> str:
    """Translate a typed error into a plain-language, token-free message."""
    if isinstance(exc, NotFoundError):
        return "Not found: the requested WxCC resource does not exist or is not visible to you."
    if isinstance(exc, InsufficientPermissionsError):
        return (
            "Permission denied: your account does not have rights to read this WxCC data. "
            "Ask an administrator to grant the appropriate read scope."
        )
    if isinstance(exc, RateLimitError):
        return "Rate limited: WxCC is throttling requests. Please retry shortly."
    if isinstance(exc, AuthError):
        return (
            "Not authorized: this session must complete the Webex OAuth sign-in before "
            "WxCC data can be read."
        )
    if isinstance(exc, WxccApiError):
        return f"WxCC API error: {exc.detail}"
    return "Unexpected error while contacting WxCC."
