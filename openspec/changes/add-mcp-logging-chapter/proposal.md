## Why

The lab guide teaches logging *operationally* — "here's what to look for, here's how to correlate" — but skips the conceptual layer that lets participants understand **why** the logging architecture works the way it does. A participant who completes the current guide can follow the two-pane cockpit, but cannot reason about:

- What MCP itself defines as a logging primitive (the `notifications/message` notification, `logging/setLevel`, RFC 5424 severity levels).
- How the server implements two independent log streams (structlog to stderr/file vs. `ctx.info()` over MCP transport) and why they are separate.
- Why third-party libraries (httpx, MCP SDK) produce plain-text noise alongside the structured JSON, and how the stdlib root logger controls that.

Adding this as a dedicated chapter transforms the troubleshooting playbook from a reference table into something participants can **extend** when they build their own MCP servers.

## What Changes

- Add a new lab guide chapter ("Understanding MCP server logging") positioned between the current Chapter 7 ("Going further") and Chapter 8 ("Troubleshooting playbook"). Current chapters 8 and the Appendix renumber accordingly.
- The new chapter walks through three layers: MCP protocol logging, server-side structured logging, and stdlib/third-party logging — grounded in actual code from `logging_config.py`, `server.py` (`_emit_log`, `_glass_log`, `_run_tool`), and the MCP spec.
- References the official MCP logging specification and debugging guide.

## Capabilities

### New Capabilities

- `mcp-logging-chapter`: Lab guide chapter that teaches MCP protocol logging concepts (notifications/message, logging/setLevel, severity levels) and maps them to the server's implementation — covering the three log streams, the two independent level filters, the structlog + contextvars correlation architecture, and the secret redaction pipeline.

### Modified Capabilities

## Impact

- **Lab guide**: `lab-materials/lab-guide/lab-guide.md` — new chapter inserted; subsequent chapter/appendix numbers shift by one.
- **No code changes**: This is a documentation-only change. No server code is added or modified.
- **References**: Links to https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging and https://modelcontextprotocol.io/docs/tools/debugging.
