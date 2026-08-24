## Why

`server.py` is the file lab participants open first, yet at ~838 lines it mixes five concerns —
client/session wiring, run orchestration, MCP primitive helpers, 17 tool definitions, and
resources/prompts — in one wall of code. The signal a learner needs (*"an MCP tool maps
arguments to a Webex call"*) is buried under cross-cutting plumbing (`_run_tool`, `_should_commit`,
`_emit_progress`, `_maybe_summarize`, `_new_request_id`, …) and a `lambda:` idiom that stalls
first-time readers.

The underlying architecture is already clean (`server.py` → `tools/*.py` → `api/*.py`), so this
is a **readability/teaching** problem, not an architecture problem. This lab teaches MCP in the
context of Webex; the entrypoint file should read like a teaching artifact.

The chosen approach (from exploration) is **progressive disclosure — best and simple**: physically
quarantine the plumbing behind a module boundary, add exactly **one** annotated "anatomy of a
tool" exemplar, and let the lab guide carry a 3-level arc (mental model → the repetition problem →
the extracted pattern). No decorators or clever abstractions are added to the running code; the
per-tool shape stays identical so every tool remains a plain, greppable function.

## What Changes

- **Extract the cross-cutting runtime into `_runtime.py`** (new module): move `_get_client`,
  `_session_id`, `_new_request_id`, `_elapsed_ms`, `_result_summary`, `_run_tool` (exported as
  `run_tool`), `_should_commit`, `_emit_progress`, `_maybe_summarize`, and the `_ApproveWrite`
  schema. `server.py` imports these. This removes ~180 lines of "read this second" machinery from
  the entrypoint's reading path.
- **Keep every tool on `run_tool`** — no behavior change, no dual code paths, identical tool
  shape. The `lambda:` stays (it is a legitimate deferred-execution idiom) and is explained
  **once**.
- **Add one "Anatomy of an MCP tool" banner** above the first read tool
  (`tool_list_address_books`) and one above the first write tool (`tool_create_address_book`),
  each ~6 lines, explaining the 3 moves and the `lambda:` a single time.
- **Reorder `server.py`** for top-to-bottom teaching flow: imports → anatomy + tools (grouped) →
  resources → prompts → `main()`.
- **Lab guide (Chapter 1)**: add a short "Anatomy of an MCP tool" progression — a minimal
  explicit ~8-line tool (how MCP works), then the repetition problem, then a pointer to
  `run_tool`/`_runtime.py` (how to build it well). Optionally show a production `@wxcc_tool`
  decorator **in prose only** as the "level 3" DRY endpoint, without adding it to the code.

## Capabilities

### New Capabilities

- `teaching-server-readability`: The MCP server entrypoint and the lab guide SHALL present the
  server through progressive disclosure — a quarantined runtime module, one annotated tool
  exemplar, and a guide arc from minimal example to the extracted pattern — so a participant can
  understand "what an MCP tool is" without reading cross-cutting plumbing first.

## Impact

- **Source code**: new `wxcc-mcp-server/src/wxcc_mcp/_runtime.py`; `server.py` slimmed to tool
  definitions + resources/prompts + `main()`, importing from `_runtime`. No functional change.
- **Tests**: `tests/test_glass_box_logging.py` references `server._run_tool`,
  `server._result_summary`, `server._new_request_id`. These move to `_runtime`; update imports
  (or re-export the names from `server` for back-compat — decided in design).
- **Lab guide**: `lab-materials/lab-guide/lab-guide.md` — Chapter 1 gains the anatomy
  progression; the `server.py` file-map reference is updated to mention `_runtime.py`.
- **Out of scope**: the `@wxcc_tool` decorator and per-tool de-duplication (approach B) — shown
  only as narrative in the guide, never added to the code. Sampling/elicitation behavior is
  unchanged (only relocated).
- **Sequencing note**: this change relocates `_run_tool` etc. that were just edited by
  `migrate-off-deprecated-mcp-logging`; apply/archive that change first to avoid churn.
