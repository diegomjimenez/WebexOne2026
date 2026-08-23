"""Cross-cutting runtime for the MCP server — *read this second*.

`server.py` is deliberately kept to the two things a lab participant cares about:
**what tools exist** and **how one tool maps to a Webex call**. Everything that is
the *same* for every tool — session/client wiring, correlation ids, timing,
structured logging, error translation, and the elicitation/progress/sampling
helpers — lives here so it stays out of the entrypoint's reading path.

Nothing in this module changes MCP behaviour; it is the machinery `server.py`
leans on. The small public surface it exposes to `server.py`:

* :func:`get_client` / :func:`session_id` — resolve the per-session Webex client.
* :func:`run_tool` — run one tool call with correlated logging + error translation.
* :func:`should_commit` — the elicitation-backed write gate.
* :func:`emit_progress` — best-effort progress notifications.
* :func:`maybe_summarize` — optional LLM summary via sampling.

Observability is stderr-native structured logging (see the logging chapter of the
lab guide); in-protocol client logging was deprecated by MCP SEP-2577 (2026-07-28)
and is intentionally not used.
"""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from .api.client import WxccApiClient
from .auth.oauth import OAuthBroker
from .errors import WxccError
from .logging_config import (
    bind_request_context,
    get_logger,
    reset_request_context,
)
from .tools._common import translate_error

logger = get_logger(__name__)

_broker: OAuthBroker | None = None
_client: WxccApiClient | None = None


# ---------------------------------------------------------------------------
# Session + client wiring
# ---------------------------------------------------------------------------


def get_client() -> WxccApiClient:
    """Return the lazily-initialized broker-backed API client."""
    global _broker, _client
    if _broker is None:
        _broker = OAuthBroker()
    if _client is None:
        _client = WxccApiClient(_broker)
    return _client


def session_id(ctx: Context | None) -> str:
    """Derive a per-session id from the MCP context.

    Falls back to a stable local id for single-user stdio deployments. A remote
    multi-user deployment MUST map each MCP session to a distinct broker session.
    """
    if ctx is not None:
        for attr in ("client_id", "session_id"):
            value = getattr(ctx, attr, None)
            if value:
                return str(value)
        session = getattr(ctx, "session", None)
        if session is not None and getattr(session, "session_id", None):
            return str(session.session_id)
    return "local-stdio-session"


# ---------------------------------------------------------------------------
# Glass-box logging (stderr-native)
#
# Every tool invocation is narrated as one correlated story on the server-side
# structured log stream, so lab participants can troubleshoot by matching a
# short id across events:
#
#   stage      server event (structlog)
#   ---------  ----------------------------------------------
#   received   tool.received  (+ intent)
#   auth       using_static_access_token / …
#   api        wxcc_api_call / wxcc_api_retry
#   result     tool.result    (+ summary, elapsed_ms)
#   error      tool.error     (+ elapsed_ms)
#
# The correlation id is bound into structlog contextvars, so server-side records
# emitted downstream (API client, auth broker, tool impls) inherit it for free.
# The host (Cursor, Claude Desktop, Inspector) captures this stream from stderr.
# In-protocol client logging (notifications/message) is intentionally not used —
# it was deprecated by MCP SEP-2577 (2026-07-28).
# ---------------------------------------------------------------------------


def _new_request_id() -> str:
    """Return a short, human-readable correlation id (6 hex chars)."""
    return secrets.token_hex(3)


