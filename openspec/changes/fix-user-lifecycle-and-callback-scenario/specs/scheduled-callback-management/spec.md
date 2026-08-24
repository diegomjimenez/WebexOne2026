## ADDED Requirements

### Requirement: Create a scheduled callback
The system SHALL create a scheduled callback via the WxCC Callback Schedule API, exposed as an MCP tool guarded by the existing elicitation/confirm write gate. Reference: `https://developer.webex.com/webex-contact-center/docs/api/v1/callback-schedule`.

#### Scenario: Create callback with required fields
- **WHEN** the create-callback tool is invoked with the required callback fields and the write is confirmed
- **THEN** the server issues the callback create request to the Callback Schedule API
- **AND** the created callback's id is returned as the resource id

#### Scenario: Dry-run preview before create
- **WHEN** the create-callback tool is invoked without confirmation and the client does not approve
- **THEN** no create request is sent
- **AND** a dry-run preview of the callback to be created is returned

### Requirement: List scheduled callbacks
The system SHALL list scheduled callbacks for an organization via the Callback Schedule API as a read-only MCP tool.

#### Scenario: List returns callbacks
- **WHEN** the list-callbacks tool is invoked for an org
- **THEN** the server issues a read request to the Callback Schedule API
- **AND** returns the callback records without requiring confirmation

#### Scenario: Empty list
- **WHEN** the list-callbacks tool is invoked and no callbacks exist
- **THEN** an empty collection is returned without error

### Requirement: Update a scheduled callback
The system SHALL update an existing scheduled callback via the Callback Schedule API, guarded by the elicitation/confirm write gate.

#### Scenario: Update an existing callback
- **WHEN** the update-callback tool is invoked with a callback id and changed fields and the write is confirmed
- **THEN** the server issues the callback update request to the Callback Schedule API
- **AND** a committed response referencing the callback id is returned

#### Scenario: Dry-run preview before update
- **WHEN** the update-callback tool is invoked without confirmation and the client does not approve
- **THEN** no update request is sent
- **AND** a dry-run preview of the intended change is returned

### Requirement: Delete a scheduled callback
The system SHALL delete a scheduled callback via the Callback Schedule API, guarded by the elicitation/confirm write gate.

#### Scenario: Delete an existing callback
- **WHEN** the delete-callback tool is invoked with a callback id and the write is confirmed
- **THEN** the server issues the callback delete request to the Callback Schedule API
- **AND** a committed response referencing the callback id is returned

#### Scenario: Dry-run preview before delete
- **WHEN** the delete-callback tool is invoked without confirmation and the client does not approve
- **THEN** no delete request is sent
- **AND** a dry-run preview stating the callback will be deleted is returned

### Requirement: Guided scheduled-callback prompt
The system SHALL provide an MCP prompt that walks an operator through the callback CRUD scenario (create, list, update, delete) using the callback tools and the write-safety approval gate.

#### Scenario: Prompt drives the CRUD walkthrough
- **WHEN** the scheduled-callback prompt is requested with an org id
- **THEN** the rendered prompt instructs the assistant to create, list, update, and delete callbacks using the callback tools
- **AND** instructs it to obtain explicit approval before each write

## REMOVED Requirements

### Requirement: Diagnose agent cannot go Available prompt
**Reason**: The read-only diagnose scenario duplicates the `validate_agent_routing` diagnostic tool and is being replaced by the scheduled-callback CRUD scenario as the lab's write-path teaching flow.
**Migration**: Use the `validate_agent_routing` tool directly for read-only availability diagnostics; the guided scenario is now scheduled-callback management. The `diagnose_agent_cannot_go_available` prompt and its server registration are removed.
