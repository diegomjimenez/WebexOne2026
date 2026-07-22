## ADDED Requirements

### Requirement: CRM contacts source resource
The system SHALL expose the CRM/directory contact data as an MCP resource returning a JSON
array of contacts, each with at least a stable id, name, and phone number.

#### Scenario: Resource is readable
- **WHEN** an MCP client reads the CRM contacts resource
- **THEN** the system returns a JSON document containing an array of contact records with
  `id`, `name`, and `number` fields

#### Scenario: Resource is the sync source of truth
- **WHEN** the sync tool runs
- **THEN** it reads its desired-state contacts exclusively from this resource

### Requirement: Address book schema guide resource
The system SHALL expose a reference resource describing address-book and entry rules: entry
naming, E.164 phone formatting, and `parentType` semantics.

#### Scenario: Guide is readable
- **WHEN** an MCP client reads the schema guide resource
- **THEN** the system returns the naming rules, E.164 format guidance, and `parentType`
  meaning

### Requirement: Diff CRM contacts against existing entries
The system SHALL compute a difference between the CRM source contacts and the existing
address-book entries, classifying each contact as create, update, or (optionally) delete,
matched on a stable key (CRM id attribute, falling back to normalized E.164 number).

#### Scenario: New contact classified as create
- **WHEN** a CRM contact has no matching existing entry
- **THEN** the diff classifies it as a create

#### Scenario: Changed contact classified as update
- **WHEN** a CRM contact matches an existing entry but a field differs
- **THEN** the diff classifies it as an update

#### Scenario: Stale entry classified as delete only when pruning
- **WHEN** an existing entry has no matching CRM contact and pruning is enabled
- **THEN** the diff classifies it as a delete
- **AND WHEN** pruning is disabled
- **THEN** the entry is left unchanged and reported as skipped

### Requirement: Composite CRM-to-address-book sync tool
The system SHALL provide a composite tool that applies the computed diff to an address book,
gated by elicitation, emitting progress notifications per step and client-facing log
messages, with pruning (delete-missing) disabled by default.

#### Scenario: Dry-run preview of the sync
- **WHEN** the sync tool is invoked without approval
- **THEN** the system returns a preview summarizing counts to create, update, and delete and
  makes no change

#### Scenario: Approved sync applies changes with progress
- **WHEN** the admin approves the sync
- **THEN** the system creates and updates entries, reports progress across the entries, logs
  noteworthy events, and returns a per-action result

#### Scenario: Pruning requires explicit opt-in and approval
- **WHEN** the sync is invoked with pruning enabled
- **THEN** the preview explicitly lists the entries to be deleted and their count
- **AND** deletions occur only after explicit approval

#### Scenario: Optional sampling summary
- **WHEN** the client supports sampling and a summary is requested
- **THEN** the system asks the client model to summarize what changed and includes it in the
  result
- **AND WHEN** sampling is unavailable
- **THEN** the system returns a deterministic summary instead
