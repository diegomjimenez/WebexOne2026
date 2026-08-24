## ADDED Requirements

### Requirement: List address books
The system SHALL provide a read-only tool that lists all address books in a WxCC
organization via the Config API (Address Book v2), returning each book's id, name,
description, and parent type.

#### Scenario: Books exist
- **WHEN** the tool is invoked with a valid `org_id`
- **THEN** the system returns a list of address books each with `id`, `name`,
  `description`, and `parent_type`

#### Scenario: No books exist
- **WHEN** the org has no address books
- **THEN** the system returns an empty list and a `total_returned` of 0

#### Scenario: Page size cap honored
- **WHEN** more books exist than the API page limit (100)
- **THEN** the system requests at most 100 per page and reports the returned count

### Requirement: Get address book by id
The system SHALL provide a read-only tool that returns a single address book's details by
id.

#### Scenario: Book found
- **WHEN** the tool is invoked with a valid `org_id` and existing `address_book_id`
- **THEN** the system returns the book's `id`, `name`, `description`, and `parent_type`

#### Scenario: Book not found
- **WHEN** the `address_book_id` does not exist
- **THEN** the system returns a plain-language not-found error

### Requirement: Create address book
The system SHALL provide a gated write tool that creates an address book with the required
`name` and `parent_type`, following the elicitation/dry-run safety pattern.

#### Scenario: Dry-run preview
- **WHEN** the tool is invoked without approval (no elicitation, `confirm=False`)
- **THEN** the system returns a preview of the address book to be created and makes no change

#### Scenario: Committed creation
- **WHEN** the admin approves (elicitation accept or `confirm=True`)
- **THEN** the system creates the address book and returns `committed=true` with the new id

#### Scenario: Missing required field
- **WHEN** `name` or `parent_type` is missing
- **THEN** the system rejects the request with a validation error before any API call

### Requirement: Update address book
The system SHALL provide a gated write tool that updates an existing address book's name or
description.

#### Scenario: Dry-run preview
- **WHEN** invoked without approval
- **THEN** the system returns a preview of the fields to change and makes no change

#### Scenario: Committed update
- **WHEN** the admin approves
- **THEN** the system updates the book and returns `committed=true`

### Requirement: Delete address book
The system SHALL provide a gated write tool that deletes an address book by id, treated as a
HIGH-risk operation requiring explicit approval.

#### Scenario: Dry-run preview with warning
- **WHEN** invoked without approval
- **THEN** the system returns a preview including a warning that deletion is permanent and
  makes no change

#### Scenario: Committed deletion
- **WHEN** the admin approves
- **THEN** the system deletes the book and returns `committed=true`

### Requirement: List address book entries
The system SHALL provide a read-only tool that lists entries within an address book,
supporting `search`, `filter`, and `attributes` query parameters and pagination.

#### Scenario: List all entries
- **WHEN** invoked with a valid `address_book_id`
- **THEN** the system returns entries each with `id`, `name`, and `number`

#### Scenario: Search and filter
- **WHEN** invoked with a `search` keyword or RSQL `filter`
- **THEN** the system returns only the matching entries

### Requirement: Get address book entry by id
The system SHALL provide a read-only tool that returns a single entry's details by id.

#### Scenario: Entry found
- **WHEN** invoked with valid `address_book_id` and `entry_id`
- **THEN** the system returns the entry's `id`, `name`, and `number`

#### Scenario: Entry not found
- **WHEN** the `entry_id` does not exist
- **THEN** the system returns a plain-language not-found error

### Requirement: Create address book entry
The system SHALL provide a gated write tool that creates an entry with the required `name`
and `number` (E.164), following the safety pattern.

#### Scenario: Dry-run preview
- **WHEN** invoked without approval
- **THEN** the system returns a preview of the entry to be created and makes no change

#### Scenario: Committed creation
- **WHEN** the admin approves
- **THEN** the system creates the entry and returns `committed=true` with the new entry id

#### Scenario: Invalid phone number
- **WHEN** `number` is not valid E.164
- **THEN** the system rejects the request with a validation error before any API call

### Requirement: Update address book entry
The system SHALL provide a gated write tool that updates an entry's name or number.

#### Scenario: Committed update
- **WHEN** the admin approves an update to an existing entry
- **THEN** the system updates the entry and returns `committed=true`

### Requirement: Delete address book entry
The system SHALL provide a gated write tool that deletes an entry by id.

#### Scenario: Committed deletion
- **WHEN** the admin approves
- **THEN** the system deletes the entry and returns `committed=true`

### Requirement: Bulk save entries
The system SHALL provide a gated write tool that saves multiple entries in one operation via
the bulk-save API.

#### Scenario: Dry-run preview of bulk save
- **WHEN** invoked without approval with a set of entries
- **THEN** the system returns a preview summarizing the count of entries to be saved and
  makes no change

#### Scenario: Committed bulk save
- **WHEN** the admin approves
- **THEN** the system saves all entries and returns `committed=true` with a per-entry result
