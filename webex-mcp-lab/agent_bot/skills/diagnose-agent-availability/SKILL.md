---
name: diagnose-agent-availability
description: Use this skill when an admin reports Contact Center agents offline, not receiving calls, or stuck unavailable. Orchestrates a platform status check and the agent MCP tools to find the cause.
---

# Diagnose Agent Availability

## Overview

This skill diagnoses why Contact Center agents appear offline or unavailable. It
deliberately mixes tool sources: a **local** tool (`check_webex_status`, not from
the MCP server) and the **MCP** agent tools on `07_agents_server.py`.

For severity definitions, state meanings, and escalation policy, consult the
`lab://agent-troubleshooting` resource (already injected into context by the
MCP server — you do not need to fetch it).

## When to use

Use when an admin reports agents offline, not receiving calls, or stuck in an
unavailable state.

## Steps

1. Call `check_webex_status` first — rule out a platform incident before blaming
   configuration. This tool is local to the bot, not an MCP server tool.
   If an incident is active, report it up front.
2. Call `list_teams`, then `list_agents`, to see who is configured.
3. For each affected agent, call `get_desktop_profile` on their profile id and
   compare it against the expected queue configuration.
4. Classify each finding using the severity rubric in `lab://agent-troubleshooting`.
5. Summarize the findings and recommend next actions. If unresolved, escalate per
   the escalation policy in `lab://agent-troubleshooting`.

## Guardrails

- Never call `reassign_desktop_profile` yourself — propose it and let the user
  decide. The server will show a confirmation card when the tool is called.
