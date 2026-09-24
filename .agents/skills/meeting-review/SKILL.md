---
name: meeting-review
description: >-
  Use when the user asks to prepare for, get ready for, review readiness of, or
  check what is missing from their meetings. Triggers on phrasings like "help me
  prepare", "am I ready for", "what do I need before", "review my meetings",
  "check my schedule for gaps". Checks each upcoming meeting for agenda,
  invitees, and conflicts, then produces a preparation checklist. Not for a
  plain list of meetings with no readiness question.
argument-hint: [person or time range]
---

# Meeting Review

## Tools

Use the Webex Meeting MCP server only.

| Need | Tool |
|---|---|
| Find upcoming meetings | `webex-list-meetings` |
| Set agenda, title, time, or invitees | `webex-update-meeting` |

If no Webex Meeting tool is available, output
`WEBEX MEETING TOOLS NOT AVAILABLE` and stop. Do not answer from memory.

## Procedure

1. Call `webex-list-meetings` with `state="scheduled"` and
   `includeParticipants=true`. Pass `from`/`to` when the user gave a time range.
2. Check all three dimensions for every meeting:
   - **Agenda** — is the `agenda` field non-empty? A meeting without one wastes
     its own first ten minutes, so this is the highest-value flag.
   - **Invitees** — is anyone listed besides the host?
   - **Conflicts** — compare each meeting's start and end against every other
     meeting in the result set. Flag both sides of any overlap.
3. Report every check, including the ones that pass. A silent check reads as a
   skipped check.
4. Produce the checklist using the template below.

## Output template

```
MEETING READINESS -- <person or range>
======================================

<title> | <day HH:MM> | <duration>
  Agenda:    <present / NO AGENDA>
  Invitees:  <N invited / NO INVITEES>
  Conflict:  <none / CONFLICT with "<other title>">

PREPARATION CHECKLIST
1. <most urgent concrete action>
2. <next action>
======================================
