## ADDED Requirements

### Requirement: Per-invocation correlation id

The server SHALL generate a correlation id for each tool invocation and make that id visible in both the client-facing log stream and the server-side log stream. The id SHALL be short and human-readable (a 6-character hexadecimal token) so it can be matched by eye. The id SHALL be bound into the server-side logging context so that every downstream server log record produced during the invocation (tool, API client, and auth broker records) carries the same id automatically.

#### Scenario: Same id appears in both streams

- **WHEN** a tool is invoked and produces both client-facing logs and server-side logs
- **THEN** the client-facing log lines include the invocation's correlation id
- **AND** the server-side log records for that invocation include the same correlation id under a stable field (e.g. `request_id`)

#### Scenario: Downstream records inherit the id

- **WHEN** a tool invocation triggers a WxCC API call and a token resolution
- **THEN** the `wxcc_api_call` record and the auth record for that invocation both carry the invocation's correlation id without those modules being passed the id explicitly

#### Scenario: Ids do not leak across invocations

- **WHEN** one tool invocation completes and another begins
- **THEN** the second invocation's log records carry a different correlation id
- **AND** no record from the second invocation carries the first invocation's id

### Requirement: Unified staged logging vocabulary

The server SHALL narrate each tool invocation using a consistent set of lifecycle stages across both log streams: a received/start stage, authentication, API request, optional retry, and a terminal result or error stage. The client-facing stage messages SHALL be human-readable and use the severity level appropriate to the stage (informational for normal stages, warning for retries and risky writes, error for failures).

#### Scenario: Successful read narrates start and result

- **WHEN** a read-only tool completes successfully
- **THEN** the client stream shows a start line and a terminal success line, both carrying the correlation id
- **AND** the server log shows a corresponding received event and a result event with the same id

#### Scenario: Failure narrates an error stage

- **WHEN** a tool invocation fails with a typed error
- **THEN** the client stream shows an error-level line with the plain-language translated message and the correlation id
- **AND** the server log shows a terminal error event carrying the same id

### Requirement: All tools emit client-facing logs

The server SHALL emit client-facing logs for every tool invocation, including read-only tools, through the shared tool-execution path. Emitting client-facing logs SHALL degrade gracefully to a no-op when the connected client does not support logging, and a logging failure SHALL never cause a tool to fail.

#### Scenario: Read tool produces client logs

- **WHEN** a read-only tool such as listing address books is invoked
- **THEN** the client receives start and result log messages for that invocation

#### Scenario: Client without logging support

- **WHEN** the connected client does not support log notifications
- **THEN** the tool still executes and returns its result
- **AND** no error is raised by the attempt to emit client-facing logs

### Requirement: Performance metric on completion

The server SHALL measure the elapsed wall-clock time of each tool invocation and include it on the terminal result stage in both streams.

#### Scenario: Result includes elapsed time

- **WHEN** a tool invocation completes successfully
- **THEN** the client-facing success line includes an elapsed-time value in milliseconds
- **AND** the server-side result event includes an `elapsed_ms` field

### Requirement: Secret redaction and stdio isolation are preserved

Glass-box logging SHALL NOT weaken existing safeguards. Sensitive values SHALL remain redacted in the server log, no secret SHALL appear in any client-facing message, and stdout SHALL continue to carry only MCP JSON-RPC frames.

#### Scenario: No secret in client-facing logs

- **WHEN** a tool resolves a token and calls the WxCC API
- **THEN** no access token, refresh token, client secret, or authorization header value appears in any client-facing log message

#### Scenario: Redaction retained on server side

- **WHEN** a server log record would contain a sensitive key
- **THEN** its value is written as the redaction placeholder, as before this change

#### Scenario: stdout remains protocol-only

- **WHEN** glass-box logs are emitted during a session over stdio transport
- **THEN** stdout continues to carry only valid JSON-RPC messages
