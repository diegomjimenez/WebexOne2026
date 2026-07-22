## ADDED Requirements

### Requirement: Single agent-lifecycle scenario

The lab MCP server SHALL expose exactly one coherent narrative scenario — the **agent
lifecycle** — composed of three acts: onboard an agent, diagnose why an agent cannot go
Available, and offboard an agent. All exposed tools, prompts, and resources SHALL serve
this scenario.

#### Scenario: Server exposes only lifecycle-relevant capabilities

- **WHEN** an MCP client lists the server's tools, prompts, and resources
- **THEN** every listed capability maps to onboard, diagnose, or offboard
- **AND** no real-time/supervisory, full-CRUD, or advanced-admin capabilities are present

#### Scenario: Learner can follow one agent end to end

- **WHEN** a lab attendee runs the scenario against a WxCC org
- **THEN** they can create an agent, then diagnose that agent's availability, then
  deactivate that agent, using only the tools this server exposes

### Requirement: Diagnostic (read) flow

The server SHALL provide read-only tools sufficient to answer "why can't this agent go
Available?" — resolving a user, reading their configuration (team, skill profile, agent
profile, multimedia profile), reading recent agent state history and login session, and
running a composite readiness check that returns ranked, evidence-backed blocking issues.

#### Scenario: Composite readiness check returns ranked blockers

- **WHEN** the diagnostic tool is run for an agent with a routing misconfiguration
- **THEN** it returns a ranked list of blocking issues, each with supporting evidence
- **AND** it performs no write operations

#### Scenario: Read tools are safe by default

- **WHEN** any diagnostic tool is invoked
- **THEN** it only reads WxCC data and never mutates org configuration

### Requirement: Onboard and offboard (write) flows

The server SHALL provide write tools to create an agent and assign a team and skill
profile (onboard), and to deactivate an agent and remove assignments (offboard). Every
write tool SHALL require explicit user confirmation before committing (see
`mcp-primitive-coverage` elicitation requirement) and SHALL first return a preview of the
intended change.

#### Scenario: Write preview precedes commit

- **WHEN** a write tool is invoked without confirmation
- **THEN** it returns a human-readable preview of the exact change and does not commit

#### Scenario: Confirmed write commits and reports outcome

- **WHEN** a write tool is invoked and the user confirms
- **THEN** the change is committed to WxCC and the tool reports the resulting entity state

### Requirement: Curated capability footprint

The server SHALL register a small, teachable footprint: approximately 12 tools, 4
resources, and 2 prompts. The tool manifest SHALL be small enough that MCP clients accept
it without toolset gating.

#### Scenario: Manifest is small and ungated

- **WHEN** the server starts with default settings
- **THEN** all tools are exposed directly without requiring toolset-filter configuration

### Requirement: Removal of out-of-scenario breadth

The server SHALL NOT contain the previously implemented real-time/supervisory tools,
full-CRUD management tools, advanced-admin tools, or their supporting API modules,
schemas, prompts, and resources. These SHALL be deleted from the lab repository.

#### Scenario: Deleted breadth is absent from the codebase

- **WHEN** the repository is inspected after the refactor
- **THEN** management/CRUD, supervisory, and advanced-admin modules for queues, skills
  management, entry points, sites, profiles, routing strategies, business hours, holiday
  lists, flows, audio files, webhooks, global variables, outdial ANI, and campaigns are
  not present

#### Scenario: No dead references remain

- **WHEN** the server module is imported after deletions
- **THEN** it imports cleanly with no references to removed tools, prompts, or resources
