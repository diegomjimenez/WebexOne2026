## Why

When diagnosing MCP server connection issues (timeouts, tool failures, auth errors), there is no persistent log file to inspect. Logs currently go only to stderr, which Claude Desktop captures to `%APPDATA%\Claude\logs\mcp-server-wxcc.log` but this is not always accessible or easy to tail. Operators need a configurable log file written directly by the server so DEBUG-level traces survive across sessions and can be shared for support.

## What Changes

- Add an optional `WXCC_LOG_FILE` environment variable (path to a log file).
- Add an optional `WXCC_LOG_LEVEL` override defaulting to `INFO` (already exists in config but ensure it flows through to file handler).
- When `WXCC_LOG_FILE` is set, `configure_logging()` additionally writes all log events to that file at the configured level, in addition to stderr.
- The file handler uses the same structured JSON format and secret redaction pipeline as the stderr handler — no separate format, no secrets in the file.
- Log file is opened in append mode so successive server restarts accumulate history.
- No new dependencies (stdlib `logging.FileHandler` only).

## Capabilities

### New Capabilities
- `mcp-log-file`: Structured JSON log file output, configurable via `WXCC_LOG_FILE` env var, sharing the same redaction and formatting pipeline as stderr.

### Modified Capabilities
- `mcp-stdio-logging`: The existing stderr-only logging constraint is relaxed — stderr remains required for stdio transport correctness, but an additional file sink may now coexist.

## Impact

- Code: `wxcc-mcp-server/src/wxcc_mcp/logging_config.py` (`configure_logging`), `wxcc-mcp-server/src/wxcc_mcp/config.py` (`Settings`).
- Dependencies: none new (stdlib `logging` only).
- Claude Desktop config: operators add `"WXCC_LOG_FILE": "C:\\path\\to\\wxcc_mcp.log"` to the `env` block in `claude_desktop_config.json`.
