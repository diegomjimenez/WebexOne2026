## Context

The server uses `structlog` with a `PrintLoggerFactory` writing to `sys.stderr`, plus `logging.basicConfig` for stdlib integration (also stderr). This was just fixed by `fix-stdio-log-pollution` to ensure stdout is clean for JSON-RPC. The logging pipeline already includes secret redaction and JSON formatting.

Currently there is no way to get a persistent log file without shell-level redirection (`2>>file`), which is fragile on Windows/PowerShell and not available when Claude Desktop manages the process lifecycle.

## Goals / Non-Goals

**Goals:**
- Allow operators to configure a log file via `WXCC_LOG_FILE` env var.
- File output uses the identical structlog JSON format and secret redaction as stderr.
- File opened in append mode — restarts accumulate, no history lost.
- Level independently controllable via existing `WXCC_LOG_LEVEL`.
- Zero new package dependencies.

**Non-Goals:**
- Log rotation (out of scope; operators can use external tools like `logrotate`).
- Separate log levels for file vs stderr (same level applied to both).
- HTTP log shipping or structured log aggregators.
- Changing the existing stderr behavior in any way.

## Decisions

### D1: stdlib `logging.FileHandler` over a second `structlog.PrintLoggerFactory`

structlog's `PrintLoggerFactory` writes to a single file object. To fan out to two sinks (stderr + file), the cleanest approach is to keep structlog pointing at stderr and use the stdlib `logging` integration for the file sink — stdlib's `logging` module supports multiple handlers natively.

The structlog pipeline already calls `structlog.stdlib` processors; adding a `FileHandler` to the root logger means file output flows through the same JSON renderer via the stdlib bridge.

**Alternative considered**: Two separate structlog configurations. Rejected — structlog is configured globally and doesn't natively support multiple sinks without custom `LoggerFactory` wrapping.

### D2: `WXCC_LOG_FILE` as a plain `str` field in `Settings` (default `""`)

Consistent with how `token_store_dir` and other path-like settings are handled. Empty string = feature disabled. No special type needed.

### D3: Append mode (`"a"`) for the file handler

Preserves log history across server restarts, which is essential for tracing intermittent connection issues across Claude Desktop sessions.

### D4: Same redaction pipeline for file output

The `_redact` processor runs in structlog before the JSON renderer and before stdlib emission, so it applies to both stderr and file output automatically — no extra work needed.

## Risks / Trade-offs

- **Unbounded file growth** → Operators should use `WXCC_LOG_FILE` only during active debugging sessions; document this clearly. Future: add `WXCC_LOG_MAX_BYTES` / `WXCC_LOG_BACKUP_COUNT` for `RotatingFileHandler` (out of scope now).
- **File permission errors on Windows** → If the path is unwritable, `logging.FileHandler` raises at startup. Catch and log a warning to stderr, then continue without the file handler rather than crashing the server.
- **Double-encoding risk** → The stdlib bridge formats the structlog JSON as the log `message`; verify the FileHandler formatter doesn't wrap it in an extra layer. Use `logging.Formatter("%(message)s")` to emit the raw JSON line.

## Migration Plan

1. Add `log_file: str = Field(default="")` to `Settings` in `config.py`.
2. Update `configure_logging()` in `logging_config.py`: after the existing setup, if `log_file` is set, attach a `logging.FileHandler` with `Formatter("%(message)s")` to the root logger.
3. Update Claude Desktop config documentation in `README.md` with the `env` block example.
4. No rollback complexity — the feature is opt-in via env var; omitting it restores prior behavior exactly.

## Open Questions

- None blocking implementation.
