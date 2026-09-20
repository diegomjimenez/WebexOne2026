---
name: meeting-review
description: >-
  Use when a user asks to review or prepare for upcoming meetings.
  Check each meeting for agenda, invitees, and scheduling conflicts.
  Flag anything missing and produce a preparation checklist.
  Do not use for simple meeting listing or lookup requests.
---

# Meeting Review

## What this skill does

Check upcoming meetings for readiness. Flag missing agendas, missing
invitees, and scheduling conflicts. Produce a short preparation checklist.

## Rules

1. List meetings in chronological order with start time and title.
2. For each meeting, check:
   - Does it have an agenda or description? Flag `NO AGENDA` if missing.
   - Are there invitees beyond the host? Flag `NO INVITEES` if empty.
   - Does it overlap or conflict with another meeting? Flag `CONFLICT`.
3. Produce a `PREPARATION CHECKLIST` at the bottom with concrete actions.
4. Be factual. Use only data from tools. Never invent attendees or agendas.
5. Keep it short. One line per meeting plus flags.
6. If no upcoming meetings exist, say so clearly.
