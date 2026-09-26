---
name: meeting-review
description: >-
  Use when the user asks to prepare for, review readiness of, check what is missing
  from, or fix readiness gaps in their meetings. Triggers on phrases like 'help me
  prepare', 'am I ready for', 'check my schedule for gaps', or 'add an agenda to
  my meetings'. This skill evaluates agendas, invitees, and conflicts, and can
  update missing meeting details. Do NOT use it for plain requests to list meetings.
argument-hint: "person or time range"
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

1. Call `webex-list-meetings` with `includeParticipants=true` as the only parameter.
Add `from`/`to` only if the user gave an explicit date range.
If the user asked to add or change an agenda, stop here and do only this:
call `webex-update-meeting` once per meeting, using the meeting ID from this
list and no other meeting tool, then report whether each update succeeded.
Do not produce the readiness template.
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

```markdown
### Meeting readiness

> **<title>** · <weekday> <HH:MM>–<HH:MM>
> Agenda · present or **missing**
> Invitees · <invitee names, comma-separated, or **none**>
> Conflict · none, or **overlaps with <other title>**

**To do**
1. <one action per gap, most urgent first>
```

## Gotchas & Constraints

- **Creating Agendas:** `webex-create-meeting` has no `agenda` parameter, so a newly
scheduled meeting needs a follow-up `webex-update-meeting` call to set one. Do not
imply the agenda was set during creation.
- **Missing Invitee Data:** `webex-list-meetings` only returns invitees when
`includeParticipants=true`. If the invitee field is absent from the tool response,
the data was not requested. Re-query the tool. Do NOT report invitees as **none**
unless the field is explicitly present and empty. Use each invitee's display name,
or their email address if no name is returned.
- **Times:** The tool returns UTC. User is on "Central European time": add 2 hours from the
last Sunday of March to the last Sunday of October, and 1 hour otherwise. Never
print the UTC value, and never ask the user to confirm a timezone.
- **No Hallucination:** Report only what the tools return. Never infer an attendee
list or agenda content from a meeting title.
- **No Local Storage:** Never create, edit, or save a local file. This skill produces
chat output only. Meeting data belongs in Webex, not on disk. If a tool cannot store
a value the user asked for, report the limitation and stop.
- **Approval:** Never write agenda text you invented. Draft the wording, show it to
the user, and wait for explicit approval before calling `webex-update-meeting`.
