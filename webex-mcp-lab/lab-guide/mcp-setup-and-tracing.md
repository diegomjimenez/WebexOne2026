# MCP in VS Code — Setup, Configuration & Tracing

A hands-on guide for the `webex-mcp-lab` stdio server, based on the working lab configuration.

---

## 1. What is an MCP server here?

The Model Context Protocol (MCP) lets VS Code (via GitHub Copilot) discover and call
**tools** exposed by a local process. In this lab the server is a Python script
(`01_hello_mcp.py`) that speaks MCP over **stdio**:

- **stdout** → reserved for the JSON-RPC protocol (never print logs here).
- **stderr** → free for your own log messages; VS Code shows these in the Output panel.

---

## 2. Prerequisites

- VS Code **1.99+** (needed for the `MCP: List Servers` command and per-server output channels).
- GitHub Copilot / Copilot Chat extension installed and signed in.
- Python virtual environment created for the lab.

Verify Python and the MCP package inside the venv:

```powershell
C:/WorkRelated_LocalFiles/wx1Simple/WebexOne2026/webex-mcp-lab/.venv/Scripts/python.exe --version
C:/WorkRelated_LocalFiles/wx1Simple/WebexOne2026/webex-mcp-lab/.venv/Scripts/python.exe -m pip show mcp
```

---

## 3. Configuration (`mcp.json`)

The server is registered in the user-level file:

```
C:\Users\<you>\AppData\Roaming\Code\User\mcp.json
```

Working configuration for this lab:

```jsonc
{
  "servers": {
    "webex-mcp-lab": {
      "type": "stdio",
      "command": "C:/WorkRelated_LocalFiles/wx1Simple/WebexOne2026/webex-mcp-lab/.venv/Scripts/python.exe",
      "args": ["01_hello_mcp.py"],
      "cwd": "C:/WorkRelated_LocalFiles/wx1Simple/WebexOne2026/webex-mcp-lab"
    }
  }
}
```

Field notes:

| Field     | Meaning                                                                 |
| --------- | ---------------------------------------------------------------------- |
| `type`    | `stdio` — VS Code launches the process and talks over stdin/stdout.    |
| `command` | Absolute path to the venv Python interpreter (avoids PATH issues).     |
| `args`    | Script to run; resolved relative to `cwd`.                             |
| `cwd`     | Working directory so the script and its imports resolve correctly.     |

> Tip: Use **forward slashes** in JSON paths on Windows to avoid escaping backslashes.

---

## 4. Start / Stop / Restart the server

Any of these work:

- **Command Palette** (`Ctrl+Shift+P`) → **MCP: List Servers** → select `webex-mcp-lab` →
  **Start Server** / **Stop Server** / **Restart Server** / **Show Output**.
- **CodeLens** in `mcp.json`: click **Start / Stop / Restart** shown above the server entry.

A healthy startup log looks like this:

```
[info] Starting server webex-mcp-lab
[info] Connection state: Starting
[info] Connection state: Running
[warning] [server stderr] webex-mcp-lab-01 running on stdio - waiting for a client (Ctrl+C to stop).
[info] Discovered 1 tools
```

`Discovered 1 tools` confirms the `greet` tool was registered.

---

## 5. Viewing logs in the Output panel

1. Open **View → Output** (`Ctrl+Shift+U`).
2. In the top-right dropdown, choose **MCP: webex-mcp-lab**.

> The channel only appears **after** the server has started at least once.
> If you don't see it, start the server (Section 4), then reopen the dropdown, or use
> **MCP: List Servers → Show Output** which opens the channel directly.

This channel shows lifecycle events, tool discovery, and anything the server writes to **stderr**.

---

## 6. Tracing tool execution

By default the Output channel shows **lifecycle events only** — not individual tool calls.
The actual `tools/call` request/response travels as JSON-RPC over stdout and is not echoed
at the default log level. Two ways to observe executions:

### Option A — Enable MCP trace logging (see JSON-RPC traffic)

1. **Command Palette** → **Developer: Set Log Level…**
2. Pick the **MCP / webex-mcp-lab** channel (or set globally) → choose **Trace**.
3. Call the tool again. You'll now see the `tools/call` request and its response logged.

### Option B — Log from inside the tool (stderr)

Add a stderr log line inside the tool function. Because stdout is reserved for the protocol,
always log to **stderr**:

```python
import sys

@mcp.tool()
def greet(name: str) -> str:
    print(f"[greet] called with name={name!r}", file=sys.stderr, flush=True)
    return f"Hello, {name}. Your first MCP tool just ran."
```

Each call now prints a `[server stderr]` line into the **MCP: webex-mcp-lab** channel.

> ⚠️ Never `print()` to **stdout** on a stdio MCP server — it corrupts the JSON-RPC stream
> and breaks the connection. Use `file=sys.stderr` for all logging.

---

## 7. Troubleshooting

| Symptom                                   | Likely cause / fix                                                                 |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| No **MCP: …** entry in Output dropdown     | Server not started yet — start it, or use **MCP: List Servers → Show Output**.     |
| `MCP: List Servers` command missing        | VS Code too old — update to 1.99+.                                                 |
| Tool calls not visible in the log          | Raise log level to **Trace** (Option A) or add stderr logging (Option B).         |
| Server starts then immediately stops       | Check the **Window** output channel and the stderr lines for a Python traceback.  |
| Connection breaks after a tool call        | Something wrote to **stdout** — move all logging to stderr.                        |
| `0 tools` discovered                       | Tool not decorated/registered, or wrong script in `args`.                         |

---

## 8. Quick verification checklist

- [ ] `mcp.json` points to the venv Python and correct `cwd`.
- [ ] **MCP: List Servers** shows `webex-mcp-lab` as **Running**.
- [ ] Output channel shows `Discovered 1 tools`.
- [ ] Calling `greet` returns `Hello, <name>. Your first MCP tool just ran.`
- [ ] Trace level (or stderr logging) reveals each tool execution.
