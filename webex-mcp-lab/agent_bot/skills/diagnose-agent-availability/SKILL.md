---
name: diagnose-agent-availability
description: Use when an admin reports Contact Center agents offline, not receiving calls, or stuck unavailable. Combines a local status tool with the agent MCP tools to find the cause.
---

# Diagnose Agent Availability

One flow, two tool sources — a **local** tool (`check_webex_status`) plus the
**MCP** tools from `07_agents_server.py`. Severity levels, state meanings, and
escalation live in the `lab://agent-troubleshooting` resource (auto-loaded into
context — you don't need to fetch it).

| Step | Tool | Source |
|------|------|--------|
| 1. Rule out a platform incident | `check_webex_status` | local |
| 2. See who's configured | `list_teams`, `list_agents` | MCP |
| 3. Inspect the affected agent | `get_desktop_profile` | MCP |
| 4. Classify + report | severity rubric | resource |

## Steps

1. Ask for the symptom:
   - Which agent / team? What state shows on their dashboard (e.g. "Not Ready", "Reserved")?
   - Not appearing at all, or appearing but not getting calls?
   - When did it start? (config changes take a few minutes to propagate)
2. Call `check_webex_status` first. If an incident is active, stop and report it.
3. Call `list_teams`, then `list_agents`, to find the agent and their profile id.
4. Call `get_desktop_profile` and compare against the expected queue config.
5. Summarize, classify severity, and recommend next steps.

## Guardrail

Never reassign a profile without approval. When a fix is needed, call
`reassign_desktop_profile` — the server shows a confirmation card and will not
proceed until the user approves.
