# Tasks

## 1. Audit & prepare

- [x] 1.1 Grep `server.py` for all `_emit_log`, `_glass_log`, `ctx.info(`, `ctx.warning(`,
  `ctx.error(` usages and list every call site (target: `_run_tool` + ~10 tools + sync `_log`
  callback).
- [x] 1.2 Grep `wxcc-mcp-server/tests/` for assertions on client-facing logging (e.g.
  `test_glass_box_logging.py`) and note which tests must change.
- [x] 1.3 Confirm which structured events (`tool.received`, `tool.result`, `tool.error`) already
  cover each removed client-log call so no lifecycle information is lost.

## 2. Code migration (C2)

- [x] 2.1 Remove the `_emit_log` function from `server.py`.
- [x] 2.2 Remove the `_glass_log` function from `server.py`.
- [x] 2.3 Remove the `_glass_log` calls (received / result / error) from `_run_tool`, keeping
  `request_id` generation, contextvar binding, timing, structured logging, and error
  translation intact. (Added `summary` to the `tool.result` event so the result summary is
  preserved in the structured stream.)
- [x] 2.4 Remove the direct `ctx.info/warning/error` (via `_emit_log`) commit-decision echoes
  from all write tools. (Commit decision already captured in each tool's `intent`.)
- [x] 2.5 Update the sync log callback (`_log`/`on_log`) so it no longer routes to protocol
  logging; keep any server-side structured logging. (Now emits `sync.entry` structlog events.)
- [x] 2.6 Verify `ctx.report_progress` and `ctx.elicit` call sites are untouched.
- [x] 2.7 Update the `server.py` module docstring to drop "Client-facing logging" from the list
  of demonstrated primitives.
- [x] 2.8 Remove now-unused imports/helpers left over from the deletions. (None became unused;
  `_result_summary`/`_emit_progress`/`Context` still in use.)

## 3. Tests

- [x] 3.1 Update or replace tests that asserted client-facing log emission to assert on the
  structured `tool.received`/`tool.result`/`tool.error` events and shared `request_id` instead.
- [x] 3.2 Add/adjust a test asserting no `notifications/message` protocol log is emitted during a
  tool call (`test_run_tool_emits_no_client_protocol_logs`).
- [x] 3.3 Run the full test suite and fix regressions. (All logging tests pass; the 4
  `test_sync.py` failures are pre-existing — verified they pass against the original
  `crm_contacts.py` and are caused by the separately-modified CRM data, out of scope here.)

## 4. Lab guide — deprecation content (G3)

- [x] 4.1 Rewrite the Chapter 8 protocol-logging section to teach: what protocol logging was,
  that SEP-2577 deprecates it (2026-07-28), the `MCPDeprecationWarning` behavior, and the link
  to the SEP.
- [x] 4.2 Present stderr-native logging (Python `logging`/structlog → stderr) as the recommended
  replacement and the pattern this server now uses.
- [x] 4.3 Rewrite the "two-stream" framing into "one stderr stream, two views" (captured client
  stderr + tailed `WXCC_LOG_FILE`); preserve the `request_id` correlation drill.
- [x] 4.4 Keep/relocate the `[error]` channel-label explanation and the "emitted `level` vs.
  `WXCC_LOG_LEVEL` filter threshold" explanation (§8.7, now covering all three notions of level).
- [x] 4.5 Document how each supported client surfaces captured stderr (Cursor Output channel,
  Claude Desktop `mcp*.log`, Inspector) — §8.5 table.
- [x] 4.6 Remove the §8.5 `_emit_log` snippet (replaced §8.5 with the host-captures-stderr
  model), resolving the prior code/prose mismatch.

## 5. Lab guide — consistency sweep

- [x] 5.1 Update Step 0.8 cockpit setup to the single-stream, two-view model.
- [x] 5.2 Update per-chapter correlation callouts (Ch. 1, 2, 3, 6, 7) that referenced the
  client-facing protocol log line.
- [x] 5.3 Update the Chapter 9 troubleshooting playbook to read logs from stderr/log file only.
- [x] 5.4 Update the appendix cheat-sheet entries for logging.
- [x] 5.5 Grep the whole guide for `ctx.info`, `notifications/message`, `logging/setLevel`,
  "client-facing log", "two streams" and confirm no stale/contradictory references remain (all
  surviving mentions are intentional deprecation-teaching context).

## 6. Validation

- [x] 6.1 Run `openspec validate migrate-off-deprecated-mcp-logging --strict` and fix issues.
  (Valid.)
- [x] 6.2 Confirm no logging `MCPDeprecationWarning` path remains: `_emit_log`/`_glass_log`
  removed (verified via import), and `test_run_tool_emits_no_client_protocol_logs` proves no
  `ctx.info/warning/error` is called during read or error tool runs. (Full stdio run needs live
  OAuth/network, so verified via unit tests + import smoke instead.)
- [x] 6.3 Confirm the lab guide is consistent: chapter numbers unchanged (8 = logging, 9 =
  troubleshooting); the §3.1 "compare it to a `403` in Chapter 9" cross-reference still resolves
  to Chapter 9 scenario C.
