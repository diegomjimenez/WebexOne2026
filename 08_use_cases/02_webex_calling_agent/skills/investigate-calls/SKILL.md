---
name: investigate-calls
description: >-
  Use for any question about a user's or a number's Webex calls — show or
  summarize call history, list who called whom, review recent calls, or look
  into a specific call. Reports the call records (CDRs) plainly, and when a
  call did not succeed it flags that call and explains the likely cause by
  correlating the user's license, phone number, and device. Also answers
  "can this user make calls at all?".
---

# Investigate Calls

You are asked about a user's or a number's calls. Pull the actual call
records first, report what you find, and only dig into causes if something
did not succeed — you do not need a failed call to be useful. Most requests
are simply "show me what happened".

## Tools you use

- `get_detailed_call_history` (troubleshooting server) — the call records
  (CDRs) for a recent window.
- `unresolved_incidents` (troubleshooting server) — is there a live outage?
- `list_people`, `list_licenses` (control-hub server) — who the user is and
  what they are entitled to. Licenses appear on a person as IDs; join them to
  `list_licenses` (`id` -> `name`) and report the names, not the IDs.
- `list_numbers`, `list_devices` (calling server) — how the user is
  provisioned to call.
- `get_call_forwarding` (calling server) — a user's call forwarding. If their
  inbound calls are not arriving, forwarding may be sending them elsewhere.

## Steps

1. Identify the subject. A named subject is a person or a phone number — not a
   location or device. Resolve a name like "Pod 0" with `list_people` (match on
   display name or email) and a number with `list_numbers`; CDRs also carry a
   `user` display name you can match directly. Do not ask whether
   the subject is a user, location, or device. Only ask a clarifying question
   when the request names no subject at all — and even then, offer to summarize
   all calls in the window. The window itself is either a recent span or a
   specific past date/time.
2. Pull the records with `get_detailed_call_history`. For a recent window,
   widen `hours_back` (max 12). When the user names a date or time, translate
   it into `start_time`/`end_time` (UTC — a date like `2026-09-24` or an ISO
   8601 timestamp like `2026-09-24T05:00:00Z`) and call the tool with that
   **absolute** window. Do not fall back to the most recent 12 hours, and do
   not decide the window is unreachable — it need not be near now; the window
   is only capped at a 12-hour span and must end at least ~5 minutes in the
   past. Then report exactly what the feed returns: the calls, an empty
   window, or the API's error.
3. Report the calls that match the user or number in question — who called
   whom, when, how long, and the outcome. This alone answers most requests. If
   you could not resolve the named subject, report all calls in the window and
   say you could not narrow to that subject — do not block.
4. If every call succeeded, say so plainly and stop; there is nothing to fix.
5. If one or more calls did not succeed, flag them and find out why:
   - `unresolved_incidents` — rule out a platform outage first.
   - `list_people` / `list_licenses` — is the user active and licensed to call?
   - `list_numbers` / `list_devices` — do they own the number and have a
     registered device?
   - `get_call_forwarding` — if inbound calls are not arriving, is forwarding
     sending them elsewhere?
   Correlate: no license or no number explains a user who cannot call; a
   routing `outcomeReason` on otherwise healthy provisioning points at dial
   plans or the destination, not the user.
6. For any non-successful call, quote its `outcomeReason` — it is the API's
   own explanation and the single most useful field.

## Reporting a diagnosis

Keep it short and evidence-based. Anchor every conclusion to the specific
`outcomeReason` and the pattern you actually saw — for example, repeated
`TemporarilyUnavailable` refusals within a few seconds usually means retries to
an endpoint that was unregistered or unavailable; `CallRejected` on an
international destination points at the outbound dial plan or the location's
calling permission for that prefix, not the user. Name only the one or two most
likely causes and offer at most two or three concrete next actions. Do not
re-list the calls you already showed, do not hedge with a long list of "could
be" possibilities, and skip incidental tool noise (for example, an unrelated
404) that is not the cause.

## Reading a CDR

`get_detailed_call_history` returns `calls[]`, each with `user`,
`callingNumber`, `calledNumber`, `answered`, `outcome`, `outcomeReason`,
`duration`, and `location`. A call is successful when it connected and
completed normally. Treat a record as a problem when `answered` is false for
a call that should have connected, `outcome` is not a success value, or
`duration` is ~0 for a call that was meant to connect.

Match a CDR's `user` / `callingNumber` to `list_people` and `list_numbers` to
confirm who owns the call.

## Edge cases

- **No CDRs in the window** — the default window is only the last few hours.
  Say so and offer to widen `hours_back` or target an explicit past window with
  `start_time`/`end_time`, rather than concluding "no calls". If the calls are
  older than Webex's CDR retention, even an explicit window returns nothing —
  say that plainly instead of implying there were no calls.
- **CDR user not in `list_people`** — likely external, a workspace, or another
  org; note it instead of forcing a match.
- **403 from the CDR feed** — the token lacks the Calling CDR scope/role;
  report it as a permission problem, not "no calls".

## Guardrails

- Reporting and investigation are read-only — do them freely.
- For a management change (create/delete a workspace, location, or device, or
  changing a user's call forwarding), call the tool directly; the server shows
  a confirmation card and waits for approval. Never write to "fix" something
  you were only asked to look at.
- Only use IDs and numbers that came from a tool, and base every conclusion on
  a field a tool returned — never guess.
