"""Structured logging configuration with secret redaction.

Every API call and tool invocation is logged as structured JSON. A processor
redacts any token-shaped values (access/refresh tokens, Authorization headers)
so secrets never reach the logs.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

# Keys whose values must always be redacted from log events.
_SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "client_secret",
    "token_encryption_key",
    "bearer",
    "password",
    "secret",
}

_REDACTED = "***REDACTED***"


def _redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values from a structlog event dict (shallow + headers)."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = _REDACTED

    # Redact common header containers if present.
    headers = event_dict.get("headers")
    if isinstance(headers, dict):
        event_dict["headers"] = {
            k: (_REDACTED if k.lower() in _SENSITIVE_KEYS else v) for k, v in headers.items()
        }
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging to emit redacted JSON logs.

    Args:
        level: Minimum log level name (e.g. ``INFO``, ``DEBUG``).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=numeric_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
