---
name: troubleshoot-address-books
description: >-
  Use when a contact-center agent reports a problem with address books
  or contacts on the Webex Contact Center desktop — contacts missing,
  wrong address book showing, empty contact list, or address book not
  assigned. Investigates the agent's desktop profile, its address book
  assignment, and the book's entries. Can fix a misassigned or missing
  address book by updating the desktop profile.
compatibility: >-
  Requires MCP servers manage_address_books and
  verify_desktop_profiles.
metadata:
  author: webexone-2026
  version: "4.0"
  lab-chapter: "8"
---

# Troubleshoot Address Books

## Why a skill, not an MCP prompt?

This workflow spans two MCP servers — the address-book server and the
desktop-profile server — plus a pure reasoning step that belongs to
neither. An MCP server prompt can only reference its own server's tools.
A skill lives client-side and orchestrates tools from any connected
server, plus reasoning steps that no single server provides.

## How it works

1. **Find the agent** — call `list_agents` (desktop-profile server) and
   grab their `agentProfileId`.
2. **Look at their profile** — call `get_desktop_profile` with that id.
   The key field is `addressBookId`.
3. **Find the right address book** — call `list_address_books`
   (address-book server) to get the desired book's `id`.
4. **Check the book has entries** — call `list_entries` with the book's
   `id` from step 3. You need that `id` first.
5. **Compare** — does the profile's `addressBookId` match the desired
   book's `id`? This is a reasoning step, no tool needed.
6. **Fix if needed** — call `update_desktop_profile` to point the profile
   at the right book.

## Data flow

Tool outputs chain directly into tool inputs. Field names match the API
— use them exactly as shown.

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
2. Call `list_agents` to find the agent. Note their `agentProfileId`.
3. Call `get_desktop_profile` with `id` set to the `agentProfileId` from
   step 2 — don't call this until step 2 has returned.
   Note the `addressBookId` field.
4. Call `list_address_books` to find the desired address book and its `id`.
   This doesn't depend on steps 2-3 — it can run alongside them.
5. Call `list_entries` with the book's `id` from step 4. You need that `id`
   first — don't call this until step 4 has returned. An empty book is as
   useless as no book.
6. Compare the profile's `addressBookId` (from step 3) with the desired
   book's `id` (from step 4). Both must be available before you compare:
   - **Match** — the book is assigned correctly; the problem is elsewhere
     (check if the book is empty).
   - **Mismatch or null** — the agent's profile points to the wrong book
     (or none). Proceed to step 7.
7. Fix with approval: call `update_desktop_profile` with `id` set to the
   `agentProfileId` from step 2 and `addressBookId` set to the desired
   book's `id` from step 4. The server shows a confirmation card warning
   that all agents on this profile will be affected — it will not proceed
   until the user approves. Summarize findings and what was changed.

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
