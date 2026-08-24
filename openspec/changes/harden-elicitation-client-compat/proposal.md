## Why

The `harden-elicitation-write-gate` change made the write gate honest: it now reports
exactly how each consent decision resolved instead of silently downgrading approvals to
dry-runs. That observability immediately paid for itself — the very first run against Codex
(build `26.818.41509`) produced `outcome: "cancelled"` while the operator reported clicking
**Accept**. So the gate is working, and it has pinned the fault outside the server.

But it pinned it only to a wall, not to a door. `cancelled` is where the trail ends, because
the gate deliberately discards the elicitation response body. That was a defensible privacy
choice for an `accept` — the body may hold user-typed data the server has no business
logging. It is the wrong choice for a refusal, because a refusal body is not a user
submission at all. It is whatever the client chose to attach, and the prevailing client
convention is to attach the reason it failed:

```js
// widely-copied client elicitation handler
setTimeout(() => rejectElicitation(id, 'Timeout: elicitation cancelled'), 60_000);
return promise.catch((err) => ({ action: 'cancel', content: { error: err.message } }));
```

Two facts follow, and together they define this change. First, `cancel` is **ambiguous by
construction** across the ecosystem: the specification defines it as "the user dismissed
without an explicit choice", while real clients also emit it to report their own timeouts
and internal errors. Second, the server is **throwing away the only field that
disambiguates them**. An operator who sees `cancelled` cannot tell whether a human declined
or the client broke, which is precisely the question they need answered.

This change closes that gap. It does not guess at Codex's behaviour; it makes the server
record what the client actually said, so the next occurrence is diagnosed from the log
rather than from a hypothesis. A low-risk compatibility improvement to the prompt schema
rides along, because the current empty-`properties` schema is a plausible contributor that
costs nothing to rule out.

### A second, worse finding — this one is ours

Running the same operation from a client with no elicitation support surfaced a defect the
predecessor change introduced. That gate resolved `unsupported` and fell back to `confirm`,
which the caller had left false, so the write could not commit. That much is correct and
specified. What is not correct is that **it can never commit from such a client**, because
the predecessor change rewrote every write tool's description to steer callers away from
`confirm`. Sync's now claims that "leaving it unset never prevents a sync the user
approved" — a statement that is false precisely where `confirm` is the only path there is.
We instructed the model never to send the one argument that makes a write possible on the
clients where the server cannot ask.

It compounds in two ways. First, none of the gate's reasoning reaches the caller: outcome
and reason go to stderr, so the model and the user in the chat window see an unexplained
dry-run and reasonably conclude the server always previews. Second, `sync` is the only write
tool that overwrites the shared dry-run message with its own planning summary, dropping the
"how to commit" hint the other tools carry — which is why sync is the one operation that
appears permanently stuck while `create_entry` quietly recovers on the same client.

So the gate's decision currently reaches nobody who can act on it: the operator gets an
outcome with no reason, and the caller gets no outcome at all. Both halves belong in this
change, because they are the same defect pointed at two different audiences.

## What Changes

- **Refusal diagnostics are preserved instead of discarded.** When the outcome is not
  `accepted`, the gate records the shape of the client's response body — its key names
  always, and the value of a small allow-list of diagnostic keys (`error`, `message`,
  `reason`), truncated. Bodies accompanying an `accept` remain unlogged, since those are the
  only ones that can carry user-submitted data.
- **The gate records how long the client took to answer.** An `elicit_ms` measurement
  separates a human decision (seconds) from a machine reflex (single-digit milliseconds).
  Nothing in the log answers that today: the `write_gate` and `tool.received` events sit
  microseconds apart in *every* run, because the gate resolves before `run_tool` begins, so
  human latency falls before the first of the two and there is nothing to measure it against.
- **The gate records which client answered.** The negotiated client name, version, and
  protocol version are attached to the event, so "which client did this, on what build"
  is answerable from the log. In a lab where every attendee brings a different client, this
  turns an unreproducible report into a filterable field.
- **The consent prompt becomes maximally client-compatible.** The requested schema gains a
  single *optional* boolean property so clients always have something concrete to render and
  submit, replacing the current empty `properties: {}` object. `required` stays empty, so
  the guarantee that any `accept` commits regardless of body is preserved unchanged.
