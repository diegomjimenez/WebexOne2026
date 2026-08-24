## ADDED Requirements

### Requirement: Lab Guide mirrors the deck tracks in 2025 step style

The Lab Guide SHALL be structured as chapters that mirror the deck's tracks, and each hands-on
chapter SHALL present learning objectives followed by numbered `Step X.Y` instructions, in the
same style as the 2025 `LabGuide.pdf`.

#### Scenario: Chapter structure

- **WHEN** a reader opens the Lab Guide
- **THEN** it contains an "About this lab" section, a "Getting started" section, and chapters
  for build-live, diagnose, and onboard/offboard that align with the deck tracks

#### Scenario: Numbered step instructions

- **WHEN** a reader follows a hands-on chapter
- **THEN** the actions are given as sequential, numbered `Step X.Y` instructions they can
  execute in order

### Requirement: Getting-started chapter reflects the actual server setup

The Getting-started chapter SHALL document the real `wxcc-mcp-server` setup: Python 3.11+,
virtual environment creation, `pip install -e ".[dev]"`, generating `WXCC_TOKEN_ENCRYPTION_KEY`,
populating `.env`, and connecting an MCP client over stdio.

#### Scenario: Setup steps match the codebase

- **WHEN** the Getting-started steps are executed against the repository
- **THEN** they succeed using the commands and environment variables that actually exist in
  `wxcc-mcp-server` (no invented commands or variables)

### Requirement: Lab Guide references existing code, not a new repo

The Lab Guide SHALL reference the existing `wxcc-mcp-server/` modules by path (e.g.
`src/wxcc_mcp/tools/get_user.py`, `resources/`, `prompts/`) rather than instructing attendees
to clone a separate companion repository.

#### Scenario: Code references resolve

- **WHEN** the guide cites a tool, resource, or prompt
- **THEN** the referenced file exists in the `wxcc-mcp-server` source tree

### Requirement: Use-case chapters include Solution callouts

Each build-live and write-flow chapter SHALL include a Solution section explaining how the
requirement is met by the code, mirroring the 2025 "Solution" callouts.

#### Scenario: Solution explains the mechanism

- **WHEN** a reader finishes a hands-on exercise
- **THEN** a Solution section describes which functions/primitives implement the behavior
  (e.g. elicitation, dry-run fallback, progress reporting)
