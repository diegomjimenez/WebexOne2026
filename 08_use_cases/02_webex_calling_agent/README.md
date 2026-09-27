# Webex Calling Agent (draft)

A self-contained use-case agent for Webex Calling / admin troubleshooting.
This folder is a **draft** — the walkthrough is not yet documented in the lab
guide. It reuses the same self-contained pattern as `01_webex_cc_agent`.

## What's here

```
02_webex_calling_agent/
    mcp_servers/
        calling_mcp.py           # Webex Calling tools
        controlhub_mcp.py        # Control Hub: people, licenses, roles, workspaces
        troubleshooting_mcp.py   # audit events, call history (CDRs), reports, incidents
    skills/
        troubleshoot-status/     # runbook: check platform incidents, then verify the user
```

## To finish this agent

Copy the engine from a built agent and wire it to these servers:

1. Copy `utils/`, `local_agent_tools/`, and `agentbot.py` from
   `01_webex_cc_agent/` into this folder.
2. In `agentbot.py`, point `_configs` at this folder's `mcp_servers/`
   (`calling_mcp.py`, `controlhub_mcp.py`, `troubleshooting_mcp.py`).
3. Add a `system_prompt.txt` with a calling/admin persona.
4. The `troubleshoot-status` skill is already here — it checks
   `unresolved_incidents` (troubleshooting server) before verifying the user
   with `list_people` (control-hub server).

No `.env` or `requirements.txt` needed — those were configured earlier in the lab.
