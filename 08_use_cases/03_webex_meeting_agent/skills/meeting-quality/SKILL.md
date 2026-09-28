---
name: meeting-quality
description: >-
  Use when someone asks why a Webex meeting had poor quality, or to review
  meetings for quality problems — bad or choppy audio, frozen/blurry video,
  people dropping, "the meeting was terrible", or "which meetings last week
  had issues". Do not just list meetings: for the meeting(s) in question,
  pull the quality analytics, flag participants with poor audio or video, and
  explain whether the cause is one participant's network/device or a
  meeting-wide problem. Produces a prioritized, per-participant summary.
compatibility: >-
  Requires the troubleshooting MCP server (list_ended_meetings and
  get_meeting_qualities). Read-only.
metadata:
  author: webexone-2026
  version: "1.0"
  lab-chapter: "8"
---

# Meeting Quality

## Why a skill, not an MCP prompt?

The server exposes two tools — `list_ended_meetings` and
`get_meeting_qualities` — but it cannot tell the model *how to turn a vague
complaint into an analysis*. A server prompt could sequence its own tools, but
the judgment here is not sequencing: it is deciding what "poor quality" means,
reading per-participant metrics, and separating a single bad network from a
meeting-wide fault. That reasoning lives client-side, in this skill.

## How it works

You are handed a complaint ("today's staff meeting was unwatchable") or a
review request ("check last week's meetings for quality issues"). You do not
stop at the schedule — you pull each meeting's quality data and explain it.

1. **Find the meeting(s)** — call `list_ended_meetings` for the right window
   and pick the meeting(s) that match the request.
2. **Pull the quality data** — for each meeting id, call
   `get_meeting_qualities`. This returns per-participant media metrics.
3. **Judge the media** — flag participants whose audio or video quality is
   poor (high packet loss, high latency/jitter, low resolution/bitrate).
4. **Find the pattern** — one bad participant vs. everyone degrading together.
5. **Summarize** — worst-affected participants first, with the likely cause
   and a concrete next step.

## What counts as poor quality

Read the metrics the analytics returns for each participant and media type
(audio, video). Treat a participant as affected when, for a sustained period:

- **Packet loss** is high (well above a fraction of a percent).
- **Latency / round-trip time** is high enough to disrupt conversation.
- **Jitter** is high (uneven packet arrival — the usual cause of choppy audio).
- **Video** resolution or bitrate collapses, or frames are dropped.

Quote the actual numbers you found — they are the evidence for your conclusion.

## Data flow

Tool outputs chain into the next tool's inputs. Field names come from the API.

- `list_ended_meetings` returns meetings, each with an `id`, `title`, and start/end.
- Pass that `id` as `meeting_id` to `get_meeting_qualities`.
- `get_meeting_qualities` returns per-participant quality items — read audio and
  video metrics per participant to decide who was affected and how badly.

## Steps

1. Clarify the scope if it is missing:
   - Which meeting (title/host), or which time window to review?
   - Whole meeting, or a specific participant's experience?
2. Call `list_ended_meetings` for the window. If nothing comes back, say the
   window held no ended meetings and offer to widen `days_back` — do not
   conclude "no problems".
3. Select the meeting(s) that match. Note each `id`.
4. For each selected meeting, call `get_meeting_qualities` with `meeting_id`
   set to the `id` from step 3 — don't call this until step 3 has returned the id.
5. Read the per-participant metrics and flag the affected participants using
   the thresholds above. This needs step 4 to have returned.
6. Decide the pattern (reasoning, no tool):
   - **One participant bad, rest fine** → that participant's network or device.
   - **Everyone degrades together, especially at the same time** → a
     meeting-wide or network-path problem, not an individual.
7. Summarize: affected participants worst-first, the metric that proves it,
   the likely cause, and the recommended next step (check that user's network,
   escalate a site issue, etc.).

## Output format

```
MEETING QUALITY — <title> | <date time>
====================================================
Participants analyzed: <N>

!! POOR — <participant> | <audio/video>
   <metric>: <value>  (e.g. packet loss 4.2%, jitter 90ms)
   --> <likely cause + next step>

-- OK — <participant>
   no significant audio/video degradation

PATTERN: <one participant / meeting-wide>
PRIORITY ACTIONS:
1. <most urgent>
2. <next>
====================================================
```

## Edge cases

- **No ended meetings in the window** — offer to widen `days_back`; do not
  report "healthy".
- **Meeting found but no quality data** — very short meetings, or data not yet
  processed. Say so rather than inventing metrics.
- **All participants healthy** — report that plainly; the complaint may be
  about content or scheduling, not media quality.
- **403 from the qualities API** — the token lacks the scope or user context
  the analytics API requires. Report it as a permission problem.

## Guardrails

- **Read-only.** This agent reviews and explains; it never changes config.
- **Only use IDs that came from a tool.** Never guess a `meeting_id` — use the
  `id` returned by `list_ended_meetings`.
- **Quote the evidence.** Every "poor" flag must cite the metric and value from
  the tool result, not an assumption. Never invent participants or numbers.
