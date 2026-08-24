## 1. Correlation id plumbing

- [x] 1.1 Add a helper to generate a short (6-hex) correlation id per invocation
- [x] 1.2 Add context binding/unbinding helpers in `logging_config.py` (wrap `structlog.contextvars.bind_contextvars` / `clear_contextvars`) so `request_id` and `tool` stamp all downstream server logs
- [x] 1.3 Verify `merge_contextvars` is active in the processor chain and that bound ids appear on `wxcc_api_call`, `oauth_*`, and tool records

## 2. Glass-box client logger

- [x] 2.1 Extend `_emit_log` (or add a `_glass_log` helper) to prefix the correlation id and use ASCII-safe markers (`>`, `[OK]`, `[ERR]`, `->`)
- [x] 2.2 Keep all client-facing emits defensive (never raise; no-op when client lacks logging support)
- [x] 2.3 Ensure no secret can appear in any client-facing message

## 3. `_run_tool` logging envelope

- [x] 3.1 Generate + bind the correlation id at the top of `_run_tool`; clear it in a `finally`
- [x] 3.2 Emit `tool.received` (server) and a `> [id] <tool> — <intent>` start line (client)
- [x] 3.3 Measure elapsed time and emit `tool.result` with `elapsed_ms` (server) and `[OK] [id] <summary> (<ms> ms)` (client) on success
- [x] 3.4 Emit `tool.error` (server) and `[ERR] [id] <translated message>` (client) on failure, preserving existing error translation
- [x] 3.5 Pass a short `tool_name` and plain-language `intent` from each tool call site into `_run_tool` (one-line addition per tool)

## 4. Stage vocabulary alignment

- [x] 4.1 Confirm auth stage surfaces (`using_static_access_token` / `oauth_token_refreshed`) carry the id and optionally mirror to the client
- [x] 4.2 Confirm API stage (`wxcc_api_call`) and retry stage (`wxcc_api_retry`) carry the id; optionally mirror a client-facing `-> METHOD path` and `retry n` line
- [x] 4.3 Document the stage → server-event → client-line mapping in code comments where helpful

## 5. Tests

- [x] 5.1 Test that a read tool emits start + result client logs and that server records share the same `request_id`
- [x] 5.2 Test that ids differ across two sequential invocations and never leak (contextvars cleared)
- [x] 5.3 Test the three failure paths: missing token and E.164 validation produce no `wxcc_api_call`; 403 does produce one
- [x] 5.4 Test graceful degradation when the client does not support logging (tool still returns)
- [x] 5.5 Test that no secret appears in client-facing messages and redaction is retained on the server side

## 6. Lab guide: cockpit and correlation

- [x] 6.1 Add Getting-started step: launch MCP Inspector against `wxcc-mcp-server`
- [x] 6.2 Add Getting-started step: tail the server log (`WXCC_LOG_FILE` + `Get-Content -Wait -Tail`)
- [x] 6.3 Add per-chapter "correlate it" callouts to the read, create, manual-add/validation, and sync chapters showing a matched id pair

## 7. Lab guide: debugging chapter and appendix

- [x] 7.1 Expand Chapter 7 with the scenario playbook (happy read; missing/expired token; 403; E.164 validation) contrasting present/absent API stages
- [x] 7.2 Add the "two independent log filters" explanation (`WXCC_LOG_LEVEL` vs client `logging/setLevel`)
- [x] 7.3 Add the log-correlation cheat-sheet appendix (stage → server event → client line)
- [x] 7.4 Reference the MCP debugging guide and Inspector; verify all cited commands/paths resolve

## 8. Validation

- [x] 8.1 Run `pytest` (mocked) and confirm all tests pass — all 11 new glass-box tests pass; 4 pre-existing `test_sync.py` failures are unrelated (stale assertions vs the already-modified `crm_contacts.py`, not caused by this change)
- [x] 8.2 Run `openspec validate --changes "add-glass-box-logging"` and confirm it passes
- [ ] 8.3 Manually walk one scenario end-to-end in the two-pane cockpit and confirm ids match across streams (manual: requires a live MCP Inspector session; automated tests cover the equivalent correlation + stage behavior)
