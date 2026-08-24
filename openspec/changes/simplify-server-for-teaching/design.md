## Context

`server.py` (~838 lines) is the lab's first-read file. The architecture beneath it is already
clean (`server.py` → `tools/*.py` → `api/*.py`), but the entrypoint interleaves five concerns:

1. Wiring — `_get_client`, `_session_id`
2. Orchestration — `_new_request_id`, `_elapsed_ms`, `_result_summary`, `_run_tool`
3. MCP primitive helpers — `_ApproveWrite`, `_should_commit`, `_emit_progress`, `_maybe_summarize`
4. 17 tool definitions (the bulk; all the same shape)
5. Resources + prompts + `main()`

Concerns 1–3 are cross-cutting machinery a learner does not need to grasp "what an MCP tool is."
Two specific snags: the sheer length pushes the tools down, and the `lambda:` coro-factory in
every tool reads as magic.

This change is the **"best and simple"** realization of the explored *progressive disclosure*
approach (option C, serving both "how MCP works" and "how to build it well"). It is a
readability refactor: **no behavior changes, no new abstractions in the running code.**

## Goals / Non-Goals

**Goals:**
- Make `server.py` read top-to-bottom as "what tools exist + how one tool maps to Webex."
- Physically separate cross-cutting runtime into `_runtime.py` ("read this second").
- Explain the tool pattern (incl. `lambda:`) exactly once via a small anatomy banner.
- Give the lab guide a 3-level arc: minimal explicit tool → repetition problem → extracted
  `run_tool` pattern.
- Zero functional change; tests stay green.

**Non-Goals:**
- No `@wxcc_tool` decorator or metaprogramming in the code (shown only as guide prose).
- No change to `tools/*.py`, `api/*.py`, schemas, auth, or logging behavior.
- No removal of the per-tool repetition itself — consistency and greppability are the priority.
- No renaming of MCP tools or changing their signatures.

## Decisions

### Decision 1: Quarantine via a new `_runtime.py` module

Move these out of `server.py` into `wxcc-mcp-server/src/wxcc_mcp/_runtime.py`:

- `_get_client`, `_session_id`
- `_new_request_id`, `_elapsed_ms`, `_result_summary`
- `run_tool` (renamed from `_run_tool` — it is now an imported, intentionally public helper)
- `_ApproveWrite`, `should_commit` (renamed from `_should_commit`), `emit_progress`,
  `maybe_summarize`

`server.py` imports what it needs:

```python
from ._runtime import run_tool, should_commit, emit_progress, maybe_summarize, get_client, session_id
```

Rationale: a module boundary is a stronger, cleaner "skip on first read" signal than comment
banners, and it shrinks the entrypoint's reading path by ~180 lines. The leading underscore on
the *module* name marks it internal without making every symbol private/awkward to import.

**Naming:** promote the moved helpers to non-underscore names (`run_tool`, `should_commit`,
`emit_progress`, `maybe_summarize`, `get_client`, `session_id`) since they are now a small
internal "runtime API" imported across modules. Keep `_result_summary`, `_new_request_id`,
`_elapsed_ms` as private helpers inside `_runtime.py`.

### Decision 2: Keep every tool on `run_tool`; keep the `lambda:`

No dual code paths. Every tool keeps the exact 3-move shape. The `lambda:` stays because the
alternatives are worse for teaching: a decorator hides the round-trip (rejected), and an async
context manager reintroduces per-tool `try/except` (rejected). Instead, explain the `lambda:`
once (Decision 3). This keeps all 17 tools identical and greppable.

### Decision 3: Exactly two anatomy banners

Add one ~6-line banner above `tool_list_address_books` (the read exemplar, and the Chapter 1
tool — continuity) and one above `tool_create_address_book` (the write exemplar — shows the
`should_commit` gate once). No per-tool comment noise elsewhere.

### Decision 4: Test imports — move, with thin back-compat re-exports

`tests/test_glass_box_logging.py` uses `server._run_tool`, `server._result_summary`,
`server._new_request_id`. Preferred: update the tests to import from `_runtime` and use the new
names (`run_tool`). To avoid a brittle rename ripple, `server.py` MAY re-export the moved names
(`from ._runtime import run_tool as _run_tool`) — but the cleaner choice is to update the tests
directly and not keep aliases. **Decision: update the tests to target `_runtime`; do not keep
back-compat aliases in `server.py`.**

### Decision 5: Guide arc lives in Chapter 1, decorator is prose-only

Chapter 1 gains a compact "Anatomy of an MCP tool" progression: (1) an ~8-line minimal explicit
tool, (2) the repetition problem, (3) a pointer to `run_tool`/`_runtime.py`. The production
`@wxcc_tool` decorator is described in one short paragraph as the real-world DRY endpoint, with
a note that the lab keeps tools explicit on purpose. No decorator is added to the code.

## Risks / Trade-offs

- **Churn against `migrate-off-deprecated-mcp-logging`** (which just edited `_run_tool`) →
  Mitigation: apply/archive that change first; this change only relocates and renames.
- **Import rename ripple** (`_run_tool` → `run_tool`) → Mitigation: it is referenced only in
  `server.py` and one test; both updated in the same change. Verified by grep + test run.
- **A new file to navigate** → Mitigation: this is the intended "read second" boundary; the
  guide's file-map names it explicitly.
- **Repetition remains** → Accepted by design: consistency/greppability beat DRY for a teaching
  lab; the DRY option is taught as narrative, not imposed.

## Migration / Rollout

Pure internal refactor; no config, API, or protocol changes. Validate by running the existing
test suite (logging tests must pass unchanged in behavior) and importing the server.
