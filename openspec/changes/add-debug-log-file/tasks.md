## 1. Add Settings field

- [x] 1.1 In `wxcc-mcp-server/src/wxcc_mcp/config.py`, add `log_file: str = Field(default="", description="Path to a log file. When set, all log events are also written here in JSON format.")` to the `Settings` class.

## 2. Update configure_logging

- [x] 2.1 In `wxcc-mcp-server/src/wxcc_mcp/logging_config.py`, update the signature of `configure_logging` to accept an optional `log_file: str = ""` parameter.
- [x] 2.2 After the existing structlog/stdlib setup, check if `log_file` is non-empty. If so, wrap the `logging.FileHandler(log_file, mode="a", encoding="utf-8")` creation in a `try/except OSError` block.
- [x] 2.3 On success, set `Formatter("%(message)s")` on the handler and add it to the root logger at the same numeric level.
- [x] 2.4 On `OSError`, emit `logging.warning("log_file_unavailable", ...)` to stderr and continue without the file handler (do not raise).

## 3. Wire settings into server startup

- [x] 3.1 In `wxcc-mcp-server/src/wxcc_mcp/server.py`, update the `main()` call to `configure_logging(settings.log_level, log_file=settings.log_file)`.

## 4. Validate

- [x] 4.1 Run the server with `WXCC_LOG_FILE=wxcc_debug.log` and confirm the file is created and contains single-line JSON events.
- [x] 4.2 Stop and restart the server; confirm existing log content is preserved (append mode).
- [x] 4.3 Run with `WXCC_LOG_FILE` pointing to a non-existent directory; confirm the server starts and emits a warning to stderr instead of crashing.
- [x] 4.4 Confirm a field in `_SENSITIVE_KEYS` (e.g., `access_token`) is redacted in the log file.

## 5. Update Claude Desktop config docs

- [x] 5.1 Add an example `env` block to the "Connecting an MCP client" section in `wxcc-mcp-server/README.md` showing `WXCC_LOG_FILE` and `WXCC_LOG_LEVEL=DEBUG` usage.
