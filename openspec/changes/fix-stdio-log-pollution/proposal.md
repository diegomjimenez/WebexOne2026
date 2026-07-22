## Why

When the WxCC MCP server runs over stdio (e.g. under Claude Desktop), its structured logs are written to **stdout**, the same channel MCP reserves for JSON-RPC. Claude Desktop's client parses each stdout line as a JSON-RPC message and rejects the log lines (Zod `unrecognized_keys: transport, event, level, timestamp`), producing connection-level errors. For stdio transport, stdout must carry protocol frames only; all logs/diagnostics must go to stderr.

## What Changes

- Route all server log output to **stderr** so stdout is exclusively JSON-RPC when using stdio transport.
- Configure `structlog` to print to `sys.stderr` (the current `PrintLoggerFactory()` defaults to stdout — the root cause).
- Configure stdlib `logging.basicConfig` to explicitly use a `stderr` stream handler, so any third-party library logs also avoid stdout.
- Keep existing structured-JSON formatting and secret redaction unchanged.

## Capabilities

### New Capabilities
- `mcp-stdio-logging`: Defines that, under stdio transport, server logs and diagnostics are emitted only to stderr and never to stdout, guaranteeing stdout carries valid JSON-RPC exclusively.

### Modified Capabilities
<!-- None: no existing published specs. -->

## Impact

- Code: `wxcc-mcp-server/src/wxcc_mcp/logging_config.py` (`configure_logging`), which is invoked from `wxcc-mcp-server/src/wxcc_mcp/server.py:main`.
- Dependencies: `structlog`, stdlib `logging` — no new dependencies.
- Behavior: MCP clients (Claude Desktop, and any stdio host) connect cleanly; no more JSON-RPC parse errors from log lines. Log content and destination format are otherwise unchanged (still structured JSON), only the stream changes to stderr.
