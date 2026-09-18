---
name: meeting-review
description: >-
  Use when a user asks about their meetings, schedule, or asks you to review
  or triage meetings for a person. Do not just list meetings — investigate
  each one across all available Webex Meeting tools: check who joined, whether
  a summary was captured, whether a recording or transcript exists, and flag
  anything missing. Produce prioritized actions.
---

# Meeting Review

## What this skill does

You receive a meeting query and perform a **complete review** — not a list.
For every meeting, you check across all available Webex Meeting capabilities:
schedule, participants, summary, recording, and transcript. You flag what is
missing and produce prioritized actions.

## How to investigate each meeting

For every meeting returned by the schedule tool:

### Past meetings — check all of these:

1. **Participants**: who was invited vs who actually joined?
   Flag if attendance was low or key people were absent.
2. **Summary**: is an AI-generated meeting summary available?
   Flag `NO SUMMARY` if missing.
3. **Recording**: is a recording available?
   Flag `NO RECORDING` if missing.
4. **Transcript**: is a transcript available?
   Flag `NO TRANSCRIPT` if missing.
5. **Missed meeting**: if the meeting state is "missed" or no one joined,
   flag it as `MISSED — produced nothing` and recommend rescheduling.
   Note how many days overdue it is.

### Upcoming meetings — check these:

1. **Agenda**: does the meeting have an agenda or description?
   Flag `NO AGENDA` if missing.
2. **Participants**: who is invited? Flag if no invitees beyond the host.
3. **Time until meeting**: note how much time remains to prepare.

## Output format

```
MEETING REVIEW for <user or query context>
====================================================

!! ACTION REQUIRED — <title> | <date time> | MISSED
   Participants: <N> invited — <who joined or "check attendance">
   Summary:     <available / NOT AVAILABLE>
   Recording:   <available / NOT AVAILABLE>
   Transcript:  <available / NOT AVAILABLE>
   --> <action recommendation>

-- UPCOMING — <title> | <date time> | <time until>
   Participants: <who is invited>
   Agenda:      <present / NONE>
   --> <action recommendation>

PRIORITY ACTIONS (in order):
1. <most urgent action>
2. <next action>
3. ...
====================================================
```

## Rules

1. **Always investigate multiple dimensions.** Do not stop at listing the
   schedule. For each meeting, call the tools for participants, summary,
   recording, and transcript. This is the core value of this skill.
2. **Flag every gap.** If any dimension is missing or empty, flag it
   explicitly with the label shown above (NO SUMMARY, NO RECORDING, etc).
3. **Quantify urgency.** For missed meetings, state how many days overdue.
   For upcoming meetings, state how much time remains.
4. **Prioritize actions.** List actions in urgency order: missed meetings
   first (they need rescheduling), then upcoming meetings needing prep.
5. **Separate past from upcoming.** Use `!! ACTION REQUIRED` for past
   meetings with problems. Use `-- UPCOMING` for future meetings.
6. **Be factual.** Only use data from tool results. Never invent
   participants, summaries, or recordings.
7. **Keep it scannable.** One block per meeting, flags on their own lines,
   actions at the bottom.
