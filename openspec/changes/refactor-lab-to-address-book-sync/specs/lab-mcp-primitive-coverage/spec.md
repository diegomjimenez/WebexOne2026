## ADDED Requirements

### Requirement: Single coherent lab scenario
The lab SHALL teach MCP through one scenario — synchronizing CRM contacts into a WxCC
address book and provisioning it for agents — and SHALL NOT include the former
agent-lifecycle scenario.

#### Scenario: Only the address-book scenario is present
- **WHEN** an attendee inspects the server's registered tools, resources, and prompts
- **THEN** all of them pertain to the CRM → address book → desktop profile scenario
- **AND** no agent onboarding, callback, or routing-diagnosis primitives are present

### Requirement: Demonstrate every MCP primitive
The lab SHALL demonstrate all core MCP primitives on the single scenario: tools, resources,
prompts, elicitation, progress notifications, client-facing logging, and (optional)
sampling.

#### Scenario: Tools present
- **WHEN** the client lists tools
- **THEN** address-book/entry CRUD, bulk save, desktop-profile/agent reads, the
  assign-to-profile write, and the composite sync tool are available

#### Scenario: Resources present
- **WHEN** the client lists resources
- **THEN** the CRM contacts source, the address-book schema guide, and the write-safety
  guide are available

#### Scenario: Prompts present
- **WHEN** the client lists prompts
- **THEN** `sync_crm_to_address_book` and `provision_outbound_dialing` are available

#### Scenario: Interactive primitives exercised
- **WHEN** a gated write runs on a client that supports them
- **THEN** elicitation requests approval, progress notifications stream per step, and
  client-facing log messages are emitted
- **AND WHEN** sampling is supported and requested
- **THEN** a model-generated summary is produced

### Requirement: Guided provisioning prompts
The lab SHALL provide two prompts: one driving discover → sync → verify, and one driving the
full arc including attaching the address book to a chosen desktop profile.

#### Scenario: Sync prompt flow
- **WHEN** the `sync_crm_to_address_book` prompt is invoked
- **THEN** it directs the assistant to read the CRM resource, diff against existing entries,
  preview, sync on approval, and verify

#### Scenario: Provisioning prompt flow
- **WHEN** the `provision_outbound_dialing` prompt is invoked
- **THEN** it directs the assistant to find or create a book, sync from CRM, choose a desktop
  profile (using the read tools), assign the book on approval, and verify which agents gain
  access

### Requirement: No deprecated API usage
The lab SHALL target non-deprecated APIs: Address Book v2, Desktop Profile APIs (not Agent
Profile), and SHALL avoid deprecated Desktop Profile dial-plan fields.

#### Scenario: Version and fields
- **WHEN** the server issues address-book or desktop-profile calls
- **THEN** it uses Address Book v2 paths and omits deprecated dial-plan fields

### Requirement: Single Config API scope pair
The server SHALL require only `cjp:config_read` and `cjp:config_write` scopes and SHALL NOT
require Reporting/Search or Platform/People scopes.

#### Scenario: Config-only scopes
- **WHEN** the server's configuration is inspected
- **THEN** only the Config API family, base URL, and its read/write scopes are present

### Requirement: Retain reusable infrastructure
The refactor SHALL preserve the OAuth broker, async API client, structured logging with
redaction, typed IO, and the elicitation/dry-run write-safety pattern.

#### Scenario: Infrastructure intact
- **WHEN** the refactor is complete
- **THEN** tokens remain brokered per session and encrypted at rest, are never returned to
  the model or logged, and every write remains gated

### Requirement: Updated lab materials
The README and lab guide SHALL be rewritten to teach the new scenario and map each step to
the MCP primitive it demonstrates.

#### Scenario: Docs reflect the new scenario
- **WHEN** an attendee reads the README and lab guide
- **THEN** they describe the CRM → address book → desktop profile scenario and its primitive
  map, with no references to the removed agent-lifecycle scenario
