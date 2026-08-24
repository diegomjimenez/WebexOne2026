## ADDED Requirements

### Requirement: Two-pane troubleshooting cockpit in Getting-started

The Lab Guide SHALL document a two-pane "cockpit" for observing both log streams at once: the MCP Inspector (showing client-facing notifications) alongside a tailed server log file. The steps SHALL use commands that work with the actual server (stdio transport, `WXCC_LOG_FILE`, `Get-Content -Wait` on Windows) and SHALL reference the official MCP Inspector.

#### Scenario: Cockpit setup steps exist

- **WHEN** a reader reaches the Getting-started chapter
- **THEN** it contains steps to launch the MCP Inspector against `wxcc-mcp-server` and to tail the server log in a second pane

#### Scenario: Cockpit commands match the codebase

- **WHEN** the cockpit steps are executed against the repository
- **THEN** they use environment variables and commands that actually exist (e.g. `WXCC_LOG_FILE`, `WXCC_LOG_LEVEL`) with no invented options

### Requirement: Per-chapter correlation callouts

Hands-on chapters that best illustrate correlation (read, create, manual-add/validation, and sync) SHALL include a short callout that shows the invocation's correlation id, the matching client-facing line, and the matching server-side log line for that step.

#### Scenario: A chapter shows a matched pair

- **WHEN** a reader completes an instrumented chapter step
- **THEN** the guide shows a client-facing log line and a server-side log record that share the same correlation id for that step

### Requirement: Troubleshooting scenario playbook

The debugging chapter SHALL include a scenario playbook that teaches correlation by contrast, covering at least: a successful read, a missing/expired token failure, a permission-denied (403) failure, and an E.164 validation failure. For each scenario the playbook SHALL show the client-facing outcome and the corresponding server-side log stages, and SHALL explain what the presence or absence of an API-call stage indicates.

#### Scenario: Playbook contrasts pre-network vs API failures

- **WHEN** a reader studies the playbook
- **THEN** it shows that a missing-token and an E.164 validation failure produce no API-call log stage
- **AND** it shows that a 403 permission failure does produce an API-call stage
- **AND** it explains how to tell these apart by matching the correlation id across both streams

### Requirement: Two independent log filters explained

The Lab Guide SHALL explain that the server has two independent log filters: the constructor/`WXCC_LOG_LEVEL` filter that governs the server-side (stderr/file) stream, and the client-controlled runtime level (`logging/setLevel`) that governs which client-facing severities the client displays.

#### Scenario: Filters are distinguished

- **WHEN** a reader consults the debugging material
- **THEN** it states that changing the server log level does not by itself change what the client shows, and that all severity levels can be surfaced in the Inspector

### Requirement: Log-correlation cheat-sheet appendix

The Lab Guide SHALL include an appendix that summarizes the staged logging vocabulary (received, auth, API, retry, result, error) mapping each stage to its server-side event name and its client-facing line shape, plus brief guidance on what a missing stage indicates.

#### Scenario: Cheat-sheet maps stages to both streams

- **WHEN** a reader opens the appendix
- **THEN** it lists each lifecycle stage with the corresponding server event name and client-facing line format
