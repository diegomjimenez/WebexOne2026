## 1. Pin the current behaviour before changing it

- [x] 1.1 Add a failing test asserting the requested consent schema declares at least one
      property, and a passing one asserting it declares no required fields (design D6). The
      pair must fail in opposite directions.
- [x] 1.2 Add a failing test asserting the gate event for a `cancel` carrying
      `{"error": "..."}` includes that error text.
- [x] 1.3 Add a failing test asserting the gate event for an approval carrying a populated
      body includes none of those values.
- [x] 1.4 Add a failing test asserting the gate event carries an elapsed-time field when a
      consent request was issued, and omits it when the gate short-circuited to
      `unsupported`.
- [x] 1.5 Add a failing test asserting the gate event identifies the connected client.
- [x] 1.6 Add a failing test asserting a write blocked by `unsupported` returns a response
      naming that outcome and stating confirmation is required on this client.
- [x] 1.7 Add a failing test asserting a write blocked by `declined` returns a response that
      does *not* mention confirmation or suggest retrying.
- [x] 1.8 Add a failing test asserting the sync dry-run response carries the same outcome,
      reason, and guidance fields as a single-entry write blocked the same way.
- [x] 1.9 Run the new tests and record which fail — this is the evidence the change is
      needed, and the baseline for verifying it landed.

## 2. Carry the response body to the log boundary

- [x] 2.1 Add a body field to `_GateDecision`, defaulting to `None`, documenting that it is
      evidence for the log and never an input to the commit decision.
- [x] 2.2 Populate it in `_ask_for_consent` from the `ElicitResult`, defensively, for every
      branch that received a response — including an unrecognized action.
- [x] 2.3 Confirm by inspection that no code path reads the body to decide consent. The
      commit decision must still derive from `outcome` alone.

## 3. Redact at the log boundary

- [x] 3.1 Write a redaction helper: given a body, return the sorted key names, plus values
      for `error`, `message`, and `reason` coerced to string and truncated to 256 characters.
- [x] 3.2 Handle the non-dict, empty, and `None` cases without raising — a malformed body
      must degrade the diagnostic, never the event.
- [x] 3.3 Unit-test the helper directly: allow-listed keys disclosed, others named only,
      oversized values truncated, empty body reported as no reason supplied.
      *Mostly asserted through the gate event, which is the observable contract; only the
      malformed-body cases are tested directly, because the typed `ElicitResult` cannot
      express shapes the wire can.*
- [x] 3.4 Call it from `should_commit` only when the outcome is not `accepted`, so the
      approval-body prohibition is enforced structurally rather than by convention.

## 4. Time the round-trip

- [x] 4.1 Measure with `time.perf_counter()` around the `elicit_form` await only, so the
      measurement covers the client round-trip and nothing else.
- [x] 4.2 Return the measurement for both the success and the failure branch of the await.
- [x] 4.3 Omit the field entirely when no request was issued, so a never-asked case cannot
      counterfeit an instant answer (design D3).
- [x] 4.4 Verify the measurement stays outside `run_tool`'s timer, so `elapsed_ms` still
      excludes human deliberation.

## 5. Record client identity

- [x] 5.1 Read the client name, version, and negotiated protocol version from the session,
      with every access `getattr`-guarded.
- [x] 5.2 Fall back to an explicit unknown marker when identity is unavailable, and never
      let introspection failure prevent the event from being emitted.
- [x] 5.3 Attach the identity to every gate event, including approvals.

## 6. Make the consent prompt maximally renderable

- [x] 6.1 Add the single optional `acknowledge` boolean to `_CONSENT_SCHEMA`, leaving
      `required` absent (design D5).
- [x] 6.2 Rewrite the schema's explanatory comment to state why the property exists — for
      the client to render — and why it is never read.
- [x] 6.3 Verify the existing accept-guarantee tests still pass unchanged: accept with `{}`,
      with no body, and with unrecognized fields must all still commit.
- [x] 6.4 Add a test that an approval setting `acknowledge` to `false` still commits, proving
      the property is not consent.

## 7. Return the gate's decision to the caller

- [x] 7.1 Change `should_commit` to return the decision rather than a bare boolean, so callers
      can report the outcome without re-deriving it. Keep the truthiness contract or update
      every call site in one pass — do not leave a mixed convention.
      *Done by taking the second option: renamed to `evaluate_write_gate` and updated all nine
      call sites, the tests, and the lab guide, since "should_commit" reads wrongly for
      something that returns a decision. `__bool__` is kept so it still works in a condition.*
- [x] 7.2 Add the outcome, a server-authored reason, and a guidance field to the write output
      schemas, all optional so a committed write carries none of them.
- [x] 7.3 Write the outcome-to-reason mapping as a single table keyed by outcome, so the
      caller-facing wording lives in one place and cannot drift per tool.
- [x] 7.4 Emit guidance only for the never-asked outcomes (`unsupported`, `error`) and never
      for `declined` or `cancelled` (design D9). Enforce this from the outcome class, not from
      per-tool conditionals.
- [x] 7.5 Confirm no client-supplied text reaches the response — the reason must be composed
      from the outcome alone (design D8).
- [x] 7.6 Mark a commit that took the non-interactive fallback path so the response discloses
      no human approved it (design D12).
- [x] 7.7 Thread the decision from each write tool in `server.py` into its tool call.

## 8. Make every write tool report a block identically

