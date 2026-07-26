"""Structured logging configuration with secret redaction.

Every API call and tool invocation is logged as structured JSON. A processor
redacts any token-shaped values (access/refresh tokens, Authorization headers)
so secrets never reach the logs.
"""

from __future__ import annotations

import logging
import sys
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


class _TeeStream:
    """Write to multiple streams simultaneously (e.g. stderr + log file)."""

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, data: str) -> None:
        for s in self._streams:
            s.write(data)

    def flush(self) -> None:
        for s in self._streams:
            s.flush()


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


def configure_logging(level: str = "INFO", log_file: str = "") -> None:
    """Configure structlog + stdlib logging to emit redacted JSON logs.

    Args:
        level: Minimum log level name (e.g. ``INFO``, ``DEBUG``).
        log_file: Optional path to a log file. When non-empty, log events are
            also written to this file in append mode using the same JSON format
            and secret redaction as stderr. A warning is emitted to stderr and
            the file handler is skipped if the path is unwritable.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Determine the output stream for structlog events.
    # PrintLoggerFactory writes directly (not through the stdlib root logger),
    # so we tee to the log file at the stream level rather than via addHandler.
    log_stream: Any = sys.stderr
    if log_file:
        try:
            _file_obj = open(log_file, "a", encoding="utf-8")  # noqa: WPS515
            log_stream = _TeeStream(sys.stderr, _file_obj)
            # Also attach a FileHandler to the stdlib root logger so that
            # third-party library logs (httpx, asyncio, etc.) go to the file too.
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            logging.getLogger().addHandler(file_handler)
        except OSError as exc:
            logging.warning("log_file_unavailable: %s - %s", log_file, exc)

    logging.basicConfig(format="%(message)s", level=numeric_level, stream=sys.stderr)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=log_stream),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)


def bind_request_context(**values: Any) -> dict[str, Any]:
    """Bind per-invocation values (e.g. ``request_id``, ``tool``) to the log context.

    Because the structlog processor chain includes ``merge_contextvars``, every
    log record emitted *anywhere* downstream during this invocation — in the API
    client, the auth broker, and the tool implementations — is automatically
    stamped with these values. This is what lets a single correlation id thread
    through the entire server-side log stream without passing it explicitly.

    Returns:
        A mapping of key -> reset token, to be passed to
        :func:`reset_request_context` in a ``finally`` block so ids never leak
        between overlapping async invocations.
    """
    return structlog.contextvars.bind_contextvars(**values)


def reset_request_context(tokens: dict[str, Any]) -> None:
    """Reset context values previously bound with :func:`bind_request_context`."""
    try:
        structlog.contextvars.reset_contextvars(**tokens)
    except Exception:  # noqa: BLE001 - context teardown must never break a tool
        structlog.contextvars.clear_contextvars()
