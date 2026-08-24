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
* :func:`evaluate_write_gate` — the elicitation-backed write gate; consent comes
  from the user's accept/decline action, every decision is narrated as a
  ``write_gate`` event, and the returned decision tells the caller why a write
  previewed instead of applying.
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
from typing import Any, NamedTuple

from mcp.server.fastmcp import Context
from mcp.types import ClientCapabilities, ElicitationCapability

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


def new_request_id() -> str:
    """Return a short, human-readable correlation id (6 hex chars).

    Public because a write tool must mint the id *before* its write gate runs, so
    the gate decision and the tool's own lifecycle events share one id.
    """
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
    request_id: str | None = None,
    gate: WriteGateDecision | None = None,
) -> dict[str, Any]:
    """Execute a tool coroutine with correlated logging and error translation.

    Binds a correlation id so every downstream server-side log inherits it, emits
    the received/result/error stages to the stderr-native structured stream, and
    times the invocation. Typed errors are translated to plain language.

    ``coro_factory`` is a zero-arg callable (typically a ``lambda:``) that DEFERS
    the actual tool call so this helper can start the timer and bind the
    correlation id *before* the work runs.

    ``request_id`` lets a caller supply an id minted earlier — write tools do
    this so their gate decision and their lifecycle events correlate. One is
    generated when omitted.

    ``gate`` is the write gate's decision, supplied by mutating tools only. It is
    attached to the result here rather than inside each tool so that every write
    explains a block the same way; read tools pass nothing and are unaffected.

    ``ctx`` is accepted for symmetry with the tool signatures but is not used for
    logging: in-protocol client logging was deprecated by MCP SEP-2577, so the
    lifecycle is observed via the structured events below (all sharing
    ``request_id``).
    """
    request_id = request_id or new_request_id()
    tokens = bind_request_context(request_id=request_id, tool=tool_name)
    start = time.perf_counter()
    logger.info("tool.received", tool=tool_name, intent=intent)
    try:
        result = await coro_factory()
        payload = result.model_dump(mode="json")
        if gate is not None:
            payload = _apply_gate_feedback(payload, gate)
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


# The consent prompt asks the client to render an approve/refuse choice, not to
# collect data. Two constraints follow, and they pull in opposite directions:
#
# * **No required fields.** Clients differ in what they submit alongside an
#   ``accept`` — an empty object, no body at all, or keys the server never asked
#   for. With nothing required, every one of those is still a valid approval. An
#   earlier version required an ``approve`` boolean, which made the SDK reject
#   conforming clients' approvals and silently downgrade the write to a dry-run.
# * **At least one property.** A form with nothing in it may render with no way
#   to submit it, leaving dismissal as the only exit — and dismissal is
#   ``cancel``. ``acknowledge`` exists purely so the client has a control to
#   draw; the server never reads it, and an ``accept`` that omits it or sets it
#   to ``false`` is still an approval (consent is the action, never the body).
_CONSENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "title": "Confirm write action",
    "description": "Accept to apply this change, or decline for a dry-run preview instead.",
    "properties": {
        "acknowledge": {
            "type": "boolean",
            "title": "Apply this change",
            "description": "Accepting this prompt approves the write.",
            "default": True,
        }
    },
}

# Outcomes that represent a human answer. Everything else means we never managed
# to ask, which is the only situation where the ``confirm`` fallback applies.
_ANSWERED_OUTCOMES = frozenset({"accepted", "declined", "cancelled"})

# Keys clients conventionally use to report *their own* failure when refusing.
# The MCP spec defines ``cancel`` as "the user dismissed without choosing", but
# real clients also emit it for timeouts and internal faults, with the reason in
# the body. Recording these is the difference between "the user said no" and
# "the client broke" — the two look identical from the action alone.
_CLIENT_DETAIL_KEYS = ("error", "message", "reason")
_MAX_CLIENT_DETAIL = 256

# What the *caller* is told, keyed by outcome. Kept as one table so the wording
# cannot drift between tools, and composed entirely by the server: a tool result
# is fed to a language model, so client-supplied text must never be relayed into
# it. The client's own words go to the log above, which a human reads.
_CALLER_REASONS: dict[str, str] = {
    "declined": "The user declined this change when asked to approve it. Nothing was changed.",
    # A cancel is the one refusal that may not involve a person: some clients
    # declare elicitation support and then answer `cancel` themselves without ever
    # drawing a dialog. Such a caller is as stuck as one with no elicitation at all,
    # but it lands in the answered class where guidance is withheld — so the reason
    # names something for the *reader* to check. It deliberately stops short of
    # naming an argument to pass, which would hand the model a way to retry past
    # someone who genuinely refused (design D13).
    "cancelled": (
        "The approval prompt was dismissed, or the client answered on its own. "
        "Nothing was changed. If a prompt did not appear on screen, this client may "
        "not support approval prompts despite advertising them — the server log "
        "records how long the client took to answer."
    ),
    "unsupported": (
        "This client cannot ask the user to approve a write, so no approval was obtained."
    ),
    "error": "The approval request could not be completed, so no approval was obtained.",
}

