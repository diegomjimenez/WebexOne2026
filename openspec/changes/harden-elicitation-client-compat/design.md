## Context

See `proposal.md` — Why. The constraints that shape the approach:

**The gate already resolves correctly.** `should_commit` reads the elicitation `action` and
nothing else, and refusals are terminal. That logic is not in question and this design does
not touch it. What is missing is evidence, not policy.

**`elicit_form` performs no response validation.** Verified against the installed SDK:
`ServerSession.elicit_form` forwards the request and returns the raw `ElicitResult`. So the
server is not rejecting Codex's approval — the client genuinely sent `action: "cancel"`. This
rules out the entire class of explanation that the predecessor change was built to fix, and
is why that change alone could not resolve the observed symptom.

**The `ElicitResult` we already hold contains the answer we discarded.** `content` is present
on the result regardless of action. `_ask_for_consent` collapses the result to a
`_GateDecision(outcome, reason)` and lets the body fall out of scope, so by the time
`should_commit` builds its event the evidence is unreachable.

**What the observed log actually tells us: less than it appears.** The reported `write_gate`
and `tool.received` events shared a timestamp to the microsecond, which initially looked like
proof that no human was in the loop. It is not — see the correction below. The log as it
stands cannot answer how long the client took, which is the one question that separates the
two readings of a `cancel`.

**The evidence is a lab artifact, not just a debugging aid.** This server teaches MCP. An
attendee whose approval does not commit needs to reach a correct conclusion from the log
alone, without a maintainer present.

**An earlier inference in this investigation was wrong, and correcting it matters.** The
observation that `write_gate` and `tool.received` shared a timestamp was read as proof that
no human participated. It proves nothing. The gate resolves *before* `run_tool` begins, so
those two events are adjacent statements and are always microseconds apart regardless of how
long the user deliberated; human latency falls *before* `write_gate`, where no preceding event
exists to measure against. A run from a client that resolved `unsupported` — a path with no
round-trip at all — produced the identical timestamp signature, confirming the two cases are
indistinguishable today. This does not weaken the case for D3; it is the case for D3, since
the log currently cannot answer the question at all.

**Three distinct paths now end in the same visible symptom**, which is why the symptom was
read as one bug:

```
elicitation OK  →  accept    →  commit
elicitation OK  →  cancel    →  refusal, terminal   →  dry-run   (Codex; cause unknown)
no elicitation  →  never asked →  falls back to confirm=false →  dry-run   (our defect)
```

**The third path is a dead end we built.** The gate is correct — the spec sanctions
committing on `unsupported` when `confirm` is true. But the predecessor change rewrote every
write tool's description to steer callers away from `confirm`, including the claim that
"leaving it unset never prevents a sync the user approved". On a client without elicitation
that claim is false and the steer is fatal: the model does not send `confirm`, the server
cannot ask, and the write can never commit.

**`sync` diverges from every other write tool.** Other writes return the shared
`dry_run_response`, whose message is "Set confirm=True to commit this change." — a hint the
model can act on, which is why `create_entry` accidentally recovers on a limited client. The
sync dry-run branch replaces that message with `deterministic_summary`, an accurate plan with
no indication of how to proceed. Sync therefore appears permanently stuck under conditions
where its siblings do not.

**Nothing the gate knows reaches the caller.** Outcome and reason go to stderr. The model and
the user in the chat see an unexplained dry-run, which is exactly the evidence from which an
operator concludes the server always previews.

## Goals / Non-Goals

**Goals:**

- Make a non-committing write self-explanatory from a single log event: what the client
  said, how long it took, and which client it was.
- Make a non-committing write self-explanatory to its *caller* too, so a client that cannot
  prompt is a recoverable condition rather than a silent dead end.
- Keep a human's refusal final while making an unaskable client recoverable — the two must not
  be conflated in either direction.
- Keep the privacy line defensible by drawing it where the risk actually is — the approval
  body — rather than across all bodies uniformly.
- Remove the empty-`properties` schema as a variable, at no cost to the accept guarantee.
- Leave every commit-path behaviour byte-for-byte identical.

**Non-Goals:**

- Diagnosing Codex from first principles. This design makes the client's own answer
  legible; it does not model the client's internals or branch on client identity.
- Working around a refusal. If a client says `cancel`, the write must not commit, whatever
  the reason. Fail-closed is preserved even when the reason proves the refusal was spurious.
- Retrying, or offering a "are you sure you meant to cancel?" second prompt. Re-prompting on
  a refusal trains users to click through gates and is exactly the fatigue the MCP security
  guidance warns against.
