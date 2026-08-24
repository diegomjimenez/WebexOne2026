## Context

See `proposal.md` — Why, for the motivation and the reproduced failure.

The gate is one function, `should_commit()` in `wxcc-mcp-server/src/wxcc_mcp/_runtime.py`,
which every mutating tool in `server.py` awaits before doing work. That concentration is
the reason a single defect disabled consent across nine tools — and the reason one fix
restores all nine.

Three facts about the pinned SDK (`mcp` 1.27.0) shape the approach:

1. `Context.elicit(message, schema)` delegates to `elicit_with_validation()`, which
   validates the client's response body against the Pydantic schema **before** returning.
   An `accept` whose body does not satisfy the schema raises `ValidationError`; an `accept`
   with a null body falls through the action branches and raises
   `ValueError("Unexpected elicitation action: accept")`. Either way the caller never
   receives a result object, so no post-hoc inspection of `result.action` can recover the
   approval.
2. `ServerSession.elicit_form(message, requestedSchema, related_request_id)` is the layer
   beneath it. It performs the round trip and returns a raw `ElicitResult` carrying
   `action` and `content`, with no schema enforcement. This is the same wire request —
   `elicit_with_validation` is a thin wrapper over it — so calling it directly changes
   nothing observable to the client.
3. `ServerSession.check_client_capability(ClientCapabilities(elicitation=...))` reports
   whether the peer negotiated elicitation at all, and returns `False` when no client
   params were exchanged. This is what makes `unsupported` distinguishable from `error`
   rather than both arriving as an anonymous exception.

Constraints carried over from the surrounding design: the gate must stay fail-closed, must
not emit anything on stdout (stdio transport), and must keep working with no session
context so the existing test suite and any scripted use continue to function.

## Goals / Non-Goals

**Goals:**

- Consent survives any response-body shape a conformant client may send.
- The four non-committing outcomes are told apart in the log, so "the user said no" is
  never confused with "the client cannot ask".
- One decision point keeps its authority: tools continue to receive a single boolean.
- Existing non-interactive callers (tests, scripts) keep working unchanged.

**Non-Goals:**

- Rewriting the lab's elicitation *teaching* beat. `add-elicitation-experience` owns the
  hands-on approve/decline drill; this change only makes that drill trustworthy.
- Per-tool risk tiers, step-up confirmation, or typed elicitation for anything other than
  consent. A future change may collect structured input (for example a reason-for-change
  field) — this design deliberately keeps consent free of payload coupling so that
  addition does not reintroduce the defect.
- Persisting an approval audit trail beyond the existing structured log stream.
- Changing the MCP wire protocol or the pinned SDK version.

## Decisions

### D1: Call `session.elicit_form()` directly instead of `ctx.elicit()`

The gate issues the elicitation request itself and interprets the raw `action`.

*Why:* consent is a three-state answer — approve, refuse, withdraw. Routing it through a
typed-form parser adds a fourth outcome that exists only as an exception, and that outcome
is indistinguishable from a genuine failure. Dropping to the layer beneath removes the
class of bug rather than the instance: no future client body shape can invalidate an
approval, because the body is never read.

*Alternatives considered:*

- **Give `approve` a default of `True` so `model_validate({})` succeeds.** Fixes the
  empty-body case only. The null-body case still raises `ValueError` inside the SDK, and a
  client sending `{"approve": false}` alongside an `accept` action would produce a
  contradictory answer the gate must then arbitrate. Rejected as a partial fix that leaves
  the conflation in place.
- **Keep `ctx.elicit()` and catch `ValidationError` / `ValueError` as implicit approval.**
  Treats a parse failure as consent, which is the wrong default for a safety gate: a
  genuine protocol error would then commit a write. Rejected on safety grounds.
- **Drop elicitation and rely on `confirm` alone.** Moves the commit decision from the
  human back to the model — the opposite of the property the server exists to demonstrate.
  Rejected.

