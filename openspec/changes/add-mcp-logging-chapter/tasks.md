## 1. Chapter skeleton and placement

- [x] 1.1 Insert new Chapter 8 heading ("Understanding MCP server logging") in `lab-materials/lab-guide/lab-guide.md` after current Chapter 7 ("Going further") and before current Chapter 8 ("Troubleshooting playbook")
- [x] 1.2 Renumber current Chapter 8 → 9 ("Troubleshooting playbook") and update the Appendix heading if needed
- [x] 1.3 Verify no cross-references in earlier chapters point to Ch 8 by number (they use section titles, but confirm)

## 2. MCP protocol logging section

- [x] 2.1 Write the opening section explaining `notifications/message` (server → client) and `logging/setLevel` (client → server) with their roles
- [x] 2.2 Add a concrete JSON-RPC envelope example showing what `ctx.info(message)` produces over the wire
- [x] 2.3 List the RFC 5424 severity levels the MCP spec defines and note which ones the server actually emits (debug, info, warning, error)
- [x] 2.4 Link to the official MCP logging specification (https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging)

## 3. Server-side structured logging section

- [x] 3.1 Write the section explaining structlog's role: structured JSON on stderr/file, not plain text
- [x] 3.2 Add an annotated code snippet from `logging_config.py` showing the `structlog.configure(...)` call with the five processors identified in order (contextvars, add_log_level, timestamper, redact, JSON renderer)
- [x] 3.3 Explain `make_filtering_bound_logger(numeric_level)` as the server-side level filter
- [x] 3.4 Explain `PrintLoggerFactory(file=log_stream)` and the `_TeeStream` for dual output (stderr + file)

## 4. Secret redaction section

- [x] 4.1 Explain the `_redact` processor: list the `_SENSITIVE_KEYS` set, describe shallow key matching and nested header dict handling, note the `***REDACTED***` replacement value
- [x] 4.2 State that secrets never appear in either log stream (server-side or client-facing)

## 5. Correlation architecture section

- [x] 5.1 Explain `_new_request_id()` (6 hex chars from `secrets.token_hex(3)`) and where it is generated (in `_run_tool`)
- [x] 5.2 Explain `bind_request_context(request_id=..., tool=...)` storing into contextvars, and `merge_contextvars` in the processor chain copying it into every downstream log record
- [x] 5.3 Show how `_run_tool` orchestrates the lifecycle: generate id → bind context → log `tool.received` → execute → log `tool.result`/`tool.error` → reset context

## 6. Bridge between the two streams

- [x] 6.1 Explain `_emit_log(ctx, level, message)`: resolves `ctx.info()` / `ctx.error()` etc. to send `notifications/message` over MCP transport
- [x] 6.2 Explain `_glass_log`: wraps `_emit_log` with the `[request_id]` prefix and ASCII markers (`>`, `[OK]`, `[ERR]`)
- [x] 6.3 Show the dual-write pattern: `logger.info("tool.received", ...)` writes to stderr/file while `_glass_log(ctx, "info", ...)` sends the same event to the client — both carrying the same request_id

## 7. Third stream (stdlib root logger)

- [x] 7.1 Explain that `logging.basicConfig(level=numeric_level)` sets the stdlib root logger, which third-party libraries (httpx, MCP SDK) use
- [x] 7.2 Identify the plain-text lines: `Processing request of type ...` (MCP SDK) and `HTTP Request: GET ...` (httpx)
- [x] 7.3 Explain that these are not structured JSON, not redacted, and not correlated — and that `WXCC_LOG_LEVEL` controls their threshold too

## 8. "Why info, not debug?" explanation

- [x] 8.1 Write the short explanation distinguishing the `"level"` field in JSON output (emitted severity chosen by the developer) from the filter threshold (`WXCC_LOG_LEVEL`)
- [x] 8.2 Explain that tool invocations are deliberately tagged as `info` because they are operationally significant, while `debug` is reserved for internal plumbing

## 9. Two independent filters recap

- [x] 9.1 Reiterate the two independent filters: server-side `WXCC_LOG_LEVEL` (controls stderr/file) vs. client-side `logging/setLevel` (controls MCP notification display)
- [x] 9.2 State that changing one does not affect the other, and that the server streams all severities to the client regardless of the server-side level

## 10. References and final review

- [x] 10.1 Add links to the MCP logging spec and the MCP debugging guide at the end of the chapter
- [x] 10.2 Verify the chapter reads as a coherent narrative from protocol → implementation → side effects → practical clarity
- [x] 10.3 Verify renumbered chapters and appendix are consistent throughout the document
