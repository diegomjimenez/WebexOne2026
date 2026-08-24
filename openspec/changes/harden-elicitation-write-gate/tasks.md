## 1. Pin the current behaviour with failing tests

- [x] 1.1 Add a reusable fake session/context test helper in `tests/` that returns a
      caller-specified `ElicitResult` (action + content) from `elicit_form`, and whose
      `check_client_capability` answer is configurable
- [x] 1.2 Add a failing test: `accept` with `content={}` must commit (reproduces the
      reported Codex defect)
- [x] 1.3 Add a failing test: `accept` with `content=None` must commit
- [x] 1.4 Add a failing test: `accept` with unknown-only keys (e.g. `{"confirm": true}`)
      must commit
- [x] 1.5 Add a failing test: `decline` with `confirm=True` must NOT commit (refusal is
      terminal)
- [x] 1.6 Confirm all five fail against the current `should_commit()` — this is the
      evidence the fix is real
- [x] 1.7 Prove the defect against the **real SDK**, not just the fake: drive an in-memory
      `ClientSession` (`tests/test_write_gate_e2e.py`) so the failure is attributable to the
      SDK's response-body validation rather than to the test double

## 2. Rework the gate in `_runtime.py`

- [x] 2.1 Define the outcome taxonomy (`accepted` / `declined` / `cancelled` /
      `unsupported` / `error`) and a small result type that pairs the outcome with an
      optional reason
- [x] 2.2 Replace the required-field `_ApproveWrite` schema with a no-required-fields
      requested schema (per design D2); remove the now-unread `approve` boolean
- [x] 2.3 Add the capability probe via `check_client_capability(...elicitation...)`,
      resolving `unsupported` without a round trip when the client never negotiated it
      (design D4)
- [x] 2.4 Call `session.elicit_form(message, requestedSchema, related_request_id)`
      directly and map the raw `action` to the outcome — `accept` → `accepted` regardless
      of body (design D1)
- [x] 2.5 Make refusal terminal by construction: `declined` / `cancelled` must never
      consult `confirm`, and only `unsupported` / `error` may fall back to it (design D3)
- [x] 2.6 Replace the bare `except Exception: pass` with a classified `error` outcome that
      captures the failure reason instead of discarding it
- [x] 2.7 Preserve the no-context path (`ctx is None`) as `unsupported`, so existing tests
      and scripted callers keep working through the `confirm` fallback
- [x] 2.8 Keep the public signature `should_commit(ctx, summary, confirm_flag) -> bool` so
      no call site in `server.py` needs to change — extended with a keyword-only
      `request_id` for correlation (see 3.2); all existing positional calls unaffected

## 3. Make the gate observable

- [x] 3.1 Emit exactly one structured `write_gate` event per evaluation, carrying the
      outcome, the gated action summary, and a reason when the outcome is not `accepted`
- [x] 3.2 Pass the correlating request id into the gate from the caller rather than
      relying on ambient contextvars, since the gate runs before `run_tool` binds them
      (design D5, ordering note)
- [x] 3.3 Assert the event contains no elicited body content
- [x] 3.4 Add a test that `accepted`, `declined`, `unsupported`, and `error` are each
      distinguishable in the emitted event
- [x] 3.5 Verify nothing is written to stdout (stdio transport must stay clean)

## 4. Correct the tool surface

- [x] 4.1 Rewrite the `confirm` wording in the write-tool docstrings in `server.py` to
      describe it as a non-interactive fallback and state that the server requests
      approval itself (design D6) — `create`/`update`/`delete` address book,
      `create`/`update`/`delete` entry, `bulk_save_entries`,
      `assign_address_book_to_profile`, `sync_crm_to_address_book`
- [x] 4.2 Ensure each destructive tool's prompt text names the specific resource being
      destroyed
- [x] 4.3 Ensure the sync prompt discloses deletion scope when `prune=True` before consent
      is requested
- [x] 4.4 Align the "Ask Before You Commit" principle in
      `resources/write_safety_guide.py` with Accept = approve and the corrected `confirm`
      contract

## 5. Validate

- [x] 5.1 Confirm the five tests from section 1 now pass
- [x] 5.2 Run the full suite; all pre-existing write tests must pass unchanged via the
      `unsupported` fallback path
- [x] 5.3 Run the linter on every touched file
- [x] 5.4 Accept path proven end-to-end over a real MCP session: the entry is created and
      `write_gate` reports `accepted`, for empty / absent / unknown-key response bodies
- [x] 5.5 Refuse path proven end-to-end over a real MCP session: `decline` and `cancel`
      both yield a dry-run and are not overridden by `confirm=True`
- [x] 5.6 Confirm the `write_gate` event shares the invocation's `request_id` with the
      surrounding `tool.received` / `wxcc_api_call` / `tool.result` lines
- [ ] 5.7 Confirm against Codex specifically, since it is the client that surfaced the
      defect and the only remaining unknown is its on-the-wire response shape

## 6. Teach it in the lab guide

- [x] 6.1 Update the elicitation explainer at the sync chapter: Accept means approve,
      Decline yields a preview, no checkbox to miss
- [x] 6.2 Document how to read the `write_gate` line to prove which path ran, instead of
      inferring it from the absence of changes
- [x] 6.3 Add a troubleshooting entry for "I approved but nothing changed", pointing at
      the `write_gate` outcome to tell `declined` from `unsupported` and `error`
- [x] 6.4 Note the client-trust boundary: presentation of the prompt is the client's
      responsibility, so a client may auto-accept without showing it
- [x] 6.5 Correct the descriptions of the gate elsewhere in the guide that still implied
      `confirm` could override consent (Chapters 1, 2 and §10.5), and refresh the
      `run_tool` snippet in §8.4 for the caller-supplied `request_id`

## 7. Close the loop

- [x] 7.1 Note in `add-elicitation-experience` that the schema and acceptance-logic scope
      is superseded here, leaving its lab-drill scope intact
- [x] 7.2 Run `openspec validate harden-elicitation-write-gate --strict` and resolve any
      findings
- [x] 7.3 Resolve the design's open question — whether `write_gate` joins the
      log-correlation cheat-sheet as a first-class lifecycle stage — or hand it to
      `add-elicitation-experience` explicitly — **resolved: yes**, recorded under the
      design's Resolved Questions with the reasoning
