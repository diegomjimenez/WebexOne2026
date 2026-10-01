---
name: meeting-quality
description: >-
  Use for any question about a Webex meeting's audio/video quality — show or
  review a meeting's quality, report how a meeting looked and sounded, check
  which recent meetings had issues, or explain why a meeting was choppy. Pulls
  the per-participant quality analytics and reports them, and when media was
  poor it flags the affected participants and explains whether it was one
  person's network or a meeting-wide problem.
---

# Meeting Quality

You are asked about a meeting's quality. Find the meeting, pull its
per-participant quality data, and report it. You do not need a complaint to be
useful — most requests are simply "show me how this meeting went". Add the
analysis only when the numbers show a problem.

## Tools you use

- `list_ended_meetings` (troubleshooting server) — meetings that already
  ended, each with an `id`, title, and start/end. When the request names a
  specific user, pass their email as `host_email` to scope the list to that
  person's meetings rather than the whole org.
- `get_meeting_qualities` (troubleshooting server) — per-participant
  audio/video metrics for one meeting id.
- `list_meeting_participants` (troubleshooting server) — who attended an ended
  meeting, with each participant's join/leave times and audio device. Use the
  same `meeting_id` as `get_meeting_qualities`.

## Steps

1. Clarify scope only if it is missing: which meeting (title/host) or which
   window to review, and whether the whole meeting or one participant.
2. Call `list_ended_meetings` for the window and pick the meeting(s) that
   match. When the request is about a specific user, pass their email as
   `host_email` so you only pull that person's meetings, not the whole org.
   Note each `id`. **If the user only asked to list or find meetings, stop here
   and report the list — do not pull quality data unasked.**
3. Only when the request is about how a meeting went (quality, audio/video, who
   was affected): for each meeting, call `get_meeting_qualities` with
   `meeting_id` set to the `id` from step 2.
4. Lead with a one- or two-line verdict for the meeting: healthy, or which
   participant(s) had trouble on audio or video. Keep it short — do not print a
   metrics table for everyone.
5. If everyone's media was fine, say so in a sentence and stop; any complaint is
   likely about content or scheduling, not the network. Do not list per-metric
   numbers for healthy participants.
6. Only for a participant whose media was actually poor: name them and quote the
   two or three numbers that prove it (the high jitter, the frame-rate collapse,
   the loss), then read the pattern:
   - One participant bad, the rest fine → that participant's network or device.
   - Everyone degrades together, especially at the same time → a meeting-wide
     or network-path problem, not an individual.
7. When the request is about *who* attended, or you need to tie a quality dip to
   a specific person, call `list_meeting_participants` with the same `meeting_id`
   and line the join/leave timeline up against the metrics.

## What "poor" means

For each participant and media type (audio, video), treat it as poor when, for
a sustained period: packet loss is high (well above a fraction of a percent),
latency / round-trip time is high enough to disrupt conversation (hundreds of
ms), jitter is high (the usual cause of choppy audio), or video
resolution/bitrate collapses. Quote the numbers you found — they are the
evidence.

Judge "poor" mainly on **packet loss and latency/jitter**. A low video frame
rate on a short or low-motion call (a 1:1, a static screen) is normal — do not
flag it as a problem on its own.

### Reading the raw values — do this before you judge anything

- **`-1` means "not measured", not zero.** It is a sentinel for a missing
  sample. Never read `-1` as "no video", "no frames", or "no audio", and never
  report it as a failure. If a stream is all `-1`, that metric simply was not
  captured for that participant — say nothing was recorded, do not infer an
  outage. The same goes for empty streams.
- **A participant can send fine while inbound is unmeasured.** If `videoIn` is
  all `-1` but `videoOut` shows real frame rates and bitrate, that person's
  video was working — only the inbound measurement is missing.
- **Attribute every number to the right person.** A latency or jitter value
  belongs only to the participant whose record it came from. Never carry one
  participant's number over to another.
- **Values are usually `[start, end]` pairs.** A bitrate or frame rate dropping
  to 0/`-1` at the very end often just means that person left before the meeting
  ended — not a failure.
- **No packet loss + sub-100 ms latency + single-digit jitter = healthy**, even
  if frame rates are low or many fields are `-1`.

`list_ended_meetings` gives the `id`; pass it as `meeting_id` to
`get_meeting_qualities`, which returns the per-participant items.

## Edge cases

- **No ended meetings in the window** — offer to widen `days_back`; do not
  report "healthy".
- **Meeting found but no quality data** — very short meetings, or data not yet
  processed. Say so rather than inventing metrics.
- **403 from the qualities API** — the token lacks the scope or user context
  the analytics API requires; report it as a permission problem.

## Guardrails

- Read-only — this agent reviews and reports; it never changes config.
- Only use a `meeting_id` returned by `list_ended_meetings`; never guess one.
- Every "poor" flag must cite the metric and value from the tool result;
  never invent participants or numbers.
- `-1` is "not measured", never a measurement. Do not turn it into "no video",
  "no frames", or an outage, and do not score it as poor.
