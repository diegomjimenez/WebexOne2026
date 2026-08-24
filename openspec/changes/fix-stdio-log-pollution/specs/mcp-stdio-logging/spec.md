## ADDED Requirements

### Requirement: Logs are isolated from the stdio protocol stream

When the server runs over stdio transport, the server SHALL write all log records and diagnostic output to `stderr` only, and SHALL NOT write any log record to `stdout`. `stdout` MUST carry MCP JSON-RPC frames exclusively.

#### Scenario: Startup log does not reach stdout

- **WHEN** the server starts and emits its startup log event (e.g. `wxcc_mcp_server_starting`)
- **THEN** the log line appears on `stderr`
- **AND** no log line appears on `stdout`

#### Scenario: Runtime logs go to stderr

- **WHEN** any tool invocation, API call, or error is logged during a session
- **THEN** the structured JSON log record is written to `stderr`
- **AND** `stdout` receives only JSON-RPC response frames

#### Scenario: MCP client parses stdout without protocol errors

- **WHEN** an MCP client (e.g. Claude Desktop) reads the server's `stdout` during initialization and tool listing
- **THEN** every line on `stdout` is a valid JSON-RPC message
- **AND** the client does not report parse/validation errors caused by log content (e.g. keys `event`, `transport`, `level`, `timestamp`)

### Requirement: Log formatting and redaction are preserved

Redirecting logs to `stderr` SHALL NOT change the existing structured-JSON log format or the redaction of sensitive values.

#### Scenario: Structured JSON format retained on stderr

- **WHEN** a log event is emitted
- **THEN** it is rendered as a single-line JSON object including `event`, `level`, and `timestamp` fields on `stderr`

#### Scenario: Secrets remain redacted

- **WHEN** a log event contains a sensitive key (e.g. `access_token`, `authorization`, `client_secret`)
- **THEN** the value is replaced with the redaction placeholder before being written to `stderr`
