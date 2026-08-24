## Context

SEP-2577 deprecates MCP protocol logging (`logging/setLevel`, `notifications/message`) as of
the 2026-07-28 spec. This server uses it in two layers:

- `_emit_log(ctx, level, message)` → `ctx.<level>(message)` — the raw bridge to protocol
  logging (best-effort; guarded by `ctx is None` and `try/except`).
- `_glass_log(ctx, level, request_id, message, marker=...)` — wraps `_emit_log` with the
  `[request_id]` prefix and ASCII markers (`>`, `[OK]`, `[ERR]`) to narrate each tool lifecycle
  to the client.

`_run_tool` calls `_glass_log` at received/result/error, and ~10 write tools call `_emit_log`
directly to echo their commit decision. Every one of those events is *also* logged server-side
via structlog (`logger.info("tool.received", ...)`, `tool.result`, `tool.error`) with the same
`request_id` bound through contextvars.

The lab guide's Chapter 8 (added by the not-yet-archived `add-mcp-logging-chapter` change)
teaches protocol logging as a core primitive and frames the whole cockpit as "two streams, one
story." Step 0.8, per-chapter callouts, Chapter 9, and the appendix all lean on the
client-facing stream.

This change implements **G3 + C2**: teach the deprecation transition in the guide, and migrate
the code to stderr-native logging while preserving the correlation architecture.

## Goals / Non-Goals

**Goals:**
- Remove the deprecated protocol-logging layer (`_emit_log`, `_glass_log`, all
  `ctx.info/warning/error` calls) so the server emits no `MCPDeprecationWarning` for logging.
- Preserve full lifecycle observability through the existing structured server-side events
  (`tool.received`, `tool.result`, `tool.error`) and their `request_id` correlation.
- Keep `ctx.report_progress` (progress) and `ctx.elicit` (elicitation) — not deprecated.
- Rewrite the guide's logging chapter to teach the deprecation honestly and present the
  stderr-native model as the recommended replacement, including how each client surfaces
  captured stderr.
- Keep the guide internally consistent: Step 0.8 cockpit, per-chapter callouts, Chapter 9
  playbook, and the appendix all reflect the single-stream reality.

**Non-Goals:**
- Sampling migration (`_maybe_summarize` → `create_message`) — also deprecated by SEP-2577, but
  a separate feature handled in a later change.
- Changing the structlog configuration, redaction, or the `WXCC_LOG_LEVEL` filter — the
  server-side stream stays exactly as-is.
- Removing progress or elicitation.

## Decisions

### Drop the client-facing narration rather than reroute it to stderr

The glass-box narration lines (`> [id] tool — intent`, `[OK] [id] summary (ms)`) will be
removed, not re-emitted as stderr structlog events. Rationale: the same information already
exists in the structured `tool.received`/`tool.result`/`tool.error` events (tool name, intent,
elapsed_ms, error message) with the same `request_id`. Re-adding a parallel human-readable line
would duplicate data and re-introduce a second formatting path. The correlation story is intact
because it was always carried by contextvars in the structured stream, not by `ctx.info`.

**Alternative considered:** Keep a human-readable narration by logging it through structlog to
stderr. Rejected as redundant; the structured events are sufficient and cleaner, and clients
render raw stderr inconsistently (e.g. Cursor tags every stderr line `[error]`).

### Keep `_run_tool`'s timing and error translation; only remove the client emit

`_run_tool` still generates the `request_id`, binds contextvars, times the call, logs the
structured events, and translates typed errors to plain language. Only the `_glass_log` calls
are removed. This keeps the orchestration and the correlation architecture unchanged.

### Guide: teach the transition (G3), single-stream cockpit

The chapter keeps the (now-historical) protocol-logging explanation as *"what it was and why
MCP is retiring it,"* then presents the stderr-native model as current practice. The two-pane
cockpit is reframed: **Pane 1 = the client's captured stderr** (Cursor Output channel / Claude
Desktop `mcp*.log`), **Pane 2 = a tailed `WXCC_LOG_FILE`** — the same stderr stream, viewed two
ways. Correlation still works via `request_id`; the drill ("find the id, scan the other view")
is preserved, just against one underlying stream.

The `[error]` prefix confusion (Cursor labels all stderr as `[error]`) and the "level field vs.
filter threshold" explanation are retained — they are more relevant than ever now that stderr
is the only channel.

### Scope the guide edits to keep numbering stable

Chapter numbers (8 = logging concepts, 9 = troubleshooting) stay. Edits are in-place rewrites of
subsections, not new chapters, so no renumbering is needed.

## Risks / Trade-offs

- **Loss of the pretty Inspector Notifications narration** → Mitigation: the structured events
  carry the same data; the guide teaches how to read them and how clients surface stderr.
- **Two unarchived changes touch the same chapter** (`add-mcp-logging-chapter` and this one) →
  Mitigation: this change owns the authoritative end-state for the logging content; archive
  `add-mcp-logging-chapter` first (or accept that this change's edits are the final word).
- **Tests asserting client logs** → Mitigation: update them to assert on structured events;
  audit `tests/` for `ctx`/log-emission assertions before removing code.
- **Deprecation window still open** → Protocol logging would still *work* today, so removal is a
  forward-looking choice, not a forced one. Accepted: teaching new-server best practice is the
  lab's goal.
