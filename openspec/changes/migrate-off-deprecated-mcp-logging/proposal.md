## Why

[SEP-2577](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
(Final) deprecates the MCP protocol-level **logging** capability (`logging/setLevel`,
`notifications/message`) as of the 2026-07-28 specification. New servers should not use
in-protocol logging; they should log with Python's `logging` module to stderr, which the host
captures automatically. On current SDK versions the deprecated calls emit an
`MCPDeprecationWarning`.

This server currently sends client-facing logs through the deprecated capability via
`_emit_log` → `ctx.info()/warning()/error()` (used in ~10 tools) and narrates each tool
lifecycle through `_glass_log`. The lab guide's Chapter 8 teaches protocol logging as a core
primitive and builds its entire "two-pane cockpit" narrative on it. Both are now teaching and
demonstrating a deprecated feature — right at the 2026-07-28 inflection point.

The good news: the server's **server-side structured logging** (structlog → stderr/file) is
already the recommended modern pattern, and the correlation architecture lives in structlog
contextvars — not in `ctx.info`. So the migration removes a redundant, deprecated layer rather
than losing the core observability story.

## What Changes

- **BREAKING (behavioral, lab-facing)**: Remove protocol-level client logging from the server.
  Delete `_emit_log` and `_glass_log`, and remove the `ctx.info()/warning()/error()` narration
  calls from all tools. The tool lifecycle remains fully observable through the existing
  server-side structured events (`tool.received`, `tool.result`, `tool.error`) which already
  carry the correlation `request_id`.
- Keep **progress notifications** (`ctx.report_progress`) and **elicitation** (`ctx.elicit`) —
  neither is deprecated by SEP-2577.
- Update the server module docstring to stop advertising "client-facing logging" as a
  demonstrated primitive.
- **Lab guide (G3 — teach the transition)**: Rewrite Chapter 8's client-logging material to
  teach the deprecation explicitly: what protocol logging was, why MCP is retiring it
  (SEP-2577), and the stderr-native replacement the server already uses. Reframe the two-pane
  cockpit as "one stderr stream, captured two ways" (the client's captured stderr + a tailed
  log file). Update Step 0.8, the per-chapter correlation callouts, the Chapter 9
  troubleshooting playbook, and the appendix cheat-sheet to drop the "client-facing protocol
  log line" framing.
- Fix the pre-existing §8.5 code/prose mismatch as part of the rewrite (the guide's `_emit_log`
  snippet omitted the `ctx is None` guard and the best-effort `try/except`; that content is
  being removed/replaced anyway).

## Capabilities

### New Capabilities

- `mcp-logging-deprecation`: The lab guide SHALL teach that MCP protocol logging is deprecated
  (SEP-2577), explain the timeline and rationale, and present the stderr-native logging pattern
  as the recommended replacement — including how each supported client surfaces captured
  stderr.

### Modified Capabilities

_None as formal spec deltas._ The prior change `add-mcp-logging-chapter` (capability
`mcp-logging-chapter`) is implemented but not yet archived, so its spec is not in
`openspec/specs/` and cannot receive a delta. This change therefore expresses all requirements
under the new `mcp-logging-deprecation` capability, which supersedes the protocol-logging and
two-stream requirements of `mcp-logging-chapter`. At archive time, `mcp-logging-deprecation`
reflects the authoritative end-state for the chapter's logging content.

## Impact

- **Source code**: `wxcc-mcp-server/src/wxcc_mcp/server.py` — remove `_emit_log`, `_glass_log`;
  strip `ctx.info/warning/error` calls from `_run_tool` and ~10 tools; update the sync log
  callback (`_log`/`on_log`) and module docstring. `ctx.report_progress` and `ctx.elicit`
  remain.
- **Tests**: `wxcc-mcp-server/tests/` — any test asserting client-facing log emission needs
  updating to assert on structured server-side events instead.
- **Lab guide**: `lab-materials/lab-guide/lab-guide.md` — Chapter 8 rewrite, Step 0.8 cockpit,
  per-chapter callouts, Chapter 9 playbook, appendix cheat-sheet.
- **Out of scope (follow-up)**: Sampling (`_maybe_summarize` → `create_message`) is also
  deprecated by SEP-2577 but is a distinct feature with its own tradeoffs; it is intentionally
  NOT addressed here and left for a separate change.
- **References**: <https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging>
