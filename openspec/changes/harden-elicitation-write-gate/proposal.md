## Why

Elicitation is this server's **only** human-in-the-loop write gate, and it fails
**silently in the unsafe-for-teaching direction**: a learner clicks **Accept**, the server
discards the approval, and the write is reported as a dry-run. Reproduced live against
Codex — the address book stayed at 9 entries while the assistant insisted it could not
commit.

The cause is structural, not cosmetic. `should_commit()` asks the SDK helper
`ctx.elicit(message, schema=_ApproveWrite)` to do two unrelated jobs at once:
**obtain consent** and **parse a typed form payload**. The SDK enforces the second job
strictly, so a client that answers `accept` without a schema-shaped body raises *inside*
`ctx.elicit()`:

- `accept` + `content={}` or a differently-shaped body → `ValidationError` (`approve` missing)
- `accept` + `content=None` → `ValueError("Unexpected elicitation action: accept")`

Both land in a bare `except Exception: pass`, which then returns `bool(confirm_flag)`.
Because a well-behaved LLM passes `confirm=False` when the user asked for a preview,
**consent collapses to "no"** and the tool silently degrades to a dry-run. The gate is
also unobservable: not one log line records that an elicitation was attempted, answered,
or discarded, so the failure is indistinguishable from "the client has no elicitation
support" — the exact confusion that consumed this debugging session.

Two prior attempts treated symptoms. Removing the redundant `data.approve` check left
dead code, because the exception fires before any result object exists. Making
elicitation unconditional (ignoring `confirm`) still funnels every consent answer through
the same strict parser. The remaining fix is to stop conflating consent with form
parsing, and to make the gate auditable — a correctness and safety property of every
write tool, not a one-client workaround.

> **Follow-up: this diagnosis was necessary but not sufficient.** The observability added
> here worked — it immediately pinned the next failure outside the server. But it stopped at
> a wall: the gate records *that* a decision was `cancelled` while discarding the response
> body that says whether a human or the client produced it. Worse, the description rewrite
> below created a new dead end. Steering callers away from `confirm` is right on a client
> that can prompt and wrong on one that cannot, where `confirm` is the only path there is —
> and because the gate's reasoning never reached the caller, such a client saw only an
> unexplained dry-run. Both are addressed in `harden-elicitation-client-compat`.

## What Changes

- **Separate consent from form parsing in the write gate.** `should_commit()` calls
  `session.elicit_form()` directly and interprets the raw `action` itself: `accept`
  commits, `decline`/`cancel` do not. Consent is a three-state answer, not a typed
  payload, so no client body shape can invalidate an approval.
- **Make consent tolerant by construction.** The requested schema carries no required
  fields, so clients that submit `{}`, omit the body, or add unknown keys all produce a
  valid `accept`. **BREAKING** (internal): `_ApproveWrite`'s required `approve` boolean is
  removed; the elicited body is no longer read.
- **Distinguish "declined" from "unavailable".** Classify each gate outcome as one of
  `accepted` / `declined` / `cancelled` / `unsupported` / `error`. Only `unsupported` and
  `error` may fall back to `confirm`; an explicit `decline` is final and must never be
  overridden by a truthy flag.
- **Make the gate observable.** Emit one structured `write_gate` event per write carrying
  the outcome, the reason when the path was not interactive, and the correlating
  `request_id`. A swallowed exception must never again be the only record of a discarded
  approval. Records the *decision*, never the elicited content.
- **State the `confirm` contract in the tool surface.** Write-tool docstrings describe
  `confirm` as a non-interactive fallback rather than the commit switch, so a model does
  not read `confirm=False` as "never write" or `confirm=True` as "skip the human".
- **Cover the client matrix in tests.** Regression tests for accept-with-empty-body,
  accept-with-null-body, accept-with-unknown-keys, decline, cancel, unsupported client,
  and mid-elicitation transport error — the shapes real clients actually send.
- **Teach the gate honestly in the lab guide.** Explain that Accept means approve,
  Decline yields a preview, and the `write_gate` log line is how a learner *proves* which
  path ran instead of inferring it from the absence of changes.

## Capabilities

### New Capabilities
- `mcp-write-gate`: The elicitation-backed write-confirmation gate shared by every
  mutating tool — consent semantics independent of elicited payload shape, the outcome
  taxonomy that governs when `confirm` may be consulted, fail-closed behaviour, and the
  observability contract that makes each gate decision auditable.

### Modified Capabilities
<!-- openspec/specs/ holds no synced source-of-truth specs; the overlapping requirements
     from add-elicitation-experience (Accept = approve, and the confirm fallback wording)
     live only inside that change and are absorbed by the new mcp-write-gate capability.
     No separate delta spec is added. -->

## Impact

- **Code:** `wxcc-mcp-server/src/wxcc_mcp/_runtime.py` — `should_commit()` and
  `_ApproveWrite`; the outcome taxonomy and the `write_gate` event originate here, so all
  nine write tools inherit the fix without individual edits.
- **Code:** `wxcc-mcp-server/src/wxcc_mcp/server.py` — `confirm` docstring wording on the
  write tools (`create`/`update`/`delete` for address books and entries, `bulk_save`,
  `assign_address_book_to_profile`, `sync_crm_to_address_book`).
- **Resource:** `wxcc-mcp-server/src/wxcc_mcp/resources/write_safety_guide.py` — align the
  "Ask Before You Commit" wording with Accept = approve.
- **Tests:** `wxcc-mcp-server/tests/` — new client-matrix coverage for the gate; existing
  write tests keep passing via the non-interactive `confirm` fallback.
- **Docs:** `wxcc-mcp-server/lab-guide/lab-guide.md` — the elicitation explainer at the
  sync chapter, plus the `write_gate` line in the log-correlation material.
- **Supersedes:** `add-elicitation-experience` (0 tasks, never implemented) for the schema
  and acceptance-logic portion; its remaining lab-experience scope stays valid and is
  unblocked once this gate is trustworthy.
- **Dependencies:** none new. Uses `session.elicit_form()`, already present in the pinned
  MCP SDK (1.27.0), and stays compatible with the `ctx.elicit()` wire protocol.
- **Risk:** low and fail-closed — every non-`accept` outcome still refuses to commit, so
  the change can only convert *silently dropped* approvals into honoured ones.
