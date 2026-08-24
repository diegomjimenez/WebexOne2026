## Purpose

What the write gate must record about a consent decision so an operator can tell a human
refusal apart from a client-side failure, and the compatibility constraints the consent
prompt must satisfy so an approval is never lost in the client's rendering of it. The write
gate itself decides whether to commit; this capability governs whether that decision can be
explained afterwards without re-running it.

## ADDED Requirements

### Requirement: A refusal carries the client's stated reason

When a consent decision resolves to anything other than an approval, the gate SHALL record
what the client returned alongside its refusal, because clients use a refusal to report
their own failures as well as a user's choice. The recorded evidence SHALL name every field
the client attached, and SHALL include the value of fields conventionally used to carry a
failure description. Values SHALL be bounded in length so a hostile or verbose client cannot
flood the log.

#### Scenario: Client reports its own failure through a cancellation

- **WHEN** the client returns action `cancel` with a body describing an error, such as a
  timeout or an internal fault
- **THEN** the emitted gate event SHALL include that description, so the operator learns the
  client failed rather than that the user refused

#### Scenario: Refusal body field names are always recorded

- **WHEN** the client returns a refusal with a body whose fields are not recognized as
  carrying a failure description
- **THEN** the emitted gate event SHALL still record the names of those fields, so an
  unexpected client convention is visible without exposing its values

#### Scenario: Refusal carries no body

- **WHEN** the client returns a refusal with an empty or absent body
- **THEN** the emitted gate event SHALL record that no reason was supplied, and SHALL NOT
  imply one

#### Scenario: Oversized reason is truncated

- **WHEN** a client attaches a failure description longer than the recorded limit
- **THEN** the emitted gate event SHALL contain a truncated form of it and SHALL remain a
  single well-formed event

### Requirement: An approval's body is never recorded

The gate SHALL NOT record any field value submitted alongside an approval. An approval is
the only response whose body can contain data the user typed, and the gate has no use for
that data because consent is determined by the action alone.

#### Scenario: Approval with a populated body

- **WHEN** the client returns action `accept` with a body containing field values
- **THEN** the emitted gate event SHALL contain none of those values

#### Scenario: Approval body values are not recoverable from the event

- **WHEN** an operator inspects the gate event for an approved write
- **THEN** the event SHALL convey that the write was approved without disclosing what was
  submitted to approve it

### Requirement: The gate records how long the client took to answer

The gate SHALL record the elapsed time between issuing the consent request and receiving the
client's response. This measurement SHALL be recorded for every outcome in which a request
was actually issued, so that a decision made by a human is distinguishable from one made
reflexively by software.

#### Scenario: A human decision is distinguishable from an automatic one

- **WHEN** an operator inspects a refusal that the user believes they approved
- **THEN** the recorded elapsed time SHALL show whether a human had the opportunity to
  respond, or whether the client answered too quickly for that to be possible

#### Scenario: No request was issued

- **WHEN** the gate never issues a consent request, because no session was available or the
  client does not support the capability
- **THEN** the event SHALL omit an elapsed time rather than report a misleading zero

#### Scenario: Timing survives a failed attempt

- **WHEN** the consent request is issued and then fails
- **THEN** the event SHALL record how long the attempt ran before failing

### Requirement: The gate records which client answered

The gate SHALL attach the identity of the connected client — its reported name and version,
and the negotiated protocol version — to each gate event, so a decision can be attributed to
a specific client build without asking the operator which one they were using.

#### Scenario: Attributing a refusal to a client build

- **WHEN** a gate event records a refusal
- **THEN** the event SHALL identify the client and version that produced it

#### Scenario: Client identity is unavailable

- **WHEN** the connected peer did not report its identity
- **THEN** the event SHALL record that the identity is unknown and SHALL still be emitted

### Requirement: The consent prompt is renderable and submittable by every client

The requested response schema for a consent prompt SHALL give the client at least one
property to render, so that no client is asked to present a form with nothing in it. The
schema SHALL declare no required fields, so that a client submitting an empty, absent, or
unrecognized body still produces a valid approval. Together these ensure a client can always
render an approval affordance and that whatever it submits is accepted.

#### Scenario: Schema offers something to render

- **WHEN** the gate issues a consent request
- **THEN** the requested schema SHALL declare at least one property

#### Scenario: Schema requires nothing

- **WHEN** the gate issues a consent request
- **THEN** the requested schema SHALL declare no required fields

#### Scenario: Approval remains valid without the offered property

- **WHEN** the client returns an approval that omits the property the schema offered
- **THEN** the write SHALL commit, because the property exists for the client to render and
  not for the server to read

#### Scenario: Offered property is not treated as consent

- **WHEN** the client returns an approval in which the offered property is set to a value
  suggesting refusal
- **THEN** the gate SHALL still treat the response as an approval, because the action alone
  determines consent

### Requirement: Documentation presents a cancellation as ambiguous

Operator-facing documentation SHALL present a cancelled outcome as having two possible
causes — a user who dismissed the prompt, and a client that failed to deliver the user's
answer — and SHALL direct the reader to the recorded reason, elapsed time, and client
identity to tell them apart. It MUST NOT describe a cancellation as proof that the user
refused.

#### Scenario: Operator diagnoses an approval that did not commit

- **WHEN** an operator follows the documentation after approving a write that did not commit
- **THEN** the documentation SHALL direct them to the recorded reason, elapsed time, and
  client identity, and SHALL explain what each one indicates

#### Scenario: Outcome reference does not overstate a cancellation

- **WHEN** the documentation's reference of gate outcomes describes a cancellation
- **THEN** it SHALL state that the client may have reported its own failure this way
