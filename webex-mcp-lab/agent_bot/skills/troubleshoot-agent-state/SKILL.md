---
name: troubleshoot-agent-state
description: Use this skill when the user reports issues with contact center agents being stuck, unavailable, or not receiving calls. Helps diagnose agent state problems and suggests resolution steps.
---

# Troubleshoot Agent State

## Overview

This skill helps diagnose and resolve common agent state issues in the Webex Contact Center.

## Instructions

### 1. Gather the symptom

Ask the user to describe the problem:
- Is the agent stuck in a specific state (e.g., "Not Ready", "Reserved")?
- Is the agent not appearing in the dashboard at all?
- Are calls not being routed to the agent?

### 2. Check the current configuration

Use the available MCP tools to inspect:
- The agent's desktop profile assignment
- The address book entries that might affect routing
- Any recent changes to the organization's configuration

### 3. Common issues and resolutions

**Agent stuck in "Not Ready":**
- Check if the agent's desktop profile has the correct idle codes configured.
- Verify the agent has logged out and back in after any profile changes.

**Agent not receiving calls:**
- Confirm the agent is in a queue that has active routing.
- Check that the address book used for routing contains the correct entries.

**Agent not visible in dashboard:**
- Verify the agent's team and site assignments are correct.
- Check if the agent profile was recently modified — changes may take a few minutes to propagate.

### 4. Escalation

If the above steps do not resolve the issue, recommend the user contact their Webex Contact Center administrator with:
- The agent's email address
- The exact state shown in the dashboard
- The time the issue was first observed