# Offered only for the never-asked outcomes. After a refusal the same sentence
# would be an invitation to retry past a human, which is precisely the approval
# fatigue a write gate exists to prevent.
_RETRY_GUIDANCE = (
    "This client cannot prompt for approval. Once the user has confirmed in "
    "conversation, call this tool again with confirm=true to apply it."
)


class WriteGateDecision(NamedTuple):
    """The gate's answer, plus everything a caller needs to explain it.

    Returned rather than a bare boolean because the two audiences need different
    things: the tool needs ``commit``, while the model and user in the chat
    window — who never see the server's stderr — need to know *why* a write
    previewed and whether anything can be done about it.
    """

    commit: bool
    outcome: str
    reason: str | None
    guidance: str | None
    approved_by_user: bool

    def __bool__(self) -> bool:
        return self.commit


def build_gate_decision(outcome: str, *, commit: bool) -> WriteGateDecision:
    """Derive the caller-facing wording for one outcome.

    Guidance is keyed to the outcome *class*, not to the fact of being blocked:
    only ``unsupported`` and ``error`` mean nobody was asked, so only they can be
    told to fall back to ``confirm`` without overriding someone.
    """
    return WriteGateDecision(
        commit=commit,
        outcome=outcome,
        reason=_CALLER_REASONS.get(outcome),
        guidance=None if outcome in _ANSWERED_OUTCOMES else _RETRY_GUIDANCE,
        approved_by_user=outcome == "accepted",
    )


def _truncate(text: str) -> str:
    """Bound a client-supplied string so a verbose peer cannot flood the log."""
    return text if len(text) <= _MAX_CLIENT_DETAIL else text[:_MAX_CLIENT_DETAIL] + "..."


def _redact_refusal_body(body: Any) -> dict[str, Any]:
    """Summarise a refusal body for the log: names always, values by allow-list.

    Key *names* are chosen by the client, not typed by the user, so recording
    them is what makes an unfamiliar convention visible. Values are where user
    text could appear, so only the keys the ecosystem uses for machine-generated
    failure descriptions are disclosed. Never called for an ``accept``, whose
    body is the only one that can carry a genuine user submission.
    """
    if not isinstance(body, dict) or not body:
        return {}
    summary: dict[str, Any] = {"client_fields": sorted(str(key) for key in body)}
    for key in _CLIENT_DETAIL_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            summary["client_detail"] = _truncate(value)
            break
    return summary


def _client_identity(ctx: Context | None) -> dict[str, str]:
    """Identify the connected peer for the log, tolerating every absence.

    Purely diagnostic: in a lab where every attendee brings a different client,
    this turns an unreproducible report into a filterable field. It must never be
    the reason a gate decision fails to get narrated, so nothing here can raise.
    """
    unknown = {"client": "unknown", "protocol": "unknown"}
    session = getattr(ctx, "session", None)
    if session is None:
        return unknown
    try:
        params = getattr(session, "client_params", None)
        info = getattr(params, "clientInfo", None)
        name = getattr(info, "name", None)
        version = getattr(info, "version", None)
        protocol = getattr(params, "protocolVersion", None)
    except Exception:  # noqa: BLE001 - introspection failure is not a gate failure
        return unknown
    if not name:
        return unknown
    return {
        "client": f"{name} {version}".strip() if version else str(name),
        "protocol": str(protocol) if protocol else "unknown",
    }


def _apply_gate_feedback(payload: dict[str, Any], decision: WriteGateDecision) -> dict[str, Any]:
    """Attach the gate's decision to a tool result.

    Applied here rather than inside each tool so every mutating tool reports a
    block identically — the previous per-tool wording is exactly how ``sync``
    ended up as the one operation that offered no way forward.
    """
    payload["gate_outcome"] = decision.outcome
    if decision.reason:
        payload["gate_reason"] = decision.reason
    if decision.guidance:
        payload["next_step"] = decision.guidance
    if decision.commit and not decision.approved_by_user:
        payload["committed_without_approval"] = True
    if not decision.commit and decision.reason:
        payload["message"] = " ".join(filter(None, (decision.reason, decision.guidance)))
    return payload


class _GateDecision(NamedTuple):
    """How the consent request resolved, and the evidence for it.

    Keeping the outcome explicit (rather than collapsing straight to a boolean)
    is what lets the commit decision, the log event, and the tests all read from
    one value — so "the user declined" cannot be confused with "the client could
    not ask", which is exactly how the earlier defect stayed invisible.

    ``body`` is the client's raw response, carried here purely as evidence for
    the log; no code path reads it to decide consent.
    """

    outcome: str
    detail: str | None = None
    body: Any = None
    elicit_ms: float | None = None


def _client_supports_elicitation(session: Any) -> bool:
    """Return whether the peer negotiated the elicitation capability.

    Used to classify ``unsupported`` without issuing a request that is known to
    fail. This is a classification aid, not a security boundary: when the answer
    cannot be determined we optimistically try, and any resulting failure is
    caught and classified as ``error`` — which still fails closed.
    """
    check = getattr(session, "check_client_capability", None)
    if check is None:
        return True
    try:
        return bool(check(ClientCapabilities(elicitation=ElicitationCapability())))
    except Exception:  # noqa: BLE001 - inability to introspect is not a refusal
        return True


