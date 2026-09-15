---
name: troubleshoot-address-books
description: >-
  Use when a contact-center agent reports a problem with address books
  or contacts on the Webex Contact Center desktop — contacts missing,
  wrong address book showing, empty contact list, or address book not
  assigned. Investigates the agent's desktop profile, its address book
  assignment, and the book's entries. Can fix a misassigned or missing
  address book by updating the desktop profile. Combines a local
  platform-status check with MCP tools from the address-book server (06)
  and the desktop-profile server (07).
compatibility: >-
  Requires MCP servers 06_manage_address_books and
  07_verify_desktop_profiles, plus local tool check_webex_status.
metadata:
  author: webex-mcp-lab
  version: "3.0"
  lab-chapter: "7"
---

# Troubleshoot Address Books

## Why a skill, not an MCP prompt?

This workflow spans three tool sources — a local tool, MCP server 06,
and MCP server 07. An MCP server prompt can only reference its own tools.
A skill lives client-side and orchestrates tools from any connected server,
plus local tools and pure reasoning steps that no single server provides.

## How it works

1. **Check platform status** — call `check_webex_status` (local tool) to
   rule out an outage before digging into config.
2. **Find the agent** — call `list_agents` (server 07) and grab their
   `agentProfileId`.
3. **Look at their profile** — call `get_desktop_profile` (server 07) with
   that id. The key field is `addressBookId`.
4. **Find the right address book** — call `list_address_books` (server 06)
   to get the desired book's `id`.
5. **Check the book has entries** — call `list_entries` (server 06) with
   the book's `id` from step 4. You need that `id` first.
6. **Compare** — does the profile's `addressBookId` match the desired
   book's `id`? This is a reasoning step, no tool needed.
7. **Fix if needed** — call `update_desktop_profile` (server 07) to point
   the profile at the right book.

## Data flow

Tool outputs chain directly into tool inputs. Field names match the API
— use them exactly as shown (see lab guide Section 7.4.7).

- `list_agents` returns each agent's `agentProfileId`.
- Pass that as the `id` to `get_desktop_profile`. It returns the
  profile's `addressBookId`.
- `list_address_books` returns each book's `id`.
- Compare the profile's `addressBookId` with the desired book's `id`.
- If they don't match, pass both to `update_desktop_profile`
  (`id` = the profile, `addressBookId` = the desired book).

## Steps

1. Ask for the symptom:
   - Which agent (name or email)? What do they see on their desktop?
   - Which address book should they see? (name or id)
   - Are contacts missing entirely, or is the address book empty?
   - When did it start? (config changes take a few minutes to propagate)
2. Call `check_webex_status` first. If an incident is active, stop and
   report it.
3. Call `list_agents` to find the agent. Note their `agentProfileId`.
4. Call `get_desktop_profile` with `id` set to the `agentProfileId` from
   step 3 — don't call this until step 3 has returned.
   Note the `addressBookId` field.
5. Call `list_address_books` to find the desired address book and its `id`.
   This doesn't depend on steps 3-4 — it can run alongside them.
6. Call `list_entries` with the book's `id` from step 5. You need that `id`
   first — don't call this until step 5 has returned. An empty book is as
   useless as no book.
7. Compare the profile's `addressBookId` (from step 4) with the desired
   book's `id` (from step 5). Both must be available before you compare:
   - **Match** — the book is assigned correctly; the problem is elsewhere
     (check if the book is empty, or if there is a platform incident).
   - **Mismatch or null** — the agent's profile points to the wrong book
     (or none). Proceed to step 8.
8. Fix with approval: call `update_desktop_profile` with `id` set to the
   `agentProfileId` from step 3 and `addressBookId` set to the desired
   book's `id` from step 5. The server shows a confirmation card warning
   that all agents on this profile will be affected — it will not proceed
   until the user approves.
9. Summarize findings and what was changed.

## Edge cases

- **Agent not found** — may be inactive or in a different org.
- **`addressBookId` is null** — profile was never assigned a book, not just
  the wrong one.
- **Address book exists but is empty** — correct assignment, wrong content.
  The fix is to add entries, not change the profile.
- **Multiple agents share the profile** — updating the profile affects all
  of them. The confirmation card makes this explicit.

## Guardrails

- **Confirm before writing.** Never update a profile without approval.
  `update_desktop_profile` shows a confirmation card — it will not proceed
  until the user approves. Remind the user that updating a profile affects
  every agent assigned to it, not just the one being investigated.
- **Validate before writing.** Before calling `update_desktop_profile`,
  verify that the `addressBookId` belongs to an actual book (it appeared
  in `list_address_books` results) and the profile `id` belongs to an
  actual profile (it appeared in `get_desktop_profile` results). Never
  pass values you constructed or guessed — only use IDs that came from
  a tool response.
