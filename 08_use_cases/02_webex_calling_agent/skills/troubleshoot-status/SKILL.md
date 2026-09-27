---
name: troubleshoot-status
description: >-
  Use when a user reports a problem with Webex services being down,
  slow, or unavailable. Always check the platform status before
  escalating or troubleshooting local configurations.
---

# Troubleshoot Status

## How it works

1. **Check platform status** — call `unresolved_incidents` (from the custom calling hub) to see if there is a known Webex outage.
2. **Review incidents** — If there are incidents, summarize them for the user and tell them to wait for Cisco to resolve it.
3. **Check local users** — If there are no incidents, call `list_people` to ensure the user's account is active and properly configured.

## Guardrails

- Never ask the user to change their password or reinstall Webex if there is an active platform incident.
- Always provide the incident title and updates if one exists.
