## Purpose

The shared human-in-the-loop confirmation gate that every mutating WxCC tool passes
through before it writes. It defines what counts as consent, when a non-interactive
fallback may be consulted, and how each gate decision is made auditable — so an approval
is never silently discarded and a refusal is never silently overridden.

## ADDED Requirements

### Requirement: Consent is determined by the client's action, not by the elicited body

The write gate SHALL decide consent solely from the elicitation action returned by the
client. A response whose action is `accept` SHALL be treated as approval regardless of the
shape, contents, or absence of the accompanying response body. The gate MUST NOT require
any field to be present in the elicited body in order to honour an approval.

#### Scenario: Client accepts with an empty body

- **WHEN** the client returns action `accept` with an empty response body (`{}`)
- **THEN** the gate SHALL report the outcome `accepted` and the write SHALL commit

#### Scenario: Client accepts with no body at all

- **WHEN** the client returns action `accept` with a null or omitted response body
- **THEN** the gate SHALL report the outcome `accepted` and the write SHALL commit

#### Scenario: Client accepts with unrecognized fields

- **WHEN** the client returns action `accept` with a body containing only fields the
  server did not request
- **THEN** the gate SHALL report the outcome `accepted` and the write SHALL commit

#### Scenario: Requested schema imposes no required fields

- **WHEN** the gate asks the client to confirm a write
- **THEN** the requested response schema SHALL declare no required fields, so that any
  syntactically valid submission satisfies it

### Requirement: An explicit refusal is final

The write gate SHALL treat an explicit refusal as a terminal decision. When the client
returns action `decline` or `cancel`, the gate SHALL NOT commit, and SHALL NOT consult the
non-interactive `confirm` fallback, even when that fallback is set to true.

#### Scenario: User declines while confirm is true

- **WHEN** the client returns action `decline` and the caller passed `confirm=true`
- **THEN** the gate SHALL report the outcome `declined` and the write SHALL NOT commit

#### Scenario: User cancels the prompt

- **WHEN** the client returns action `cancel`
- **THEN** the gate SHALL report the outcome `cancelled` and the write SHALL NOT commit

#### Scenario: Declined write returns a preview

- **WHEN** a write is refused at the gate
- **THEN** the tool SHALL return its dry-run preview and SHALL NOT report the operation as
  committed

### Requirement: The non-interactive fallback applies only when consent could not be obtained

The write gate SHALL consult the caller-supplied `confirm` argument only when interactive
consent was impossible — because no session context is available, the client does not
support elicitation, or the elicitation attempt failed. In every such case the gate SHALL
fail closed when `confirm` is absent or false.

#### Scenario: Client does not support elicitation

- **WHEN** the client offers no elicitation capability and the caller passed `confirm=true`
- **THEN** the gate SHALL report the outcome `unsupported` and the write SHALL commit

#### Scenario: Client does not support elicitation and no confirmation was given

- **WHEN** the client offers no elicitation capability and `confirm` is absent or false
- **THEN** the gate SHALL report the outcome `unsupported` and the write SHALL NOT commit

#### Scenario: Elicitation fails mid-flight

- **WHEN** the elicitation attempt raises a transport, protocol, or validation failure
- **THEN** the gate SHALL report the outcome `error` and SHALL fall back to the `confirm`
  argument, committing only if it is true

#### Scenario: No session context is available

- **WHEN** a write tool is invoked without a session context, such as from a test or script
- **THEN** the gate SHALL report the outcome `unsupported` and SHALL commit only if
  `confirm` is true

### Requirement: Every gate decision is observable

The write gate SHALL emit exactly one structured event per write-gate evaluation,
recording the outcome, the action being gated, and the correlation identifier of the
invocation. When the outcome is not `accepted`, the event SHALL carry a machine-readable
reason. The event MUST NOT contain any content submitted through the elicited body.

#### Scenario: Approved write is recorded

- **WHEN** the gate resolves an approval
- **THEN** a single structured event SHALL be emitted with outcome `accepted` and the
  invocation's correlation identifier

#### Scenario: Failure reason is recorded rather than swallowed

- **WHEN** the elicitation attempt fails
- **THEN** the emitted event SHALL carry outcome `error` together with a reason describing
  the failure, and the failure SHALL NOT be discarded without a record

#### Scenario: Unsupported client is distinguishable from a refusal

- **WHEN** an operator inspects the log stream after a write did not commit
- **THEN** the recorded outcome SHALL distinguish `declined` and `cancelled` from
  `unsupported` and `error`

#### Scenario: Elicited content is never logged

- **WHEN** the gate emits its event
- **THEN** the event SHALL contain no field values submitted by the user through the
  elicitation body

### Requirement: The gate behaves identically for every mutating tool

The write gate SHALL be the single decision point for all mutating tools, so that consent
semantics, fallback rules, and observability do not vary between operations. Tools SHALL
NOT implement their own confirmation logic.

#### Scenario: Consent semantics are uniform across write tools

- **WHEN** any mutating tool — creating, updating, or deleting an address book or entry,
  bulk-saving entries, assigning an address book to a desktop profile, or running the CRM
  sync — evaluates whether to commit
- **THEN** it SHALL obtain that decision from the shared gate and SHALL apply the same
  consent, fallback, and observability rules

#### Scenario: High-risk deletions use the same gate

- **WHEN** a destructive operation such as deleting an address book or entry is gated
- **THEN** the same consent rules SHALL apply, and the confirmation prompt SHALL identify
  the specific resource being destroyed

### Requirement: The confirmation prompt identifies the pending change

The confirmation prompt presented to the user SHALL describe the specific write awaiting
approval, so consent is informed rather than generic. For a batch operation the prompt
SHALL convey its scope, including whether entries absent from the source will be removed.

#### Scenario: Single-entry write prompt

- **WHEN** the gate asks for approval to create or modify one entry
- **THEN** the prompt SHALL name the affected resource

#### Scenario: Destructive batch scope is disclosed

- **WHEN** the gate asks for approval to run a sync configured to remove entries absent
  from the source
- **THEN** the prompt SHALL state that entries will be deleted before consent is given

### Requirement: The tool surface describes the fallback accurately

The published description of each mutating tool SHALL present `confirm` as a
non-interactive fallback rather than as the commit switch, and SHALL state that the server
requests user approval on its own. The description MUST NOT imply that passing
`confirm=false` prevents a write or that passing `confirm=true` bypasses the human.

#### Scenario: Caller relies on the tool description

- **WHEN** a model or client author reads a mutating tool's description to decide which
  arguments to send
- **THEN** the description SHALL make clear that the tool may be invoked without
  `confirm` and that approval will still be requested interactively
