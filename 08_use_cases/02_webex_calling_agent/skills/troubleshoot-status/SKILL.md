---
name: troubleshoot-status
description: >-
  Use ONLY when a user reports that Webex itself is down, slow, or
  unavailable — a suspected platform outage. Checks the platform status
  before escalating or troubleshooting local configurations. Do not use
  this for plain listing or reporting requests (listing users, licenses,
  numbers, devices, or call history) — those never need an outage check.
---

# Troubleshoot Status

## How it works

1. **Check platform status** — call `unresolved_incidents` (from the custom calling hub) to see if there is a known Webex outage.
2. **Review incidents** — If there are incidents, summarize them for the user (title and latest update) and tell them to wait for Cisco to resolve it.
3. **No incident** — If there are none, say the platform is healthy and hand back to normal troubleshooting; the outage is not the cause.

## Guardrails

- Never ask the user to change their password or reinstall Webex if there is an active platform incident.
- Always provide the incident title and updates if one exists.
