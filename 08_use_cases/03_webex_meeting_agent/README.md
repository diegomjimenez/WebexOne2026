# Webex Meeting Agent (draft)

A self-contained use-case agent for Webex Meetings. This folder is a **draft**
— the walkthrough is not yet documented in the lab guide. It reuses the same
self-contained pattern as `01_webex_cc_agent`.

## What's here

```
03_webex_meeting_agent/
    skills/
        meeting-review/          # runbook: review meetings across schedule,
                                 # participants, summary, recording, transcript
```

## To finish this agent

1. Copy `utils/`, `local_agent_tools/`, and `agentbot.py` from
   `01_webex_cc_agent/` into this folder.
2. Add a `system_prompt.txt` with a meetings persona.
3. The `meeting-review` skill is already here.

## TODO — transport

Unlike the Contact Center and Calling agents, this agent targets the
**remote hosted Webex Meetings MCP** (Streamable HTTP + bearer token), not a
local stdio server. The engine's `utils/mcp_client.py` is currently
**stdio-only** (`connect_all` uses `StdioServerParameters`).

To connect to the hosted Meetings MCP, add HTTP transport back to this folder's
`utils/mcp_client.py` (the Lab 6 `McpClient` had a Streamable-HTTP path using
`streamable_http_client` + a bearer token — reintroduce that alongside the
persistent-session support).

No `.env` or `requirements.txt` needed — those were configured earlier in the lab.
