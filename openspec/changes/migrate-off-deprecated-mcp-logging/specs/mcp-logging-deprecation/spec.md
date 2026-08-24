## ADDED Requirements

### Requirement: Server does not use deprecated MCP protocol logging

The server SHALL NOT call the deprecated MCP protocol-level logging capability
(`ctx.info`/`ctx.warning`/`ctx.error`, i.e. `notifications/message`). The helper functions
`_emit_log` and `_glass_log` SHALL be removed, and no tool SHALL emit client-facing protocol
log messages. Tool lifecycle observability SHALL instead be provided by the existing
server-side structured events.

#### Scenario: No protocol log notifications during a tool call

- **WHEN** any tool runs to completion (success or handled error)
- **THEN** the server emits no `notifications/message` protocol log
- **AND** the SDK raises no `MCPDeprecationWarning` for logging

#### Scenario: Helpers removed

- **WHEN** the source of `server.py` is inspected
- **THEN** `_emit_log` and `_glass_log` are absent
- **AND** no `ctx.info(`, `ctx.warning(`, or `ctx.error(` calls remain

### Requirement: Tool lifecycle remains observable via structured server-side logs

The server SHALL continue to emit structured server-side events for every tool invocation —
at minimum `tool.received`, `tool.result`, and `tool.error` — each carrying the correlation
`request_id` bound through contextvars, so that a full lifecycle can be reconstructed without
protocol logging.

#### Scenario: Correlated lifecycle events

- **WHEN** a tool is invoked
- **THEN** a `tool.received` event and a terminal `tool.result` or `tool.error` event are
  written to the server-side (stderr/file) stream
- **AND** all events for that invocation share the same `request_id`

### Requirement: Progress and elicitation are preserved

The server SHALL continue to support progress notifications (`ctx.report_progress`) and
elicitation (`ctx.elicit`), which are not deprecated by SEP-2577.

#### Scenario: Sync still reports progress and elicits confirmation

- **WHEN** a confirm-gated sync tool runs
- **THEN** it still elicits user approval before committing writes
- **AND** it still reports per-entry progress updates

### Requirement: Server metadata reflects removal of client-facing logging

The server module docstring and any user-facing capability description SHALL NOT advertise
"client-facing logging" as a demonstrated MCP primitive.

#### Scenario: Docstring updated

- **WHEN** the `server.py` module docstring is read
- **THEN** it does not list client-facing / protocol logging among the demonstrated primitives
- **AND** it still lists tools, resources, prompts, elicitation, and progress notifications

### Requirement: Lab guide teaches the protocol-logging deprecation

The lab guide SHALL explain that MCP protocol-level logging is deprecated by SEP-2577
(2026-07-28 specification), including the timeline, the `MCPDeprecationWarning` behavior on
current SDKs, and the rationale, with a link to the SEP.

#### Scenario: Reader learns the deprecation and timeline

- **WHEN** a participant reads the logging chapter
- **THEN** they learn that `logging/setLevel` and `notifications/message` are deprecated as of
  2026-07-28
- **AND** they learn that new servers should log to stderr via Python's `logging` module
- **AND** a link to SEP-2577 is provided

### Requirement: Lab guide presents the stderr-native logging model

The lab guide SHALL present stderr-native structured logging as the recommended replacement and
SHALL explain how each supported client surfaces the server's captured stderr (e.g. Cursor
Output channel, Claude Desktop `mcp*.log`), including why Cursor labels stderr lines `[error]`
regardless of severity and why the JSON `level` field is independent of the `WXCC_LOG_LEVEL`
filter threshold.

#### Scenario: Reader can locate captured server logs per client

- **WHEN** a participant follows the chapter's guidance
- **THEN** they can find the server's captured stderr in their client
- **AND** they understand that the `[error]` channel label is not the message severity
- **AND** they understand the difference between the emitted `level` and the filter threshold

### Requirement: Lab guide cockpit and correlation drills use a single stream

The lab guide's setup cockpit (Step 0.8), per-chapter correlation callouts, the troubleshooting
playbook, and the appendix cheat-sheet SHALL describe observability in terms of the single
stderr stream (viewed as captured client stderr and/or a tailed `WXCC_LOG_FILE`) and SHALL NOT
instruct readers to rely on a client-facing protocol log line.

#### Scenario: Cockpit reframed to one stream, two views

- **WHEN** a participant sets up the two-pane cockpit in Step 0.8
- **THEN** both panes show the same stderr stream (captured client output and a tailed log file)
- **AND** the correlation drill still works by matching `request_id` across the two views

#### Scenario: No stale references to client protocol logging remain

- **WHEN** the lab guide is searched for guidance about reading logs
- **THEN** no instruction depends on `ctx.info`/`notifications/message` protocol logging
- **AND** the §8.5 `_emit_log` snippet mismatch no longer exists