### D2: Request a schema with no required fields

The requested schema stays a valid JSON Schema object so clients that render a form have
something to render, but declares nothing required.

*Why:* clients differ in how they answer a body-less confirmation, and the server has no
say in that. A schema with no required fields is satisfiable by every one of those
behaviours — `{}`, an omitted body, or extra keys — which turns a cross-client
compatibility problem into a non-event. The removed `approve` boolean was never read for
anything other than the redundant second gate.

*Trade-off:* the prompt loses its explicit checkbox. That is the intended outcome — the
checkbox was the footgun, and `Accept` already carries the semantics.

> **Superseded in part by `harden-elicitation-client-compat`.** "No required fields" was the
> right constraint and still holds. Going all the way to `properties: {}` was one step too
> far: a form with nothing in it can render with no control to submit, leaving dismissal as
> the only exit — and dismissal is `cancel`. The schema now declares a single *optional*
> `acknowledge` boolean, so there is always something to draw, while `required` stays empty
> so every approval body remains valid. The claim above that this "turns a cross-client
> compatibility problem into a non-event" was too confident: it removed the schema's ability
> to *reject* an approval, not its ability to be *unrenderable*.

### D3: Model the result as an explicit outcome, not a bare boolean

The gate resolves to one of `accepted`, `declined`, `cancelled`, `unsupported`, `error`,
and derives the boolean from it. Only `unsupported` and `error` consult `confirm`.

*Why:* the boolean is what the tools need, but it is not enough to reason about. Collapsing
five distinct situations into `False` at the moment of decision is precisely what made this
bug invisible for three debugging rounds. Keeping the outcome explicit lets the same value
drive the commit decision, the log event, and the tests — so the taxonomy cannot drift out
of sync with behaviour.

This also fixes a latent bug of its own: today a `decline` returns early and never reaches
the `confirm` fallback, but only by accident of control flow. Making refusal terminal by
construction means a caller passing `confirm=True` can never override a human "no".

*Alternative considered:* keep returning a boolean and log separately at each call site.
Rejected — nine call sites, nine chances for the log and the decision to disagree.

### D4: Probe client capability before attempting elicitation

`check_client_capability` is consulted first. A negative answer yields `unsupported`
without a round trip; only a genuine failure during an attempted elicitation yields
`error`.

*Why:* these two cases need different operator responses — one is "configure a capable
client", the other is "investigate a fault" — and an exception message cannot reliably
tell them apart. Probing also avoids issuing a request that is known to fail.

*Note:* the probe is an optimisation for classification, not a security boundary. The
`error` path still catches everything, so a client that advertises elicitation and then
misbehaves is handled identically to one that never advertised it — both fail closed.

### D5: Emit one `write_gate` event carrying the decision, never the content

A single structured event per gate evaluation, on the existing stderr-native structured
stream, inheriting `request_id` from the contextvars already bound by `run_tool`.

*Why:* the gate was the one unobserved step in an otherwise glass-box server; every
neighbouring stage already narrates itself. One event per evaluation keeps the correlation
story readable — a learner greps a six-character id and sees the gate decision in sequence
with the API calls that followed, or the absence of them.

Elicited content is excluded deliberately: bodies may carry user-typed text, and the gate
has no need for it. Logging the decision and not the payload keeps the event safe to ship
at info level and satisfies the project's redaction posture.

*Ordering note:* `should_commit()` runs before `run_tool()` binds the correlation id, so
the event must be emitted with the id explicitly available to the gate. The gate therefore
accepts the correlating context from its caller rather than assuming ambient state — the
alternative, reordering the tools so `run_tool` wraps the gate, would put a blocking user
prompt inside the timed region and corrupt every `elapsed_ms` measurement in the lab's
logging chapter.

### D6: Correct the `confirm` contract in the tool descriptions

Write-tool docstrings describe `confirm` as a fallback for non-interactive clients and
state that the server requests approval itself.

