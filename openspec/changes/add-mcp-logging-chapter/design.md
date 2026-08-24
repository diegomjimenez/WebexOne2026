## Context

The lab guide currently teaches observability through:
- **Step 0.8**: Two-pane cockpit setup (Inspector + tailed log file)
- **Per-chapter callouts**: Correlation id examples showing matched pairs
- **Chapter 8**: Troubleshooting playbook (scenario matrix by missing/present stages)
- **Appendix**: Log-correlation cheat-sheet

This material is effective operationally — participants can follow the logs — but lacks the conceptual foundation that would let them understand *why* there are two streams, how the MCP protocol defines logging, and how this server bridges the gap. Participants who want to build their own MCP servers (or extend this one) need that layer.

The server's logging architecture has three distinct output streams visible on stderr:
1. **structlog** (JSON, redacted, correlated via contextvars) — from server code
2. **MCP protocol notifications** (`notifications/message` via `ctx.info()` etc.) — sent to the client over the MCP transport, visible in Inspector
3. **stdlib root logger** (plain text, no redaction, no correlation) — from httpx, MCP SDK, asyncio

The first two are intentional and well-designed. The third is a side effect of `logging.basicConfig(level=numeric_level)` setting the root logger threshold, which lets every third-party library that logs at that level or above dump to stderr.

## Goals / Non-Goals

**Goals:**
- Teach the MCP logging primitive: `notifications/message`, `logging/setLevel`, and the RFC 5424 severity levels — grounded in the actual spec.
- Show how this server implements two independent log streams and why they serve different audiences (operator vs. client/model).
- Explain the three-stream reality (structlog, MCP notifications, stdlib) so participants understand all the output they see.
- Clarify the "two independent filters" concept (server-side `WXCC_LOG_LEVEL` vs. client-side `logging/setLevel`) that already appears in Chapter 8 but deserves a conceptual introduction.
- Walk through the key code paths: `configure_logging()`, `_emit_log()`, `_glass_log()`, `_run_tool()`, and the `_redact` processor — with annotated snippets.
- Ground everything in the output participants already saw in earlier chapters (e.g., "why does `list_address_books` show `level: info` when `WXCC_LOG_LEVEL=DEBUG`?").

**Non-Goals:**
- Changing any server code (this is documentation-only).
- Teaching structlog internals in depth (just enough to understand the processor chain).
- Covering MCP transport debugging (connection issues, Inspector setup) — that's already in Step 0.8.
- Covering the troubleshooting scenario matrix — that stays in the existing Chapter 8 (renumbered to 9).

## Decisions

### Chapter placement: new Chapter 8, before the troubleshooting playbook

**Rationale:** The troubleshooting playbook (current Ch 8, becomes Ch 9) teaches *pattern matching* against log stages. Placing the conceptual logging chapter immediately before it means participants understand the architecture *before* they need to diagnose failures. Putting it inside Ch 7 ("Going further") would bury it in a grab-bag section.

**Alternative considered:** Folding it into the existing troubleshooting chapter. Rejected because that chapter is already a dense reference; mixing conceptual exposition with the scenario matrix would make both harder to use.

### Structure: three layers, top-down

The chapter walks through logging in three layers:
1. **MCP protocol logging** — what the spec defines (`notifications/message`, `logging/setLevel`, severity levels)
2. **Server-side structured logging** — structlog + JSON, secret redaction, contextvars correlation
3. **The third stream** — stdlib root logger, why httpx/MCP SDK produce plain text, how `WXCC_LOG_LEVEL` controls all three

**Rationale:** Top-down (protocol → implementation → side effects) matches how a developer would reason about adding logging to their own MCP server. It also mirrors the two-pane cockpit: layer 1 is Pane 1 (client-facing), layer 2 is Pane 2 (server-side), layer 3 is "that other stuff in Pane 2."

### Code walkthrough: annotated snippets, not full listings

Show 3–5 focused code snippets from `logging_config.py` and `server.py` with inline annotations. Not full file dumps.

**Rationale:** The lab guide style uses short, illustrative code blocks. Full listings are in the source files already linked. The snippets should answer specific questions ("what does `_emit_log` actually call?", "where does the JSON format come from?").

### Answering the "why info, not debug?" question explicitly

Include a short subsection that explains: the `"level"` field in JSON output is the emitted severity, not the filter threshold. `WXCC_LOG_LEVEL=DEBUG` means "let everything through," but the code deliberately tags tool invocations as `info` because they are operationally significant.

**Rationale:** This question came up during our exploration and is likely to confuse other participants. A 3-sentence explanation prevents a class of misunderstandings.

## Risks / Trade-offs

- **Lab length increase** → The chapter adds ~5 minutes of reading. Mitigation: mark it as "reference / self-study" so instructors can skip it in time-constrained sessions while participants can read it later.
- **Chapter renumbering** → Existing Ch 8 becomes Ch 9, Appendix stays. Mitigation: simple find-and-replace; no cross-references in earlier chapters point to Ch 8 by number (they use section titles).
- **Spec drift** → The MCP logging spec could change. Mitigation: link to the spec URL rather than quoting the full text; use dated spec reference (`2025-11-25` revision) so the link is stable.
