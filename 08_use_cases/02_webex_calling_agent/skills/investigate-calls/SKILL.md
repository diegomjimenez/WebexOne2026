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
- `list_blocked_numbers` (calling server) — the specific numbers a user is
  blocked from dialing (outgoing-permission digit patterns). If a user cannot
  reach one particular number while other calls work, that number may have a
  BLOCK pattern here.
- `get_calling_permissions` (calling server) — a user's outgoing permissions by
  call type. If a user cannot reach a whole category of numbers while other
  calls work, check whether that call type is set to BLOCK here.

## Steps

1. Identify the subject — a person (resolve with `list_people`, matching display
   name or email) or a number (`list_numbers`); CDRs also carry a `user` display
   name you can match directly. If a user has multiple addresses, use all of
   them to match their calls. If the request names no subject, summarize all
   calls in the window. The window is either a recent span or a specific past
   date/time.
2. Pull the records with `get_detailed_call_history`. Call this tool **exactly
   once per user request** — the CDR feed is rate-limited to roughly one request
   per minute, so a second call fails with `429 Too Many Requests`. Your very
   first call to this tool must already carry the right window: resolve the
   subject and work out the window, then make one call. Never call it bare or
   with empty parameters to "see recent calls" first — that reflexive pull wastes
   the single request you get and makes the real query fail.
   - If the user names a specific date or time, that single call MUST pass
     `start_time` and `end_time` (UTC — a date or an ISO 8601 timestamp). Never
     call with empty parameters when a date was requested: an empty call returns
     only the last 12 hours ending now and will miss the requested window
     entirely. The tool fully supports past windows — never claim otherwise.
   - Only if the user just wants recent calls, call with `hours_back` (max 12)
     and no start/end.

   Do not fall back to the most recent 12 hours if a past date is requested. The
   window is capped at a 12-hour span and must end at least ~5 minutes in the
   past. Report exactly what the feed returns: the calls, an empty window, or the
   API's error.
3. Report the calls that match the user or number in question — who called
   whom, when, how long, and the outcome. If the user asks you to summarize,
   provide a summary instead of just listing every call. If you could not
   resolve the named subject, report all calls in the window and say you could
   not narrow to that subject — do not block.
4. If every call succeeded, say so plainly and stop; there is nothing to fix.
5. If one or more calls did not succeed, flag them and find out why:
   - `unresolved_incidents` — only relevant when the failure is happening now.
     It lists currently-open outages and cannot explain a past-dated call. Cite
     an incident only if it affects Webex Calling and overlaps the failure's
     time; ignore incidents for other services (for example, Contact Center).
   - `list_people` / `list_licenses` — is the user active and licensed to call?
   - `list_numbers` / `list_devices` — do they own the number and have a
     registered device?
   - `get_call_forwarding` — if inbound calls are not arriving, is forwarding
     sending them elsewhere?
   - `list_blocked_numbers` — if the user cannot dial one specific number (for
     example 1-800-444-4444) while other calls work, check whether that number
     has a BLOCK digit pattern.
   - `get_calling_permissions` — if the user cannot dial a number, check whether
     that call or call type (e.g. TOLL_FREE) is set to BLOCK.
   Correlate: no license or no number explains a user who cannot call; a call
   rejected for one specific number while others succeed on healthy provisioning
   points at a blocked digit pattern; a whole call type failing (e.g. all
   toll-free) points at a blocked call-type permission; a routing `outcomeReason`
   on otherwise healthy provisioning points at dial plans or the destination, not
   the user.
6. For any non-successful call, quote its `outcomeReason` — it is the API's
   own explanation and the single most useful field.

## Reporting a diagnosis

Keep the whole reply short. Name the most likely cause the evidence supports —
anchored to the specific `outcomeReason` and the pattern you saw, not to a
coincidental incident whose service or timeframe does not match — then stop
reasoning. Do not infer a cause the `outcomeReason` does not state, and do not
assume a fixed cause for a given reason; let the evidence drive it.

End with one short list of one or two concrete next actions: specific tool calls
you would run or a clear recommendation, never a conditional hedge ("if you have
a dial plan id", "if possible", "may require permissions"). Give a single such
list — not separate "what I can check", "what I can do", and "suggested next
steps" sections. Do not re-list the calls you already showed, do not pad with a
long list of possibilities, and skip incidental tool errors that are not the
cause.

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
- For a management change, call the tool directly; the server shows a
  confirmation card and waits for approval. Never write to "fix" something you
  were only asked to look at.
- Only use IDs and numbers that came from a tool, and base every conclusion on
  a field a tool returned — never guess.