- [x] 8.1 Extend `dry_run_response` to carry the outcome, reason, and guidance fields.
      *Implemented one level up instead: `run_tool` applies the gate's decision to whatever
      payload a tool returns. Putting it in `dry_run_response` would have required every tool
      to thread the decision down to its own helper call, which is exactly the per-tool
      duplication that let sync drift. `dry_run_response` now carries a neutral message rather
      than hardcoded `confirm` advice, since that advice is only correct for some outcomes.*
- [x] 8.2 Route the sync dry-run branch through the shared response and attach
      `deterministic_summary` as an additional field rather than overwriting the message
      (design D10).
- [x] 8.3 Verify by test that sync and a single-entry write blocked by the same outcome return
      the same outcome, reason, and guidance.
- [x] 8.4 Correct every write tool docstring: `confirm` is unnecessary when the client can
      prompt and required when it cannot. Remove the claim that omitting it never prevents an
      approved write (design D11).
- [x] 8.5 Re-read all nine docstrings together to confirm they now say the same thing, since
      inconsistency between them is what let this defect through.

## 9. Prove it end to end

- [x] 9.1 Extend `test_write_gate_e2e.py` with a case where the client returns `cancel`
      carrying an error, asserting the write does not commit and the reason is recoverable
      from the emitted event.
- [x] 9.2 Add an end-to-end case where the client approves without `acknowledge`, asserting
      the write commits.
- [x] 9.3 Add an end-to-end case with a client that declares no elicitation capability,
      asserting the response explains the block and states that confirmation is required.
- [x] 9.4 Add an end-to-end case proving that re-invoking with confirmation after a *refusal*
      re-asks the user rather than committing.
- [x] 9.5 Confirm the emitted events go to stderr and leave stdout clean, so the stdio
      transport stays uncorrupted.
- [x] 9.6 Re-run the full suite and confirm every test from section 1 now passes.

## 10. Update the operator-facing material

- [x] 10.1 Revise the lab guide's `write_gate` outcome table so the cancelled row names both
      causes — user dismissal and a client reporting its own failure.
- [x] 10.2 Revise troubleshooting Scenario F to read `reason`, `elicit_ms`, and `client`, and
      state what each one indicates: an instant answer means no human was involved, a
      multi-second one means the click was mapped to the wrong action.
- [x] 10.3 Add a short troubleshooting note for clients without elicitation support: the
      outcome is `unsupported`, the write needs `confirm`, and an elicitation-capable client is
      the better setup because approval then comes from the user rather than the model.
- [x] 10.4 Add the new fields to the log-correlation example so an attendee sees the shape
      they should expect.
- [x] 10.5 Keep the additions proportionate — this is a troubleshooting aid, not a new
      chapter.

## 11. Correct the record and verify against the real clients

- [x] 11.1 Annotate decision D2 in `harden-elicitation-write-gate/design.md` with what was
      learned: the empty-properties schema was reasoned from Codex's own outgoing prompts,
      which is weaker evidence than it appeared, and it is superseded here.
- [x] 11.2 Note in that change's proposal that its diagnosis was necessary but not sufficient,
      and that its description rewrite created the unaskable-client dead end fixed here — so
      the history reads honestly.
- [x] 11.3 Correct the timestamp inference recorded during the investigation: adjacent gate
      and lifecycle events prove nothing about human latency, which is why `elicit_ms` exists.
- [x] 11.4 Run one live Codex session (build `26.818.41509`) against a gated write and capture
      the `write_gate` event verbatim.
      *Captured from `codex-mcp-client 0.149.0-alpha.4.1`: two gated syncs, both `cancelled`,
      `elicit_ms` of `421.0` then `3.2`, no `client_detail`. Recorded in design.md.*
- [x] 11.5 Interpret it against design D5's two branches and record the conclusion: schema
      resolved it, or the client answers without a human, or the click maps to the wrong
      action.
      *Second branch. The client answers without a human — 3.2 ms cannot involve a person, and
      no dialog was reported. It declares the elicitation capability (otherwise the gate would
      have resolved `unsupported` without issuing a request) and auto-cancels. The schema
      hypothesis is dead: `acknowledge` changed nothing.*
- [ ] 11.6 Re-run the custom non-elicitation client and confirm the write now completes after
      the caller-facing guidance, with the non-interactive disclosure present.
- [ ] 11.7 If the Codex finding is a client defect, file it upstream with the captured event,
      and close task 5.7 of `harden-elicitation-write-gate` with the result either way.
      *Confirmed a client defect by 11.5 — the upstream report is now warranted rather than
      conditional.*

## 12. Explain an unaskable cancel without making it retryable (design D13)

- [x] 12.1 Add a failing test asserting a `cancelled` response mentions that a missing prompt
      may mean the client does not support approvals.
- [x] 12.2 Add a failing test asserting that same response still carries no guidance field and
      still never mentions the confirmation argument — the D9 safety property must survive.
      *The existing `test_refusal_response_never_mentions_confirmation` already pinned both
      properties for `cancelled`, so it needed no change and served as the regression guard;
      the new `test_the_hint_survives_only_for_cancelled` covers the other half — that
      `declined` stays unambiguous and gains no hint.*
- [x] 12.3 Extend the `cancelled` entry in the caller-reason table with the informational
      sentence, leaving `declined` unchanged since a decline is unambiguous.
- [x] 12.4 Confirm the sentence names something to *check*, not an argument to *pass*, so a
      model reading it has nothing new to try.
      *It points at two observations — whether a dialog appeared, and the round-trip time in
      the server log — and the guard test confirms the token `confirm` appears nowhere in the
      response.*
- [x] 12.5 Note in the lab guide's Scenario F that a `cancelled` with a low `elicit_ms` and no
      dialog indicates the client auto-cancelled, and cite the Codex build as the known case.
