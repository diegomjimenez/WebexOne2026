# Tasks

## 1. Create the `_runtime.py` module

- [x] 1.1 Create `wxcc-mcp-server/src/wxcc_mcp/_runtime.py` with a module docstring describing it
  as the cross-cutting runtime ("read this second").
- [x] 1.2 Move `_get_client` → `get_client` and `_session_id` → `session_id` into `_runtime.py`
  (with the module-level `_broker`/`_client` singletons).
- [x] 1.3 Move `_new_request_id`, `_elapsed_ms`, `_result_summary` into `_runtime.py` (keep them
  private with the leading underscore).
- [x] 1.4 Move `_run_tool` → `run_tool` into `_runtime.py`, preserving request_id binding,
  timing, structured `tool.received`/`tool.result`/`tool.error` logging, and error translation.
- [x] 1.5 Move `_ApproveWrite`, `_should_commit` → `should_commit`, `_emit_progress` →
  `emit_progress`, `_maybe_summarize` → `maybe_summarize` into `_runtime.py`.
- [x] 1.6 Move the required imports (secrets, time, json, Context, BaseModel/Field, WxccApiClient,
  OAuthBroker, WxccError, logging_config helpers, translate_error) into `_runtime.py`.

## 2. Slim and reorder `server.py`

- [x] 2.1 Replace the removed definitions with `from ._runtime import run_tool, should_commit,
  emit_progress, maybe_summarize, get_client, session_id`.
- [x] 2.2 Update every tool to call the imported helpers (`get_client()`, `session_id(ctx)`,
  `run_tool(...)`, `should_commit(...)`, `emit_progress(...)`, `maybe_summarize(...)`).
- [x] 2.3 Ensure ordering is: module docstring → imports → anatomy + tools (grouped: address
  books, entries, desktop profiles/agents, sync) → resources → prompts → `main()`.
- [x] 2.4 Remove now-unused imports from `server.py` (e.g. `secrets`, `time`, `BaseModel`/`Field`
  if no longer referenced).

## 3. Add the two anatomy banners

- [x] 3.1 Add a ~6-line "Anatomy of an MCP tool" banner above `tool_list_address_books`
  explaining the 3 moves and the `lambda:` deferred-execution idiom (once).
- [x] 3.2 Add a short banner above `tool_create_address_book` explaining the `should_commit`
  write gate (dry-run vs commit) once.
- [x] 3.3 Confirm no other tools gained redundant boilerplate comments.

## 4. Update tests

- [x] 4.1 Update `tests/test_glass_box_logging.py` to import `run_tool`, `_result_summary`,
  `_new_request_id` from `wxcc_mcp._runtime` (new names), replacing `server._run_tool` etc.
- [x] 4.2 Grep the whole `tests/` tree for `server._run_tool`, `server._result_summary`,
  `server._new_request_id`, `server._should_commit`, `server._emit_*`, `server._maybe_summarize`
  and fix any remaining references.
- [x] 4.3 Run the full test suite; confirm the logging/orchestration tests pass (behavior
  unchanged) and no new failures are introduced. (38 pass; the 4 `test_sync.py` failures are
  pre-existing, caused by modified `crm_contacts.py` fixture data — out of scope.)

## 5. Lab guide — anatomy progression

- [x] 5.1 In Chapter 1, add a short "Anatomy of an MCP tool" progression: a minimal ~8-line
  helper-free tool (bare round-trip).
- [x] 5.2 Add the "repetition problem" beat (logging + error translation + write gate × 17).
- [x] 5.3 Add the "extracted pattern" beat pointing to `run_tool` / `_runtime.py`.
- [x] 5.4 Add a one-paragraph note on the production `@wxcc_tool` decorator as the DRY endpoint,
  stating the lab keeps tools explicit on purpose (prose only, no code change).
- [x] 5.5 Update any `server.py` file-map / reference lines in the guide to mention `_runtime.py`.

## 6. Validation

- [x] 6.1 Import the server (`python -c "from wxcc_mcp import server"`) and confirm it loads and
  registers the same tools. (Loads; all 18 `tool_*` registered.)
- [x] 6.2 Run `openspec validate simplify-server-for-teaching --strict` and fix issues. (Valid.)
- [x] 6.3 Confirm `server.py` line count is materially reduced and reads top-to-bottom as tools +
  wiring, with plumbing in `_runtime.py`. (838 → 561 lines; plumbing in `_runtime.py`, 224 lines.)
