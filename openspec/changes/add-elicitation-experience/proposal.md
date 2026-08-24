## Why

The lab promises learners will "understand the MCP primitive surface … **elicitation** … and *why each beats a raw API call*," and the server's design (`refactor-wxcc-mcp-for-lab/design.md`, D3) made elicitation the **primary** write-confirmation mechanism precisely because it is "a far stronger teaching moment than a boolean flag." But the **lab guide never delivers on this for elicitation**: it narrates the `confirm=True` dry-run *fallback* ("only an approved call (or `confirm=True`) commits"), never stages the `ctx.elicit` prompt actually firing, and never explains the one thing that makes elicitation matter — that it moves the commit decision from the *model* to a *human*. Learners currently leave understanding the dry-run gate, not the elicitation primitive. This change makes the lab teach elicitation for both **understanding** (why a human-held gate beats a model-held boolean) and **experiencing** (answering a real prompt and seeing the two outcomes).

## What Changes

- **Add an "experience it" beat to the lab guide (Chapter 2, first write).** Turn the create-address-book step into a hands-on elicitation drill: invoke the write, watch the elicitation prompt appear in the MCP Inspector (Elicitation tab / inline card), then run it twice — **decline** (no commit, no `wxcc_api_call`) and **approve** (commit, full API chain) — correlated across both panes, mirroring the existing B-vs-D "detective" framing.
- **Add an "understanding" explainer to the lab guide.** A short contrast — *model-decides* (`confirm=True`) vs *human-decides* (`ctx.elicit`) — establishing why elicitation is a stronger safety gate than a boolean and why the model cannot self-approve an elicited write.
- **Add an elicitation lifecycle stage to the two-pane cheat-sheet / scenario matrix** so the primitive is visible in the glass-box cockpit, not just implied.
- **Simplify the elicitation schema so "Accept" means "approve."** Remove the redundant inner `approve` boolean from `_ApproveWrite`; treat the client's `accept` action as the approval, `decline`/`cancel` as rejection. This removes the first-experience footgun where a learner clicks Accept but leaves the checkbox unchecked and the write silently does not commit. **BREAKING** (internal): changes the elicited response schema and `_should_commit` acceptance logic.
- **Keep a one-line note about the accept-vs-approve distinction** so the simplification is explained rather than silent, and the `confirm=True` fallback remains documented for clients without elicitation support.

> **Superseded in part by `harden-elicitation-write-gate`.** The two bullets above that touch
> *code* — simplifying the elicitation schema so "Accept" means approve, and the corresponding
> `should_commit` acceptance logic — were implemented there, along with the write-safety-guide
> wording and the test updates. That change went further than proposed here: the redundant
> `approve` boolean was not merely dropped but replaced with a **no-required-fields** schema,
> because the SDK's `ctx.elicit` helper validated the response body before returning and so
> rejected conforming clients' approvals outright. It also added the `write_gate` observability
> event and corrected the `confirm` contract in the tool descriptions.
>
> **Still in scope here:** the *teaching* work — the hands-on approve/decline drill in Chapter 2
> and the model-decides-vs-human-decides explainer. The lifecycle-stage bullet is also done:
> `write_gate` was added to the cheat-sheet and the scenario matrix (Scenario F).

## Capabilities

### New Capabilities
- `elicitation-experience`: Requirements that the lab **demonstrably lets a learner experience** elicitation — the write prompt renders in the lab's client, the learner can approve/decline/cancel, and the two outcomes (commit vs no-commit) are observable and correlated in both log panes.

### Modified Capabilities
<!-- openspec/specs/ holds no synced source-of-truth specs; prior capabilities
     (mcp-primitive-coverage, lab-guide-document) live only inside their originating
     changes. Their requirement changes are captured here via the new capability and
     the design's schema decision, so no separate delta spec is added. -->

## Impact

- **Docs:** `lab-materials/lab-guide/lab-guide.md` — Chapter 2 (elicitation drill + understanding explainer), Section 8 scenario matrix and the Appendix log-correlation cheat-sheet (new elicit stage).
- **Code:** `wxcc-mcp-server/src/wxcc_mcp/server.py` — `_ApproveWrite` (drop the boolean) and `_should_commit` (commit on `accept`). The `confirm` fallback path is unchanged.
- **Resource:** `wxcc-mcp-server/src/wxcc_mcp/resources/write_safety_guide.py` — align the "Ask Before You Commit" principle wording with Accept = approve.
- **Tests:** `wxcc-mcp-server/tests/` — update any assertion that relies on the elicited `approve` boolean payload.
- **Client dependency:** none new — MCP Inspector already renders form-mode elicitation with Accept/Decline/Cancel. Claude Desktop support varies; the `confirm` fallback covers it.