def _elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since ``start`` (perf counter), rounded."""
    return round((time.perf_counter() - start) * 1000, 1)


def _result_summary(payload: dict[str, Any]) -> str:
    """Build a short, human-readable summary of a tool result for the log."""
    if not isinstance(payload, dict):
        return "done"
    if "error" in payload:
        return str(payload["error"])
    if "total_returned" in payload:
        return f"{payload['total_returned']} item(s)"
    if payload.get("dry_run"):
        return "dry-run preview (not committed)"
    if payload.get("committed"):
        rid = payload.get("resource_id")
        return f"committed{f' ({rid})' if rid else ''}"
    if "to_create" in payload:
        return (
            f"{payload.get('to_create', 0)} create / "
            f"{payload.get('to_update', 0)} update / "
            f"{payload.get('to_delete', 0)} delete"
        )
    for key in ("address_book_id", "entry_id", "profile_id", "identifier", "id"):
        if payload.get(key):
            return f"{key}={payload[key]}"
    return "done"


async def run_tool(
    coro_factory: Any,
    ctx: Context | None,
    *,
    tool_name: str = "tool",
    intent: str = "",
) -> dict[str, Any]:
    """Execute a tool coroutine with correlated logging and error translation.

    Generates a correlation id, binds it so every downstream server-side log
    inherits it, emits the received/result/error stages to the stderr-native
    structured stream, and times the invocation. Typed errors are translated to
    plain language.

    ``coro_factory`` is a zero-arg callable (typically a ``lambda:``) that DEFERS
    the actual tool call so this helper can start the timer and bind the
    correlation id *before* the work runs.

    ``ctx`` is accepted for symmetry with the tool signatures but is not used for
    logging: in-protocol client logging was deprecated by MCP SEP-2577, so the
    lifecycle is observed via the structured events below (all sharing
    ``request_id``).
    """
    request_id = _new_request_id()
    tokens = bind_request_context(request_id=request_id, tool=tool_name)
    start = time.perf_counter()
    logger.info("tool.received", tool=tool_name, intent=intent)
    try:
        result = await coro_factory()
        payload = result.model_dump(mode="json")
        elapsed_ms = _elapsed_ms(start)
        logger.info(
            "tool.result",
            tool=tool_name,
            summary=_result_summary(payload),
            elapsed_ms=elapsed_ms,
        )
        return payload
    except (WxccError, ValueError) as exc:
        # WxccError → translated plain language; ValueError → E.164/schema message.
        message = translate_error(exc) if isinstance(exc, WxccError) else str(exc)
        elapsed_ms = _elapsed_ms(start)
        logger.warning("tool.error", tool=tool_name, elapsed_ms=elapsed_ms, error=message)
        return {"error": message}
    finally:
        reset_request_context(tokens)


# ---------------------------------------------------------------------------
# MCP primitive helpers (elicitation / progress / sampling)
#
# Every helper is defensive: MCP clients differ in which primitives they
# support, so unsupported calls degrade gracefully instead of crashing a tool.
# ---------------------------------------------------------------------------


class _ApproveWrite(BaseModel):
    """Schema for the elicited write-confirmation response."""

    approve: bool = Field(description="Approve and commit this write action?")


async def emit_progress(
    ctx: Context | None, progress: float, total: float, message: str | None = None
) -> None:
    """Send a progress notification; no-op if unsupported."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(progress=progress, total=total, message=message)
    except TypeError:
        try:
            await ctx.report_progress(progress, total)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


async def should_commit(ctx: Context | None, summary: str, confirm_flag: bool) -> bool:
    """Decide whether a write should commit.

    Prefers interactive elicitation. The user clicking "Accept" in the
    elicitation dialog is treated as sufficient approval — some clients
    (e.g. Codex) do not populate the schema data fields, so requiring both
    ``action=="accept"`` AND ``data.approve==True`` caused false negatives.

    If the client does not support elicitation (or it errors), falls back to
    the explicit ``confirm`` argument so the tool still works — and stays safe
    by defaulting to *not* committing.
    """
    if ctx is not None:
        try:
            result = await ctx.elicit(
                message=f"Confirm write action: {summary}", schema=_ApproveWrite
            )
            action = getattr(result, "action", None)
            if action == "accept":
                return True
            if action in ("decline", "cancel"):
                return False
        except Exception:  # noqa: BLE001 - fall back to the confirm flag
            pass
    return bool(confirm_flag)


async def maybe_summarize(ctx: Context | None, findings: dict[str, Any]) -> str | None:
    """Optionally ask the client's LLM to summarise a sync result (sampling).

    Fully guarded: returns ``None`` if sampling is unavailable or errors, in
    which case callers use their own deterministic summary.
    """
    if ctx is None:
        return None
    try:
        from mcp.types import SamplingMessage, TextContent

        session = getattr(ctx, "session", None)
        create_message = getattr(session, "create_message", None)
        if create_message is None:
            return None
        prompt = (
            "In one or two sentences, summarise this WxCC address book sync "
            f"result for an administrator:\n{json.dumps(findings, indent=2)}"
        )
        result = await create_message(
            messages=[SamplingMessage(role="user", content=TextContent(type="text", text=prompt))],
            max_tokens=200,
        )
        content = getattr(result, "content", None)
        text = getattr(content, "text", None)
        return str(text) if text else None
    except Exception:  # noqa: BLE001 - sampling is optional
        return None