- Reading the offered schema property as consent. It exists for the client to render.

## Decisions

### D1. Carry the response body out of `_ask_for_consent`, redact it at the log boundary

`_GateDecision` gains a third field holding the raw response body. `should_commit` — the one
place that already owns the event — decides what is safe to record. Redaction happens once,
where the outcome is known, rather than inside the function that does not yet know whether
this was an approval.

*Alternative — log inside `_ask_for_consent`:* it would have to emit a second event or
duplicate the outcome logic, and the spec requires exactly one event per evaluation.

*Alternative — return a pre-redacted string:* pushes a presentation concern into the
consent-reading function and makes the redaction rule harder to test in isolation.

### D2. Redact by structure, disclose by allow-list

For a refusal: record every key name, and the value only for `error`, `message`, and
`reason`, coerced to string and truncated (256 characters). For an approval: record nothing.

Key names are structural metadata — knowing a client sent `{"error": ...}` versus
`{"userNote": ...}` is what makes an unfamiliar convention visible, and a key name is chosen
by the client, not typed by the user. Values are where user text can appear, so only the
three keys the ecosystem uses for machine-generated failure descriptions are disclosed.

*Alternative — log refusal bodies verbatim:* simplest, and defensible on the argument that a
refusal body is never a user submission. Rejected because "never" is a claim about all
current and future clients, and a truncated allow-list costs almost nothing.

*Alternative — key names only, no values:* would record that Codex sent an `error` key but
not what it said, which is the one thing we need.

*Alternative — hash the values:* useless here; nobody has a rainbow table of client error
strings, and the point is to read them.

### D3. Time the round-trip, and omit the field when no request was issued

Measure with `time.perf_counter()` around the `elicit_form` await only. Record `elicit_ms`
when a request was issued — including when it then failed — and omit the field entirely
when the gate short-circuited to `unsupported` before asking.

Omission rather than `0` or `null`: a zero would read as "answered instantly", which is the
exact signal being measured, so a never-asked case must not be able to counterfeit it.

This measurement stays outside `run_tool`'s timer, preserving the existing property that
`elapsed_ms` reflects work and not human deliberation.

### D4. Read client identity from the negotiated session, tolerate its absence

Take `session.client_params.clientInfo` (name, version) and the negotiated protocol version.
Every access is defensive — this is a diagnostic field and must never be the reason a gate
event fails to emit. When identity is unavailable, record it as unknown and continue.

*Alternative — require the operator to state their client:* that is the status quo, and it
is what turned this investigation into a multi-round exchange.

### D5. One optional property in the requested schema

```
properties: { "acknowledge": { type: "boolean", title: "Apply this change", default: true } }
```
with `required` still absent.

The rationale is narrow and worth stating precisely, because the predecessor change decided
the opposite and that record should not read as settled. Codex uses
`{"type":"object","properties":{}}` for its *own* exec-approval elicitations, which is strong
evidence that an empty-properties schema is a shape it understands — as a client *receiving*
one. It is weaker evidence about how its UI renders a form with no fields when *another*
server sends one: a form with nothing to fill in may present no submit affordance, leaving
dismissal as the only exit, and dismissal is `cancel`. That is a hypothesis, not a finding.

It is adopted anyway because the cost is provably zero. With `required` empty, every
guarantee in the predecessor's spec — accept with `{}`, accept with no body, accept with
unrecognized fields — is untouched, and D6 pins that with a test. A hypothesis that costs
nothing to eliminate should be eliminated rather than argued about.

*Alternative — leave the schema empty and wait for the diagnostics:* strictly more
disciplined, and tempting. Rejected because the diagnostics require another live Codex
session to produce data, and if the schema is the cause we would have spent that session
confirming something we could have fixed in the same commit.

*Alternative — mark the property required:* reintroduces the original defect exactly. Any
client that approves without populating it produces a response the schema rejects.

### D6. Pin the schema shape with a regression test

Assert `properties` is non-empty **and** `required` is empty-or-absent. The two halves fail
in opposite directions — one guards against reverting to an unrenderable form, the other
against re-creating the original silent-downgrade bug — and a future editor is far more
likely to notice a named test than a comment.

### D7. Teach the ambiguity rather than the outcome name

The lab guide's outcome table currently glosses `cancelled` as the user dismissing the
prompt, which is what the specification says and what this investigation showed to be
incomplete. It will state both causes and point at `reason`, `elicit_ms`, and `client`.