*Why:* the tool description is the only specification a model reads. The reproduced session
shows the consequence of a misleading one: the assistant, having been asked for a preview,
passed `confirm=False` and then reported the server was "failing to recognize the commit
flag" — a coherent inference from the description it was given. Fixing the wording is part
of fixing the behaviour, not documentation cleanup.

## Risks / Trade-offs

- **Bypassing `ctx.elicit()` couples the gate to a lower SDK surface** → `elicit_form` is a
  public method on `ServerSession` and is what `ctx.elicit()` itself calls; the wire
  request is unchanged. Confine the call to `should_commit()` so an SDK change touches one
  function, and cover it with the client-matrix tests from the spec.
- **A client that auto-accepts without showing a prompt would commit** → true before this
  change too, and out of the server's control: the protocol delegates presentation to the
  client. The prompt states the concrete pending change (spec: *The confirmation prompt
  identifies the pending change*), so an agent relaying it has the scope it needs. Noted in
  the lab guide as a client-trust boundary.
- **Approvals that previously fell through now commit** → this is the intent, and it is the
  one behavioural reversal in the change. It is safe because it only converts a discarded
  `accept` into an honoured one; no path that previously refused begins to commit.
- **Losing the checkbox reduces the visible ceremony of a destructive write** → prompt text
  carries the weight instead, including explicit disclosure when a sync will delete
  entries. Destructive tools keep their `HIGH risk` marking.
- **An extra log line per write** → one event, at info, on a stream the lab already teaches
  learners to read. Net negative cost: it replaces the silent-failure mode that made this
  defect take three attempts to find.

## Migration Plan

No data migration, no configuration change, no client-side change. The behavioural
reversal is confined to a previously-broken path.

1. Land the gate change in `_runtime.py`, then the docstrings, resource wording, and lab
   guide — the gate is the only functional edit; the rest align the description with it.
2. Verify with the client-matrix tests, then confirm end to end against Codex: accepting
   must commit, declining must leave the directory untouched, and both must be visible as
   `write_gate` events sharing the invocation's `request_id`.
3. Confirm existing write tests still pass unchanged through the `unsupported` path, which
   proves the non-interactive fallback survived.

**Rollback:** revert the commit. The gate fails closed at every outcome, so a rollback
returns to over-refusing writes rather than over-committing them — never data loss.

## Open Questions

*(none outstanding)*

## Resolved Questions

- **Does `write_gate` belong in the lab guide's log-correlation cheat-sheet as a first-class
  lifecycle stage, alongside `received` / `auth` / `api` / `result`?** **Yes** — added as a
  `Gate (writes only)` row, plus a Scenario F entry in the troubleshooting matrix. The
  deciding argument is that the cheat-sheet's whole method is "read which stages are present
  or absent", and consent is a stage that can independently fail. Without the row, a gate
  failure presents as a successful dry-run with no stage missing, which is exactly the
  invisibility this change set out to remove. The row records the ordering rationale too:
  the gate precedes `tool.received` because it blocks on a human, and timing it would turn
  every `elapsed_ms` into a measure of operator reaction time.

- **Does the real SDK actually reject conforming approvals, or was the fake session masking
  something?** Confirmed against the real SDK. Driving an in-memory `ClientSession` against
  the pre-fix gate reproduced the defect exactly: `accept` with an empty body, an absent
  body, and an unknown-key body all returned `committed=False, dry_run=True`. The same
  harness is retained as `tests/test_write_gate_e2e.py`.

  One correction this surfaced: an early reading of the unit-test failures suggested the old
  gate also let `confirm=True` override an explicit `decline`. It did not — that failure was
  an artefact of the fake session not implementing `ctx.elicit`. Against the real SDK the old
  gate handled refusals correctly, because the SDK validates the response body only on
  `accept`. The refusal-is-terminal requirement is therefore a hardening guarantee rather
  than a bug fix, and is now enforced by construction.
