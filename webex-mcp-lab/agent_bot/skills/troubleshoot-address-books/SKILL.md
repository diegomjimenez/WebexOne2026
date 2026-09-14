---
name: troubleshoot-address-books
description: Use when an agent reports they cannot see address book contacts on their desktop. Combines a local status tool with MCP tools from both the address-book server (06) and the desktop-profile server (07) to find the cause.
---

# Troubleshoot Address Books

One flow, three tool sources — a **local** tool (`check_webex_status`), **MCP**
tools from `06_manage_address_books.py` (address books), and **MCP** tools from
`07_verify_desktop_profiles.py` (agent profiles). Field meanings live in the
`lab://desktop-profile-reference` resource (auto-loaded — you don't need to
fetch it).

| Step | Tool | Source |
|------|------|--------|
| 1. Rule out a platform incident | `check_webex_status` | local |
| 2. Find the agent | `list_agents` | MCP (07) |
| 3. Inspect the agent's profile | `get_desktop_profile` | MCP (07) |
| 4. Check address books on profile | `list_address_books` | MCP (06) |
| 5. Verify books have contacts | `list_entries` | MCP (06) |
| 6. Find a better profile if needed | `list_desktop_profiles` | MCP (07) |
| 7. Fix with approval | `reassign_desktop_profile` | MCP (07) |

## Steps

1. Ask for the symptom:
   - Which agent (name or email)? What do they see on their desktop?
   - Are contacts missing entirely, or is the address book empty?
   - When did it start? (config changes take a few minutes to propagate)
2. Call `check_webex_status` first. If an incident is active, stop and report it.
3. Call `list_agents` to find the agent and their `desktop_profile_id`.
4. Call `get_desktop_profile` with that id to see the profile details.
5. Call `list_address_books` to see what books exist in the org.
6. If the profile should have address books, call `list_entries` on each to
   verify they contain contacts (an empty book is as useless as no book).
7. Compare: does the agent's profile have the right books assigned?
   - If not, call `list_desktop_profiles` to find a profile that does.
   - Present the mismatch and recommend reassignment.
8. Summarize findings and recommend next steps.

## Guardrail

Never reassign a profile without approval. When a fix is needed, call
`reassign_desktop_profile` — the server shows a confirmation card and will not
proceed until the user approves.
