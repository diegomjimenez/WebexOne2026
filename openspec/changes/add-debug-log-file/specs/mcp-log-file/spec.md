## ADDED Requirements

### Requirement: Log file output configurable via environment variable
The server SHALL support an optional `WXCC_LOG_FILE` environment variable. When set to a non-empty file path, the server SHALL write all log events to that file in append mode, in addition to stderr. When the variable is absent or empty, no log file is created and behavior is identical to the current state.

#### Scenario: Log file is written when WXCC_LOG_FILE is set
- **WHEN** the server starts with `WXCC_LOG_FILE` set to a writable path
- **THEN** log events are written to that file in structured JSON format, one event per line

#### Scenario: Existing log content is preserved across restarts
- **WHEN** the server restarts with the same `WXCC_LOG_FILE` path
- **THEN** new log events are appended to the file without truncating prior content

#### Scenario: No log file is created when WXCC_LOG_FILE is absent
- **WHEN** the server starts without `WXCC_LOG_FILE` set
- **THEN** no log file is created and stderr behavior is unchanged

### Requirement: Log file uses the same format and redaction as stderr
The log file SHALL use the same structured JSON format (one JSON object per line, with `event`, `level`, and `timestamp` fields) and the same secret redaction processor as the stderr handler. No sensitive field (access token, client secret, authorization header, etc.) SHALL appear in the log file.

#### Scenario: Log file records are single-line JSON
- **WHEN** a log event is emitted
- **THEN** each record in the log file is a single line of valid JSON with at least `event`, `level`, and `timestamp` fields

#### Scenario: Sensitive fields are redacted in log file
- **WHEN** a log event includes a field in the sensitive key set (e.g., `access_token`)
- **THEN** that field's value is written as `***REDACTED***` in the log file

### Requirement: Unwritable log file path does not crash the server
The server SHALL NOT crash or refuse to start if `WXCC_LOG_FILE` refers to an unwritable path. Instead, it SHALL log a warning to stderr describing the failure and continue operating without the file handler.

#### Scenario: Server starts despite unwritable log file path
- **WHEN** `WXCC_LOG_FILE` is set to a path the process cannot write (e.g., missing directory, permission denied)
- **THEN** the server emits a warning to stderr and starts normally without a file handler
