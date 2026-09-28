---
name: investigate-calls
description: >-
  Use when an administrator asks about a user's calls or a specific call —
  failed calls, dropped calls, calls that would not connect, no dial tone,
  "why did this call fail", call history for a person, or whether a user is
  provisioned to call at all. Pulls Webex Calling call records (CDRs), flags
  non-successful outcomes, then correlates them with the user's license,
  phone number, and device to explain the likely cause. Rules out a platform
  incident first, then uses MCP tools from the troubleshooting server
  (incidents, CDRs), the control-hub server (people, licenses), and the
  calling server (numbers, devices).
compatibility: >-
  Requires MCP servers troubleshooting_mcp, controlhub_mcp, and calling_mcp.
metadata:
  author: webexone-2026
  version: "1.0"
  lab-chapter: "8"
---

# Investigate Calls

## Why a skill, not an MCP prompt?

This workflow spans three servers — the troubleshooting server (incidents,
CDRs), the control-hub server (people, licenses), and the calling server
(numbers, devices). An MCP server prompt can only reference its own server's
tools. A skill lives client-side, so it can orchestrate tools from every
connected server plus pure reasoning steps — here, matching a call record to
the user who owns the number.

## How it works

You are handed a symptom ("user X's calls keep failing", "why did this call
drop", "can user X even make calls?"). You do not stop at listing calls —
you pull the records, decide which ones actually failed, and then explain
*why* by checking how that user is provisioned.

1. **Rule out an outage** — call `unresolved_incidents` (troubleshooting
   server). If there is an active incident, config is not the cause; report
   and stop.
2. **Pull the call records** — call `get_detailed_call_history` to get CDRs
   for the recent window.
3. **Find the failures** — from those records, keep the ones for the user in
   question and flag the ones that did not succeed (see "What counts as a
   failed call").
4. **Explain the cause** — for a user with failures (or a user who cannot
   call at all), correlate their provisioning: are they active, licensed for
   calling, assigned a number, and is a device registered?
5. **Summarize** — state what failed, the most likely cause, and the fix.

## What counts as a failed call

A CDR is a *successful* call when it connected and completed normally. Flag a
record as a problem when any of these is true:

- `answered` is false (nobody picked up / it never connected), **and** it was
  not simply a normal missed inbound call.
- `outcome` is not a success value — read `outcomeReason` for the detail
  (for example a routing or permission failure).
- `duration` is 0 or near-zero for a call that was supposed to connect.

Always quote the `outcomeReason` back to the user — it is the API's own
explanation and the single most useful field.

## Data flow

Tool outputs chain into the next tool's inputs. Field names come straight
from the API — use them exactly.

- `get_detailed_call_history` returns `calls[]`, each with `user`,
  `callingNumber`, `calledNumber`, `answered`, `outcome`, `outcomeReason`,
  `duration`, `location`.
- Match a CDR's `user` to a person from `list_people` (same email / name).
- Match a CDR's `callingNumber` to an entry from `list_numbers` to confirm
  the number is actually assigned to that user.
- `list_licenses` tells you whether a calling license exists for the user.
- `list_devices` tells you whether the user has a registered device.

## Steps

1. Clarify the scope if it is missing:
   - Which user (name or email)? A specific call, or all of their recent calls?
   - Roughly when? (CDRs cover the last few hours only.)
2. Call `unresolved_incidents` first. If an incident is active, report it and
   stop — do not chase a configuration cause during an outage.
3. Call `get_detailed_call_history` to pull the recent CDRs. Widen
   `hours_back` if the user says the problem is older than the default window.
4. From the returned `calls[]`, select the records whose `user` matches the
   person in question, then flag the failed ones using the rules above. This
   needs step 3 to have returned — don't reason about calls you have not pulled.
5. If there are failures (or the user reports they cannot call at all), find
   out why. These lookups are independent of each other and can run together:
   - `list_people` — is the user present and active?
   - `list_licenses` — does a Webex Calling license exist for them?
   - `list_numbers` — does the user own the `callingNumber` from the CDRs?
   - `list_devices` — is a device registered for the user?
6. Correlate (reasoning, no tool): line the failures up against the
   provisioning. A "no number assigned" or "no calling license" explains a
   user who cannot call; a routing `outcomeReason` on otherwise healthy
   provisioning points at dial plans or destination, not the user.
7. Summarize: the failing calls (with `outcomeReason`), the most likely
   cause, and the concrete next step for the admin.

## Edge cases

- **No CDRs in the window** — the feed covers only the last few hours. Say so
  and offer to widen `hours_back`, rather than concluding "no problems".
- **CDR user does not appear in `list_people`** — the caller may be external,
  a workspace, or in another org. Note it instead of forcing a match.
- **All calls succeeded** — report that plainly; the issue may be call
  quality (a meetings/quality concern) rather than call setup.
- **403 from the CDR feed** — the token lacks the Calling CDR scope/role.
  Report it as a permission problem, not "the user has no calls".

## Guardrails

- **Investigation is read-only.** Listing people, licenses, numbers, devices
  and pulling CDRs never changes anything — do it freely.
- **Confirm before any write.** If the admin asks for a management change
  (create/delete a workspace, location, or device), call the tool directly;
  the server shows a confirmation card and will not proceed until the user
  approves. Never perform a write to "fix" something the user only asked you
  to investigate.
- **Only use IDs and numbers that came from a tool.** Never construct or guess
  a user id, number, or device id — use the values a tool returned.
- **Quote the evidence.** Base every conclusion on a field from a tool result
  (`outcomeReason`, license state, number assignment), not on assumption.
