## Context

The `wxcc-mcp-server` already emits two independent log streams:

- **Server-side** — `structlog` JSON to stderr and (optionally) `wxcc_debug.log`, with secret redaction. Events like `tool_invoked`, `wxcc_api_call`, `wxcc_api_retry`, `using_static_access_token`, `oauth_token_refreshed`. Configured in `logging_config.py`; its processor chain already includes `structlog.contextvars.merge_contextvars`.
- **Client-facing** — `ctx.info/warning/error` via the `_emit_log` helper in `server.py`, streamed to the MCP client as `notifications/message`. Currently used only by write tools, as terse machine strings; `ctx.debug` is unused; read tools are silent.

Neither stream shares an identifier, so a single tool invocation cannot be traced across both. The lab (`lab-materials/lab-guide/lab-guide.md`) walks through six chapters (read → create → manual add → provision → drift → sync) but has no way to teach *correlated* troubleshooting.

Constraints: stdio transport (stderr captured by host, stdout reserved for JSON-RPC); secrets must stay redacted; write-safety/elicitation gates must not change; changes should avoid touching the 20+ individual tool functions; must degrade gracefully on clients without logging support.

## Goals / Non-Goals

**Goals:**
- One **correlation id** per tool invocation, visible verbatim in *both* the client stream and the server log.
- A **unified staged vocabulary** so every tool narrates the same lifecycle shape.
- **All tools** (including reads) emit client-facing logs via a single choke point (`_run_tool`).
- Human-readable, level-appropriate glass-box messages plus **`elapsed_ms`** performance metrics.
- Lab-guide material: a two-pane cockpit (MCP Inspector + tailed server log) and a scenario playbook that teaches matching by id and reasoning about present/absent stages.

**Non-Goals:**
- No new transport, no HTTP/remote deployment work.
- No change to secret redaction, stdio isolation, or the elicitation/dry-run write gate.
- Not a production observability system (OpenTelemetry, trace export) — this is deliberately pedagogical verbosity.
- No changes to tool signatures or the typed input/output contracts.

## Decisions

### Decision 1: Correlation id bound via structlog contextvars
Generate a short id (6 hex chars, e.g. `a1b2c3`) once at the top of `_run_tool`. Bind it with `structlog.contextvars.bind_contextvars(request_id=..., tool=...)` and clear it in a `finally`. Because `merge_contextvars` is already in the processor chain, **every** downstream server log (in `tools/*.py`, `api/client.py`, `auth/oauth.py`) is stamped automatically with no edits to those modules. The same id is prefixed onto client-facing messages.

- **Why short id over UUID**: participants match by eye in a live lab; `[a1b2c3]` is scannable, a full UUID is not. Collisions are irrelevant at lab scale.
- **Alternative considered**: threading an explicit `request_id` parameter through every function — rejected as invasive and touching all tool files, defeating a key constraint.

### Decision 2: `_run_tool` becomes the logging envelope
`_run_tool` already wraps every tool coroutine with try/except for error translation, so it is the natural single place to emit `tool.received` (start) and `tool.result`/`tool.error` (end), and to time the call for `elapsed_ms`. To narrate intent, `_run_tool` accepts a short `tool_name` and a plain-language `intent` string from each call site (a one-line addition per tool, or derived centrally).

- **Why here**: it is the one function every tool routes through; reads and writes alike gain envelopes without per-tool work.
- **Alternative considered**: FastMCP middleware — heavier, less transparent for a teaching codebase, and version-dependent.

### Decision 3: Unified staged vocabulary
Server events and client lines map to the same stages so the two streams read as one story:

| Stage | Server event | Client-facing line |
|---|---|---|
| Received | `tool.received` | `> [id] <tool> — <intent>` |
| Auth | `using_static_access_token` / `oauth_token_refreshed` | `  [id] using session token` |
| API | `wxcc_api_call` | `  [id] -> <METHOD> <path>` |
| Retry | `wxcc_api_retry` | `  [id] retry <n> (rate limited)` |
| Result | `tool.result` (+`elapsed_ms`) | `[OK] [id] <summary> (<ms> ms)` |
| Error | `tool.error` | `[ERR] [id] <translated message>` |

Symbols use safe ASCII (`>`, `[OK]`, `[ERR]`, `->`) to render cleanly across clients; an optional richer glyph set can be a config toggle.

### Decision 4: All severity levels reach the client
Client-facing logs use `ctx.debug/info/warning/error` per stage. Per the MCP debugging guidance, the constructor `log_level` only filters stderr, and clients can call `logging/setLevel` to adjust the client stream at runtime — so the Inspector can show every level. This is called out in the lab guide as the "two independent filters" lesson.

### Decision 5: Lab-guide teaches by contrast
The scenario playbook centers on three failures that look alike in the client but differ on the server: **missing/expired token** (fails before any `wxcc_api_call`), **403 permission** (the API call *did* happen), and **E.164 validation** (rejected pre-network, no `wxcc_api_call`). Learning to read "which stages are present/absent, matched by id" is the transferable troubleshooting skill.

## Risks / Trade-offs

- **Verbosity / noise on reads** → Reads become chatty by design; documented as a teaching choice with a note that production would reduce it (level or a `GLASS_BOX` toggle).
- **Client renders symbols poorly** → Use ASCII-safe markers; keep messages plain text.
- **Logging failure breaks a tool** → All client-facing emits stay wrapped in the existing defensive try/except (`_emit_log` never raises).
- **contextvars leak across concurrent invocations** → Bind at entry and `clear_contextvars`/unbind in `finally` within `_run_tool` so ids never bleed between overlapping async tool calls.
- **Correlation id collision at scale** → Acceptable for a single-user lab; not intended for production multi-tenant tracing.
- **Lab-guide drift vs code** → Keep sample transcripts illustrative and note that concrete ids will differ per run (consistent with existing guide phrasing).

## Migration Plan

Additive and backward compatible. No config or API changes required to keep current behavior; the glass box activates automatically. Rollback is removing the `_run_tool` envelope and correlation-id binding — no data or schema migration involved. Lab-guide edits are documentation-only.

## Open Questions

- Should glass-box verbosity be gated behind an env toggle (e.g. `WXCC_GLASS_BOX=1`) for a quieter default, or always on for the lab? (Leaning: always on for the lab edition.)
- Do we want `elapsed_ms` on the client line, the server log, or both? (Leaning: both.)
- Include a tiny per-chapter callout in every chapter, or only the read/create/validate/sync chapters that best illustrate correlation?
