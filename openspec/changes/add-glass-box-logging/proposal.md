## Why

The lab teaches MCP primitives, but troubleshooting — the skill of *correlating* what happened in the client with what happened on the server — is currently impossible to teach. The two log streams speak different vocabularies and share no identifier, so a participant cannot match a tool click in their client to the `wxcc_api_call` lines it produced. Client-facing logging is also thin: read tools emit nothing, `ctx.debug` is never used, and messages are terse machine strings. This change turns the server into a "glass box" whose client and server logs tell one correlated story, making MCP + WxCC troubleshooting a first-class, impressive part of the lab.

## What Changes

- Introduce a **per-invocation correlation id** (short, human-readable) generated once per tool call and bound into structlog `contextvars` so it stamps *every* downstream server-side log automatically, and prefixed onto every client-facing `ctx` log so both streams can be matched by eye.
- Adopt a **unified staged logging vocabulary** across both channels: `tool.received` → auth → `wxcc_api_call` (+ retry) → `tool.result` (with `elapsed_ms`) / `tool.error`.
- Wrap all tool execution in `_run_tool` so **read tools also emit client-facing logs** (they are currently silent) and so success/error envelopes are consistent, without touching the 20+ individual tool functions.
- Add a **glass-box client logger helper** that streams human-readable, level-appropriate (`debug`/`info`/`warning`/`error`) messages via the MCP context, including the correlation id, plain-language intent, and result/error summary.
- Add **elapsed-time (performance) metrics** to the result stage.
- Document a **scenario playbook** and a **two-pane cockpit** (MCP Inspector notifications alongside a tailed `wxcc_debug.log`) in the lab guide, including the contrasting failure scenarios (missing token vs 403 vs E.164 validation) that teach "read both, match by id, notice what's present or absent."
- Explain the two independent log filters (constructor `log_level` filters stderr; `logging/setLevel` adjusts the client stream) so all severity levels can surface in the Inspector.

## Capabilities

### New Capabilities
- `glass-box-logging`: Correlated client-facing + server-side logging for troubleshooting — the correlation id, the unified staged vocabulary, the `_run_tool` logging envelope for all tools (including reads), performance metrics, and graceful degradation when a client does not support logging.

### Modified Capabilities
- `lab-guide-document`: The lab guide gains a two-pane troubleshooting cockpit (MCP Inspector + tailed server log), per-chapter "correlate it" callouts, an expanded debugging chapter with the scenario playbook, and a log-correlation cheat-sheet appendix.

## Impact

- **Code**: `wxcc-mcp-server/src/wxcc_mcp/server.py` (`_run_tool`, `_emit_log`, new correlation-id + glass-box helpers); `logging_config.py` (contextvars binding helpers, optional). Tool implementations (`tools/*.py`) are unchanged — they inherit the bound correlation id automatically.
- **Docs**: `lab-materials/lab-guide/lab-guide.md` (Chapter 0 setup, per-chapter callouts, Chapter 7 debugging, new appendix); references the MCP debugging guide and Inspector.
- **Runtime behavior**: More verbose client-facing logs by design (a teaching feature); no change to secret redaction, stdio isolation, or the write-safety/elicitation gates. Fully backward compatible — logging degrades to no-ops on clients that do not support it.
- **Dependencies**: None new (MCP Inspector is run ad hoc via `npx`).
