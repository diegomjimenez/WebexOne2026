## ADDED Requirements

### Requirement: MCP protocol logging section

The chapter SHALL open with a section explaining the MCP logging primitive as defined by the protocol specification: the `notifications/message` notification (server → client), the `logging/setLevel` request (client → server), and the RFC 5424 severity levels (debug through emergency). The section SHALL include an example of the JSON-RPC envelope that `ctx.info(message)` produces over the wire.

#### Scenario: Protocol primitive explained with wire format

- **WHEN** a participant reads the MCP protocol logging section
- **THEN** it describes `notifications/message` and `logging/setLevel` with their roles (server-to-client notification vs. client-to-server level control)
- **AND** it shows a concrete JSON-RPC envelope example for a `notifications/message` notification

#### Scenario: Severity levels listed

- **WHEN** a participant reads the protocol section
- **THEN** it lists the RFC 5424 severity levels the MCP spec uses (debug, info, notice, warning, error, critical, alert, emergency) and notes which ones the server actually emits

### Requirement: Server-side structured logging section

The chapter SHALL include a section explaining how the server uses structlog to produce structured JSON logs on stderr (and optionally a log file), covering: the processor chain (contextvars merge, add level, timestamp, redaction, JSON rendering), the `PrintLoggerFactory` output target, and the `make_filtering_bound_logger` level filter.

#### Scenario: Processor chain walkthrough

- **WHEN** a participant reads the structured logging section
- **THEN** it identifies the five structlog processors in order (contextvars, add_log_level, timestamper, redact, JSON renderer) and explains each one's role in one sentence

#### Scenario: Code snippet from configure_logging

- **WHEN** a participant reads the structured logging section
- **THEN** it includes an annotated code snippet from `logging_config.py` showing the `structlog.configure(...)` call

### Requirement: Secret redaction explained

The chapter SHALL explain the `_redact` processor: which keys it targets (`_SENSITIVE_KEYS`), how it handles nested header dicts, and that the redaction value is `***REDACTED***`. It SHALL state that secrets never appear in either log stream.

#### Scenario: Redacted keys listed

- **WHEN** a participant reads the redaction explanation
- **THEN** it lists the key names that are always redacted (authorization, access_token, refresh_token, token, client_secret, token_encryption_key, bearer, password, secret)

### Requirement: Correlation architecture section

The chapter SHALL explain how the `request_id` (6 hex chars) is generated per tool invocation, bound into structlog contextvars via `bind_request_context`, and inherited by every downstream log record — making the server-side stream greppable by a single id. It SHALL reference the `_run_tool` function as the orchestration point.

#### Scenario: Contextvars correlation explained

- **WHEN** a participant reads the correlation section
- **THEN** it explains that `bind_request_context` stores the request_id in a contextvar, and that `merge_contextvars` in the processor chain copies it into every subsequent log record for that invocation

### Requirement: Bridge between the two streams

The chapter SHALL explain how `_emit_log` and `_glass_log` bridge the server-side log stream and the MCP protocol log stream: `_emit_log` calls `ctx.info()` / `ctx.error()` etc. to send a `notifications/message` to the client, while structlog `logger.info()` writes to stderr/file. Both carry the same `request_id`, making the two streams one correlated story.

#### Scenario: _emit_log code path shown

- **WHEN** a participant reads the bridge section
- **THEN** it shows how `_emit_log(ctx, level, message)` resolves to `ctx.info(message)` (or the appropriate severity method) which sends a `notifications/message` notification over the MCP transport

### Requirement: Third stream explained (stdlib root logger)

The chapter SHALL explain that third-party libraries (httpx, MCP SDK, asyncio) log through the stdlib root logger configured by `logging.basicConfig`, producing plain-text output on stderr that is not structured JSON, not redacted, and not correlated. It SHALL explain that `WXCC_LOG_LEVEL` controls the root logger threshold, so setting it to DEBUG causes all third-party debug output to appear alongside the structured JSON.

#### Scenario: Plain-text lines identified

- **WHEN** a participant reads the third-stream section
- **THEN** it identifies the plain-text lines (`Processing request of type ...`, `HTTP Request: GET ...`) as coming from the MCP SDK and httpx respectively, not from the server's own logging

### Requirement: "Why info, not debug?" explanation

The chapter SHALL include a short explanation that the `"level"` field in a structured JSON log record reflects the severity the developer chose when calling `logger.info()` or `logger.debug()`, not the filter threshold. Setting `WXCC_LOG_LEVEL=DEBUG` means the filter passes everything at DEBUG or above, but tool invocations are deliberately tagged as `info` because they are operationally significant.

#### Scenario: Level field vs. filter threshold distinguished

- **WHEN** a participant reads the explanation
- **THEN** it states that `"level": "info"` in a log record means the code called `logger.info()`, and that the `WXCC_LOG_LEVEL` setting controls which levels pass the filter, not which level appears in the output

### Requirement: Two independent filters recap

The chapter SHALL reiterate (before the troubleshooting playbook) that the server has two independent level filters: the server-side `WXCC_LOG_LEVEL` (constructor-time, controls stderr/file output) and the client-side `logging/setLevel` (runtime, controls which MCP notifications the client displays). Changing one does not affect the other.

#### Scenario: Filters clearly separated

- **WHEN** a participant reads the filters recap
- **THEN** it presents the two filters as independent controls, states what each governs, and notes that the server streams all severities to the client regardless of the server-side level

### Requirement: Spec and debugging guide references

The chapter SHALL link to the official MCP logging specification (https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging) and the MCP debugging guide (https://modelcontextprotocol.io/docs/tools/debugging) as authoritative references.

#### Scenario: External links present

- **WHEN** a participant wants to read more
- **THEN** the chapter includes hyperlinks to both the MCP logging spec and the MCP debugging guide
