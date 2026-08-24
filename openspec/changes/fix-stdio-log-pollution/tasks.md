## 1. Redirect logging to stderr

- [x] 1.1 In `wxcc-mcp-server/src/wxcc_mcp/logging_config.py`, add `import sys`.
- [x] 1.2 Update `logging.basicConfig(...)` to pass `stream=sys.stderr`.
- [x] 1.3 Change `structlog.PrintLoggerFactory()` to `structlog.PrintLoggerFactory(file=sys.stderr)`.

## 2. Verify no other stdout writes

- [x] 2.1 Confirm no `print(...)` or stdout writes exist in `wxcc-mcp-server/src/wxcc_mcp/` outside the MCP transport (search for `print(` and `sys.stdout`).

## 3. Validate the fix

- [x] 3.1 Run the server and capture stdout/stderr separately; confirm the `wxcc_mcp_server_starting` event appears on stderr and stdout has no log lines before the first JSON-RPC frame.
- [ ] 3.2 Reconnect from Claude Desktop (or an MCP stdio client) and confirm `initialize`, `tools/list`, `prompts/list`, `resources/list` succeed with no Zod/JSON-RPC parse errors.
- [x] 3.3 Confirm log records on stderr are still single-line JSON with `event`/`level`/`timestamp` and that a sensitive field is still redacted.
