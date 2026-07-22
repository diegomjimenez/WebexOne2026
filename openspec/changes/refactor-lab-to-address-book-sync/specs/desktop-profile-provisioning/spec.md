## ADDED Requirements

### Requirement: List desktop profiles
The system SHALL provide a read-only tool that lists desktop profiles in the organization,
returning each profile's id, name, and currently assigned `addressBookId` (if any), and
SHALL NOT read or return the deprecated fields `dialPlans`, `agentDNValidationCriteria`, or
`agentDNValidationCriterions`.

#### Scenario: Profiles returned with address book link
- **WHEN** invoked with a valid `org_id`
- **THEN** the system returns desktop profiles each with `id`, `name`, and `address_book_id`

#### Scenario: Deprecated fields excluded
- **WHEN** the API response contains deprecated dial-plan fields
- **THEN** the system does not surface them in its output

### Requirement: Get desktop profile by id
The system SHALL provide a read-only tool that returns a single desktop profile's details,
including its assigned `addressBookId`.

#### Scenario: Profile found
- **WHEN** invoked with a valid `org_id` and existing `profile_id`
- **THEN** the system returns the profile `id`, `name`, and `address_book_id`

#### Scenario: Profile not found
- **WHEN** the `profile_id` does not exist
- **THEN** the system returns a plain-language not-found error

### Requirement: List agents
The system SHALL provide a read-only tool that lists agents (users) in the organization,
returning identity fields and the desktop profile assigned to each agent.

#### Scenario: Agents returned with profile assignment
- **WHEN** invoked with a valid `org_id`
- **THEN** the system returns agents each with an identifier and their assigned desktop
  profile id

### Requirement: Get agent by id
The system SHALL provide a read-only tool that returns a single agent's details, including
the agent's assigned desktop profile id.

#### Scenario: Agent found
- **WHEN** invoked with a valid `org_id` and existing agent identifier
- **THEN** the system returns the agent's identity and assigned desktop profile id

### Requirement: Map desktop profiles to agents
The system SHALL surface which desktop profile is assigned to which agent so an operator can
determine the impact of assigning an address book to a profile.

#### Scenario: Mapping derived from reads
- **WHEN** the operator requests the profile-to-agent mapping for the org
- **THEN** the system returns, for each desktop profile, the agents assigned to it

### Requirement: Assign address book to desktop profile
The system SHALL provide a gated write tool that assigns an address book to a desktop
profile by setting the profile's `addressBookId`, following the elicitation/dry-run safety
pattern and without modifying deprecated profile fields.

#### Scenario: Dry-run preview
- **WHEN** invoked without approval with a `profile_id` and `address_book_id`
- **THEN** the system returns a preview showing the current and proposed `addressBookId` and
  makes no change

#### Scenario: Committed assignment
- **WHEN** the admin approves
- **THEN** the system updates the profile's `addressBookId` and returns `committed=true`

#### Scenario: Existing profile fields preserved
- **WHEN** the assignment is committed
- **THEN** the system preserves all other (non-deprecated) profile fields unchanged

#### Scenario: Verify after assignment
- **WHEN** the assignment is committed
- **THEN** re-reading the profile shows the new `address_book_id`
