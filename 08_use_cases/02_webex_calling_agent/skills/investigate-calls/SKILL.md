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

## Steps

1. Clarify scope only if it is missing: which user or number, and roughly
   when (CDRs cover the last few hours).
2. Pull the records with `get_detailed_call_history`. Widen `hours_back` if
   the request is about an older window.
3. Report the calls that match the user or number in question — who called
   whom, when, how long, and the outcome. This alone answers most requests.
4. If every call succeeded, say so plainly and stop; there is nothing to fix.
5. If one or more calls did not succeed, flag them and find out why:
   - `unresolved_incidents` — rule out a platform outage first.
   - `list_people` / `list_licenses` — is the user active and licensed to call?
   - `list_numbers` / `list_devices` — do they own the number and have a
     registered device?
   Correlate: no license or no number explains a user who cannot call; a
   routing `outcomeReason` on otherwise healthy provisioning points at dial
   plans or the destination, not the user.
6. For any non-successful call, quote its `outcomeReason` — it is the API's
   own explanation and the single most useful field.

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

- **No CDRs in the window** — the feed only covers the last few hours. Say so
  and offer to widen `hours_back`, rather than concluding "no calls".
- **CDR user not in `list_people`** — likely external, a workspace, or another
  org; note it instead of forcing a match.
- **403 from the CDR feed** — the token lacks the Calling CDR scope/role;
  report it as a permission problem, not "no calls".

## Guardrails

- Reporting and investigation are read-only — do them freely.
- For a management change (create/delete a workspace, location, or device),
  call the tool directly; the server shows a confirmation card and waits for
  approval. Never write to "fix" something you were only asked to look at.
- Only use IDs and numbers that came from a tool, and base every conclusion on
  a field a tool returned — never guess.