This is the most durable part of the change. A student who learns that a protocol's outcome
names are aspirational, and that clients diverge, has learned something true about
integrating against MCP — more useful than any single field.

### D8. The caller-facing reason is server-authored, never the client's text

The operator log gets the client's own words (D2). The tool response gets a plain-language
string the server composes from the outcome, with no client-supplied text in it.

The asymmetry is deliberate and is a security boundary, not a style preference. A tool
response is consumed by a language model, so relaying an arbitrary client-controlled string
into it is a prompt-injection surface — a client could return a refusal whose "error" reads as
an instruction. The MCP guidance to treat tool output as untrusted and return only the minimum
necessary applies squarely. The operator log is read by a human and is the right place for
verbatim client text; the model's context is not.

*Alternative — relay the client's reason to the caller:* strictly more informative and
strictly more dangerous. Rejected on the injection argument alone.

*Alternative — sanitize and relay:* the sanitizer becomes a permanent liability for a benefit
already covered by the log an operator can read.

### D9. Retry guidance is keyed to the outcome class, not to the fact of blocking

Outcomes split cleanly into *answered* (`accepted`, `declined`, `cancelled`) and *never asked*
(`unsupported`, `error`). Only the second class gets "confirmation is required on this client".
The first gets an explanation and no path forward.

This is the whole safety argument for the user's choice, so it is worth stating why it holds.
Telling a model it may set `confirm` after a *refusal* would be teaching it to override a
human. Telling it after `unsupported` cannot override anyone, because nobody was asked. And
the guidance is safe even if a model ignores the distinction: `confirm` is consulted *only*
for never-asked outcomes, so on a client that can prompt, setting it re-asks the user rather
than bypassing them. The invariant established by the predecessor change — refusals are
terminal — is what makes recovery guidance safe to publish at all.

*Alternative — never suggest `confirm`:* the "explain but keep the block" option. Cleanest
security story, and a legitimate policy. Not chosen, because it makes the lab unusable on any
client without elicitation and removes the fallback the spec already sanctions.

*Alternative — suggest `confirm` on every block:* one fewer branch, and it trains models to
retry past humans. Rejected.

### D10. Route sync's dry-run through the shared response, then add its summary

Sync keeps `deterministic_summary` — it is genuinely useful — but as an additional field
rather than as a replacement for the shared explanation. The divergence exists because a tool
was allowed to overwrite a shared message; the fix is to make the shared explanation
structural, so a future tool cannot silently drop it by assigning over one string.

*Alternative — copy the hint into `deterministic_summary`:* fixes today's symptom and leaves
the next tool free to reintroduce it.

### D11. Correct the descriptions rather than delete the guidance

The descriptions were rewritten for a good reason — models were passing `confirm=false` and
suppressing the prompt — and that steer should survive. Only the false absolute goes: `confirm`
is unnecessary *when the client can prompt*, and required when it cannot. The correction is a
qualification, not a reversal.

### D12. A non-interactive commit is marked as such

When a write commits via the fallback, the response says no human approved it. This costs one
boolean and means the one genuinely LLM-authorised write path is never invisible in a
transcript. It also gives the lab guide something concrete to point at when explaining why an
elicitation-capable client is the better setup.

## Risks / Trade-offs

**The schema change is a hypothesis and may not fix anything** → Accepted, and stated as
such. Its cost is bounded by D6, and the diagnostics land in the same change, so the next
run is informative regardless of whether the schema mattered.

**A client could put user text in a refusal body under an allow-listed key** → The value is
truncated and only three keys are disclosed. The residual exposure is bounded, and this is
the diagnostic stream on stderr, not an audit record. Documented rather than eliminated,
because eliminating it means recording nothing and returning to the current dead end.

**More fields on `write_gate` could crowd the event an attendee reads** → Fields are
conditional: `reason` and body diagnostics appear only on non-approval, `elicit_ms` only when
a request was issued. The approved-write event grows by client identity alone.

**Client identity introspection touches SDK internals that may move** → Every access is
`getattr`-guarded with an unknown fallback, and a test covers the absent-identity path. A
future SDK rename degrades the field, never the gate.

**Publishing retry guidance gives the model effective write authority on clients without
elicitation** → This is the accepted cost of the chosen option, and it is bounded rather than
open: `confirm` is consulted only when nobody could be asked, so on any client that can prompt
the model cannot use it to bypass a human. On a client that cannot prompt, the model's
chat-level confirmation is the only consent mechanism that exists — the alternative is not
safer consent but no writes at all. D12 keeps the path visible in the transcript. If a
deployment wants the stricter posture, the natural lever is a configuration switch that
refuses writes outright when elicitation is unavailable; it is deliberately not in scope here,
since the lab needs the permissive default to run on varied clients.

