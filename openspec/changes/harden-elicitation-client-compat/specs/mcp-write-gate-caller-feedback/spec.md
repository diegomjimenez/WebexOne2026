## Purpose

What a mutating tool must tell the caller that invoked it when a write did not commit: why it
was blocked, and whether anything can be done about it. A client that cannot prompt the user
should be a recoverable condition the caller can act on, not a silent dead end — while a
human's refusal must stay final no matter how the caller responds to it.

## ADDED Requirements

### Requirement: A write that did not commit explains why

When a mutating tool returns without committing, its response SHALL convey the gate outcome
that blocked it and a plain-language reason. A caller SHALL NOT have to consult the server's
log stream to learn why the operation previewed instead of applying.

#### Scenario: Blocked write names its cause

- **WHEN** a mutating tool returns a preview because the gate did not approve the write
- **THEN** the response SHALL identify which outcome blocked it and describe that outcome in
  plain language

#### Scenario: Committed write needs no explanation

- **WHEN** a mutating tool commits
- **THEN** its response SHALL report the commit and SHALL NOT carry blocking-reason fields

#### Scenario: Caller can distinguish a refusal from an unaskable client

- **WHEN** a caller inspects the response of a write that did not commit
- **THEN** it SHALL be able to tell that the user refused from that the user could not be
  asked, without further calls

### Requirement: The caller-facing reason is authored by the server

The reason returned to the caller SHALL be composed by the server from the gate outcome. The
response MUST NOT embed text supplied by the client through its elicitation response, because
that text is untrusted input and the response is consumed by a language model.

#### Scenario: Client-supplied error text is not relayed to the caller

- **WHEN** a client refuses with a body containing its own error description
- **THEN** that description SHALL appear in the server's log stream and SHALL NOT appear in
  the tool's response

#### Scenario: Reason is stable for a given outcome

- **WHEN** two writes are blocked by the same outcome
- **THEN** both SHALL return the same server-authored reason, independent of what the client
  attached

### Requirement: Guidance to retry is given only when consent could not be obtained

When the gate could not obtain a decision — no session, an unsupported client, or a failed
attempt — the response SHALL state that the non-interactive confirmation argument is required
on this client. When the user refused, the response MUST NOT suggest retrying, MUST NOT
mention the confirmation argument as a way forward, and MUST NOT imply the decision can be
overridden.

#### Scenario: Unaskable client is told how to proceed

- **WHEN** a write is blocked because the client does not support elicitation
- **THEN** the response SHALL state that the confirmation argument is required for this client
  to write

#### Scenario: Refusal is not presented as retryable

- **WHEN** a write is blocked because the user declined or cancelled
- **THEN** the response SHALL NOT suggest retrying and SHALL NOT reference the confirmation
  argument

#### Scenario: Retrying a refusal does not commit

- **WHEN** a caller ignores the response and re-invokes the tool with confirmation set after a
  refusal
- **THEN** the gate SHALL ask again, and the write SHALL commit only if the user approves that
  new request

#### Scenario: Failed elicitation is treated as unaskable

- **WHEN** a write is blocked because the elicitation attempt failed rather than being refused
- **THEN** the response SHALL state that confirmation is required, since no decision was
  obtained

### Requirement: Every mutating tool reports a blocked write the same way

All mutating tools SHALL convey a blocked write through the same fields and the same
guidance rules, so no operation appears permanently stuck while another recovers under
identical conditions. A tool MAY add its own descriptive summary, but SHALL NOT do so in place
of the shared explanation.

#### Scenario: Composite operation matches single-resource operations

- **WHEN** the CRM sync is blocked by the same outcome as a single-entry write on the same
  client
- **THEN** both SHALL convey the same outcome, reason, and guidance

#### Scenario: Tool-specific summary supplements rather than replaces

- **WHEN** a tool has a meaningful summary of its own, such as a planned change count
- **THEN** that summary SHALL accompany the shared explanation rather than displacing it

### Requirement: A write committed without human approval discloses that

When a write commits because interactive consent was impossible and the caller supplied the
non-interactive confirmation, the response SHALL disclose that it committed without a human
approving it, so the fact is visible to whoever reads the result.

#### Scenario: Non-interactive commit is marked

- **WHEN** a write commits on the non-interactive fallback path
- **THEN** the response SHALL record that no interactive approval was obtained

#### Scenario: Approved commit is not marked

- **WHEN** a write commits because the user approved it
- **THEN** the response SHALL NOT carry the non-interactive disclosure

### Requirement: Tool descriptions state when confirmation is required

The published description of each mutating tool SHALL state that the confirmation argument is
unnecessary when the client can prompt the user, and required when it cannot. A description
MUST NOT assert that omitting confirmation never prevents an approved write, because that is
untrue on a client without elicitation support.

#### Scenario: Description covers the unaskable client

- **WHEN** a caller reads a mutating tool's description to decide which arguments to send
- **THEN** the description SHALL make clear that a client unable to prompt requires the
  confirmation argument for the write to commit

#### Scenario: Description does not promise confirmation is always optional

- **WHEN** a mutating tool's description explains the confirmation argument
- **THEN** it SHALL NOT claim that leaving it unset can never prevent a write the user
  approved
