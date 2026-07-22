## Context

`configure_logging()` in `wxcc-mcp-server/src/wxcc_mcp/logging_config.py` wires up `structlog` with `structlog.PrintLoggerFactory()`. By default `PrintLoggerFactory` writes to `sys.stdout`. It also calls `logging.basicConfig(format="%(message)s", level=...)`, which attaches a `StreamHandler` (defaulting to `stderr`, but this is left implicit).

`main()` in `server.py` calls `configure_logging()` and then `logger.info("wxcc_mcp_server_starting", transport="stdio")` before `mcp.run()`. That startup event — and every subsequent structlog line — is rendered as JSON and printed to stdout.

Under stdio transport the MCP host multiplexes JSON-RPC on stdout. Claude Desktop reads each stdout line and validates it against the JSON-RPC schema; the log line `{"event": "...", "transport": "stdio", "level": "info", "timestamp": "..."}` fails validation (`unrecognized_keys: transport, event, level, timestamp`), which is exactly the reported error. The MCP spec requires that servers using stdio never write anything but valid MCP messages to stdout, and use stderr for logging.

## Goals / Non-Goals

**Goals:**
- Guarantee stdout carries only JSON-RPC frames under stdio transport.
- Send all structlog output to stderr.
- Ensure stdlib `logging` (and any dependency using it) also defaults to stderr.
- Preserve current structured-JSON formatting and secret redaction.

**Non-Goals:**
- Changing log level semantics, log fields, or the redaction key set.
- Adding file-based logging or a new logging backend.
- Introducing configuration for choosing the log stream (stderr is the correct, non-optional target for stdio).

## Decisions

- **Point `structlog.PrintLoggerFactory` at `sys.stderr`.** Change `PrintLoggerFactory()` to `PrintLoggerFactory(file=sys.stderr)`. This is the minimal, direct fix for the root cause and keeps the JSONRenderer pipeline intact.
  - Alternative considered: replace `PrintLoggerFactory` with a stdlib-`logging`-backed factory (`structlog.stdlib.LoggerFactory`) so a single stderr handler governs everything. Rejected as more invasive for this fix; the print factory + explicit stderr is sufficient and lower-risk.

- **Make `logging.basicConfig` explicitly target stderr.** Pass `stream=sys.stderr` to `basicConfig`. `stderr` is already the default, but stating it explicitly documents intent and protects against any future change or handler that might target stdout.

- **Keep the processor chain unchanged.** `merge_contextvars`, `add_log_level`, `TimeStamper`, `_redact`, and `JSONRenderer` remain, so redaction and format are unaffected — only the destination stream changes.

## Risks / Trade-offs

- **A third-party library prints directly to stdout** → Out of scope of this change; the current codebase has no such prints (only the two logging call sites). If one appears later it must be redirected separately.
- **Tooling that expected logs on stdout** → No known consumer relies on that; structured logs remain identical in content, only on stderr, which is the conventional location for diagnostics.

## Migration Plan

1. Edit `logging_config.py` as described (import `sys`, set stderr on both `basicConfig` and `PrintLoggerFactory`).
2. Restart the MCP server; reconnect from Claude Desktop.
3. Rollback: revert the single-file edit if any regression appears.

## Open Questions

- None.