**A model may ignore the outcome distinction and set `confirm` after a refusal** → Harmless by
construction: a refusal never consults `confirm`, so the retry re-asks the user. Covered by a
spec scenario and a test rather than left to inference.

**Adding fields to tool responses changes the shape models see** → Additive only, and the
existing `dry_run`/`committed`/`message` fields keep their meaning, so a caller reading only
those is unaffected.

**`cancelled` remains terminal even when the reason proves it was a client fault** → A
deliberate trade-off. A write that commits on a refusal the server decided to disbelieve is
a far worse failure than a dry-run the user has to retry. The operator gets a log line that
says exactly what happened and can re-run it.

## Migration Plan

No migration. Purely additive to an existing event, one prompt-schema change with no
protocol implication, and no persisted state. Rollback is reverting the commit.

Verification is deliberately sequenced:

1. Unit tests establish redaction, timing, identity, and the pinned schema shape.
2. End-to-end tests, against the real client/server session already used by
   `test_write_gate_e2e.py`, prove a `cancel` carrying an error is diagnosable and that an
   approval omitting `acknowledge` still commits.
3. One live Codex run (build `26.818.41509`) then answers the open question below. Whatever
   it shows, it produces a log line that names a cause — which is the point of the change.

## Resolved Questions

**Why does Codex return `cancel` for an approved prompt?** Answered on the first run after
this change landed, by the fields it added. Two consecutive gated syncs from
`codex-mcp-client 0.149.0-alpha.4.1` (protocol `2025-06-18`) produced:

```text
{"event":"write_gate","outcome":"cancelled","elicit_ms":421.0,"client":"codex-mcp-client 0.149.0-alpha.4.1",…}
{"event":"write_gate","outcome":"cancelled","elicit_ms":3.2,"client":"codex-mcp-client 0.149.0-alpha.4.1",…}
```

This lands on the first branch above, unambiguously. `3.2 ms` is not a human; it is not even
enough time to draw a dialog. The 421 ms of the first call is first-invocation overhead and is
still an order of magnitude below the time a person needs to notice a prompt exists.

Three further readings come free from the same two lines:

- Codex **declares** the elicitation capability. Had it not, the gate would have resolved
  `unsupported` without issuing a request, and there would be no `elicit_ms` field at all. It
  advertises support and then declines to use it.
- The schema hypothesis (D5) is **dead**. `acknowledge` gave the client something concrete to
  render and the behaviour did not change, so the empty-`properties` object was not the cause.
  D5 stands on its own merits — a form must be submittable — but it is not the fix for this.
- `client_detail` is **absent**, so Codex is not reporting a timeout or an internal fault. It
  is not claiming anything went wrong; it simply answers `cancel`.

The conclusion is a client defect, and it belongs upstream (task 11.7).

### D13. An unaskable `cancel` is explained, not made retryable

The Codex finding breaks an assumption inside D9. That decision splits outcomes by whether a
human was asked, and places `cancelled` in the *answered* class — reasonably, since the
specification defines it as a user dismissal. Codex demonstrates a third case: a client that
answers `cancel` with nobody involved. Such a client lands in the answered class, receives the
refusal treatment, and therefore gets no way forward — the exact dead end this change removed
for `unsupported`, reappearing under a different label.

The fix is *not* to move `cancelled` into the never-asked class, nor to infer the class from
`elicit_ms`. A genuine fast dismissal and an auto-cancel are indistinguishable at the policy
layer, and guessing wrong means instructing a model to walk past a human who said no. The
safety property is worth more than the convenience.

Instead the `cancelled` reason gains one informational sentence, addressed to the person
reading the transcript rather than to the model: if no prompt appeared, the client may not
support approval prompts. It names a thing to check without naming an argument to pass, so a
human can act on it and a model has nothing new to try.

*Alternative — treat a sub-threshold `elicit_ms` as never-asked:* mechanically simple and it
would unblock Codex today, but it converts a safety boundary into a latency heuristic. A slow
client or a decisive user relocates the boundary. Rejected.

*Alternative — a denylist of clients with known-broken elicitation:* accurate where it applies,
but it is a maintenance burden that ages badly and encodes another project's bugs into this
one's configuration. Rejected.

*Alternative — document Codex as unsuitable and change nothing:* the honest minimum, and the
fallback if the sentence proves confusing. Not chosen, because the log already knows what
happened and the caller still learns nothing.