- **`cancelled` is documented as ambiguous.** The lab guide's troubleshooting material
  currently reads `cancelled` as "you refused". It will instead teach operators to read
  `elicit_ms` and the recorded reason to tell a refusal from a client failure.
- **A write that did not commit tells its caller why.** The gate's outcome and a plain-language
  reason travel back in the tool's response, so the model can explain to the user that their
  client cannot prompt — rather than reporting a bare dry-run and leaving them to guess.
- **A caller blocked by an unaskable client is told how to proceed.** When the outcome is
  `unsupported` or `error`, the response states that `confirm` is required on this client, and
  the tool descriptions say the same. **This guidance is withheld when the user actually
  refused**, so a `declined` or `cancelled` write never invites the model to retry past a
  human's decision.
- **Every write tool gives the same dry-run feedback.** `sync` stops overwriting the shared
  message with a planning summary that omits how to commit, so no operation is silently the
  odd one out.
- **The inaccurate claim in the tool descriptions is corrected.** `confirm` is described as
  unnecessary *when the client can prompt* and required when it cannot, which is what the gate
  actually does.
- The gate's *decision* logic is deliberately untouched. Consent still derives from the
  action alone, refusals remain terminal, and the `confirm` fallback still applies only when
  no one could be asked. This change adds evidence, compatibility, and honest feedback — not
  new policy.

## Capabilities

### New Capabilities

- `mcp-write-gate-diagnostics`: What the write gate must record about a consent decision for
  an operator to distinguish a human refusal from a client-side failure — response-body
  diagnostics on refusal, round-trip timing, and client identity — together with the
  compatibility constraints the consent prompt must satisfy so that a client's approval is
  never lost in rendering.
- `mcp-write-gate-caller-feedback`: What a mutating tool must tell the caller that invoked it
  when a write did not commit — why it was blocked, and whether anything can be done about it
  — so a client that cannot prompt is a recoverable condition rather than a silent dead end,
  while a human's refusal remains final.

### Modified Capabilities

<!-- None. `mcp-write-gate` is defined as a delta in the not-yet-archived
     `harden-elicitation-write-gate` change and has no counterpart under openspec/specs/,
     so there is no synced requirement to modify. This change's requirements refine that
     delta's observability and prompt-schema rules; the two are reconciled when both are
     archived. The one rule that genuinely tightens — "elicited content is never logged" —
     is restated here in its narrowed form, scoped to accept bodies. -->

## Impact

- `wxcc-mcp-server/src/wxcc_mcp/_runtime.py` — `_ask_for_consent` returns the response body
  alongside its decision, `should_commit` enriches the `write_gate` event, `_CONSENT_SCHEMA`
  gains one optional property, and a redaction helper is added.
- `wxcc-mcp-server/tests/test_write_gate.py` — new coverage for body redaction, the
  diagnostic allow-list, timing, client identity, and a regression test pinning the schema
  to non-empty `properties` with empty `required`.
- `wxcc-mcp-server/tests/test_write_gate_e2e.py` — an end-to-end case proving a
  `cancel`-carrying-an-error round-trip is diagnosable from the emitted event.
- `wxcc-mcp-server/src/wxcc_mcp/tools/_helpers.py` — the shared dry-run response carries the
  gate outcome, a reason, and outcome-dependent guidance.
- `wxcc-mcp-server/src/wxcc_mcp/tools/sync.py` — the dry-run branch stops discarding the
  shared message, so sync matches every other write tool.
- `wxcc-mcp-server/src/wxcc_mcp/models/schemas.py` — `WriteOutput` and `SyncOutput` gain the
  fields needed to convey why a write was blocked.
- `wxcc-mcp-server/src/wxcc_mcp/server.py` — every write tool threads its gate outcome into
  the call, and the docstrings' claim about `confirm` is corrected.
- `wxcc-mcp-server/lab-guide/lab-guide.md` — the `write_gate` outcome table and
  troubleshooting Scenario F ("I approved but nothing changed") are revised for the
  ambiguity of `cancelled`, and a note covers clients without elicitation support.
- `openspec/changes/harden-elicitation-write-gate/design.md` — decision D2 (empty requested
  schema) is annotated with what was learned, so the record does not read as settled.
- No change to tool signatures, the WxCC API client, or any commit-path behaviour. No
  dependency changes. Log consumers gain fields and lose none.