async def _ask_for_consent(ctx: Context | None, summary: str) -> _GateDecision:
    """Ask the user to approve one write, and classify the answer.

    Calls ``session.elicit_form`` directly rather than the ``ctx.elicit`` helper.
    That helper validates the client's response body against a Pydantic schema
    *before* returning, so an ``accept`` carrying an unexpected body shape raises
    instead of yielding a result — turning an approval into an exception the
    caller cannot recover. Consent is a three-state answer, so we read the raw
    ``action`` and never look at the body.
    """
    if ctx is None:
        return _GateDecision("unsupported", "no MCP context (non-interactive caller)")

    session = getattr(ctx, "session", None)
    if session is None:
        return _GateDecision("unsupported", "context exposes no session")

    elicit_form = getattr(session, "elicit_form", None)
    if elicit_form is None:
        return _GateDecision("unsupported", "session does not implement elicit_form")

    if not _client_supports_elicitation(session):
        return _GateDecision("unsupported", "client did not negotiate elicitation")

    # Timed around the await alone: this is the one measurement that shows
    # whether a human had the opportunity to answer. It deliberately stays
    # outside ``run_tool``'s timer, so ``elapsed_ms`` keeps meaning "work done"
    # rather than "time spent waiting for a person".
    start = time.perf_counter()
    try:
        result = await elicit_form(
            message=f"Confirm write action: {summary}",
            requestedSchema=_CONSENT_SCHEMA,
            related_request_id=getattr(ctx, "request_id", None),
        )
    except Exception as exc:  # noqa: BLE001 - any failure means consent is unknown
        return _GateDecision("error", f"{type(exc).__name__}: {exc}", None, _elapsed_ms(start))

    elapsed = _elapsed_ms(start)
    body = getattr(result, "content", None)
    action = getattr(result, "action", None)
    if action == "accept":
        return _GateDecision("accepted", None, body, elapsed)
    if action == "decline":
        return _GateDecision("declined", None, body, elapsed)
    if action == "cancel":
        return _GateDecision("cancelled", None, body, elapsed)
    return _GateDecision(
        "error", f"unrecognized elicitation action: {action!r}", body, elapsed
    )


async def evaluate_write_gate(
    ctx: Context | None,
    summary: str,
    confirm_flag: bool,
    *,
    request_id: str | None = None,
) -> WriteGateDecision:
    """Decide whether a write should commit — the shared human-in-the-loop gate.

    Consent is requested on every write, regardless of ``confirm_flag``: a model
    asked for a preview will pass ``confirm=False``, and that must not remove the
    user's opportunity to approve.

    * **Approved** — commit.
    * **Declined or cancelled** — do not commit, and do *not* consult
      ``confirm_flag``; an explicit refusal outranks a caller-supplied flag. This
      invariant is what makes it safe to tell an unaskable caller to pass
      ``confirm``: on a client that *can* prompt, doing so re-asks the user
      rather than bypassing them.
    * **Never asked** (no context, no elicitation support, or a failed attempt) —
      fall back to ``confirm_flag``, which keeps scripted and test callers
      working while still failing closed when it is unset.

    Returns the decision rather than a boolean so the calling tool can tell its
    caller *why* a write previewed. It stays usable in a boolean position via
    ``__bool__``.

    ``request_id`` correlates the emitted ``write_gate`` event with the rest of
    the invocation. It is passed in rather than read from contextvars because the
    gate deliberately runs *before* :func:`run_tool` starts its timer — a
    blocking user prompt inside the timed region would corrupt every
    ``elapsed_ms`` the server reports.
    """
    answer = await _ask_for_consent(ctx, summary)

    if answer.outcome == "accepted":
        commit = True
    elif answer.outcome in _ANSWERED_OUTCOMES:
        commit = False
    else:
        commit = bool(confirm_flag)

    # One event per evaluation. It carries the decision, how long the client took
    # to reach it, and who the client is — the three things needed to tell a
    # human's refusal from a client that answered on its own.
    event: dict[str, Any] = {
        "outcome": answer.outcome,
        "action": summary,
        "committed": commit,
        **_client_identity(ctx),
    }
    if answer.detail:
        event["reason"] = answer.detail
    if answer.elicit_ms is not None:
        event["elicit_ms"] = answer.elicit_ms
    if answer.outcome not in _ANSWERED_OUTCOMES:
        event["fallback_confirm"] = bool(confirm_flag)
    if answer.outcome != "accepted":
        # Only a refusal body is summarised; an approval's body is the one that
        # can hold text the user typed, and the gate has no use for it.
        event.update(_redact_refusal_body(answer.body))
    if request_id:
        event["request_id"] = request_id
    logger.info("write_gate", **event)

    return build_gate_decision(answer.outcome, commit=commit)


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
