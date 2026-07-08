## ADDED Requirements

### Requirement: Agent state reference resource

The server SHALL register an `agent_state_reference` MCP resource enumerating WxCC agent states, each state's meaning, and whether it blocks Available. It SHALL include at least RONA, Idle (with reason codes), Available, and Not Responding.

#### Scenario: Resource enumerates blocking states

- **WHEN** a client reads the `agent_state_reference` resource
- **THEN** it receives the list of agent states with meaning and a flag indicating whether each state blocks going Available, including RONA, Idle, Available, and Not Responding

### Requirement: Error code catalog resource

The server SHALL register an `error_code_catalog` MCP resource providing a structured list of `{code, meaning, likely_cause, remediation}`. Entries MAY be seeded as placeholders and SHALL be clearly marked for population from WxCC docs.

#### Scenario: Resource returns structured error entries

- **WHEN** a client reads the `error_code_catalog` resource
- **THEN** it receives a structured list where each entry has code, meaning, likely cause, and remediation fields

### Requirement: Config dependency map resource

The server SHALL register a `config_dependency_map` MCP resource documenting the relationships user → team(s) → queue(s) → required skills; user → skill profile → skills; and user → multimedia profile → channels. It SHALL encode the rule that going Available requires team mapping, skill match, and channel enablement to all align.

#### Scenario: Resource encodes the availability rule

- **WHEN** a client reads the `config_dependency_map` resource
- **THEN** it receives the documented dependency relationships and the rule that Available requires team mapping, skill match, and channel enablement to align

### Requirement: Troubleshooting runbook resource

The server SHALL register a `troubleshooting_runbook` MCP resource expressing the ordered decision tree: active/licensed → logged in → not stuck in RONA/idle → team assigned → team mapped to active queue → skills match → channel enabled → else escalate.

#### Scenario: Resource returns ordered decision tree

- **WHEN** a client reads the `troubleshooting_runbook` resource
- **THEN** it receives the ordered diagnostic steps ending in an escalation step

### Requirement: Diagnose-agent prompt

The server SHALL register a `diagnose_agent_cannot_go_available` MCP prompt with required arguments `agent_identifier` and `org_id`. The prompt SHALL set a READ-ONLY WxCC admin-assistant role that forbids executing or suggesting direct changes as actions, SHALL instruct following the runbook order and stopping early when a definitive blocking cause is confirmed, SHALL instruct cross-referencing findings against the runbook, agent-state reference, and error-code catalog, and SHALL require output as a ranked list of likely causes, each with cited evidence and a recommended remediation (noting where a remediation would require a write action without performing it), in plain language with bullet points.

#### Scenario: Prompt enforces read-only diagnostic behavior

- **WHEN** the `diagnose_agent_cannot_go_available` prompt is rendered with an `agent_identifier` and `org_id`
- **THEN** the prompt body assigns a read-only role, forbids performing writes, and directs the assistant to follow the runbook and cross-reference the reference resources

#### Scenario: Prompt requires ranked, evidence-backed output

- **WHEN** the assistant follows the prompt to a conclusion
- **THEN** it is directed to produce a ranked list of likely causes, each with cited evidence and a recommended remediation, flagging remediations that would require a write action without executing them
