## Context

The `wxcc-mcp-server` is a clean six-layer onion, but the lab guide only narrates the top
three layers (MCP surface → `run_tool` → `tools/`). The bottom three — `api/` + `client.py`,
`auth/oauth.py` + `config.py`, and `errors.py` — are where an operator looks when a live
integration misbehaves, yet they appear in the guide only as `Reference:` line items and
`# VERIFY` markers.

Two facts shape this design:

1. **The code already exists and is small.** `api/client.py` (~300 lines) holds the entire
   request/retry/error-mapping story; `auth/oauth.py` (~280 lines) holds the token lifecycle;
   `config.py` holds every endpoint constant. Nothing needs to be built — only *explained*.
2. **Chapter 9 already teaches the symptoms.** The troubleshooting matrix distinguishes a
   pre-network rejection (E.164, no `wxcc_api_call`) from a WxCC refusal (403, *with* a
   `wxcc_api_call`). That matrix is currently unmoored from the code that produces it. The new
   chapter's job is to *anchor* it.

Audience is explicitly **both**: novice admins (who need "where does this failure come from and
how do I read it?") and MCP developers (who need "how do I build an authenticated, retrying,
error-mapping API layer?"). The overall guide effort is budgeted at ~180 min; this chapter is
reference/self-study so it does not inflate the timed hands-on path (Ch. 1–6).

## Goals / Non-Goals

**Goals:**
- Trace one concrete call (`list_address_books`) top-to-bottom and back, naming the file and
  function at each layer, so the reader can navigate the source unaided afterward.
- Make the failure path first-class: HTTP status → typed exception (`errors.py`) →
  `translate_error` → the plain-language string the glass box shows — explicitly wired to the
  Chapter 9 scenario matrix.
- Explain auth at the depth an operator needs: the PAT bypass (`WXCC_ACCESS_TOKEN`) they use in
  the lab, OAuth acquire/refresh, expiry skew, and the "tokens never reach model or logs"
  invariant (tie to the existing redaction section).
- Explain config/contracts: `Settings` from env, `# VERIFY` endpoint placeholders + go-live
  checklist, and the typed `*Input`/`*Output` models (incl. E.164) as the pre-network gate.
- Ship an operator-facing **"which file when X breaks?"** map and a layered architecture
  diagram consistent with the exploration diagram.
- Serve both audiences with dual-lens callouts (admin "read it" vs developer "build it") rather
  than two separate chapters.

**Non-Goals:**
- No source behavior changes. At most, a few clarifying teaching comments anchored to lines the
  chapter cites.
- Not teaching prompts, elicitation-as-experience, or the novice experience-first on-ramp
  (separate threads B/C/D).
- Not a full API reference for every endpoint — one representative CRUD path (address books)
  plus the shared client/error/auth machinery; other tools are noted as "same shape."
- Not resolving the `# VERIFY` placeholders (that is a go-live task, not a teaching task).

## Decisions

**D1 — One new chapter, not inline-only callouts.** A dedicated chapter keeps the fast hands-on
path (Ch. 1–6) unchanged while giving the layers room for a coherent narrative and a reusable
troubleshooting reference. *Alternative considered:* scatter "peek one layer down" callouts into
Ch. 1/3/4. Rejected as the primary vehicle — it fragments the request/failure story and buries
the operator reference — but adopted as a *secondary* measure via cross-links (see D5).

**D2 — Chapter placement: reference/self-study, after the logging chapters (new Chapter 10,
before the Appendix).** The logging + troubleshooting chapters (8, 9) already establish the
glass-box vocabulary (`wxcc_api_call`, `tool.error`, `request_id`); the under-the-hood chapter
builds directly on them by explaining the code that emits those events. *Alternative:* place it
right after Ch. 1. Rejected — it would front-load heavy internals before the learner has felt
the payoff, hurting the novice audience.

**D3 — Organize by the journey of one request, not by folder.** Structure: (1) the layered map,
(2) the request path down, (3) the response/failure path up, (4) auth as a side-quest the client
depends on, (5) config & contracts, (6) the "which file when X breaks?" table. A single worked
call is more memorable than a per-file tour. *Alternative:* one section per folder
(`api/`, `auth/`, `models/`, `config/`). Rejected — reads like API docs, not a lesson.

**D4 — Dual-lens callouts for the "both" audience.** Where a layer serves the two audiences
differently, use paired notes: an **Operator** note ("what a broken X looks like and where to
look") and a **Builder** note ("the pattern to reuse / the trade-off"). Keeps one chapter
serving both without doubling length. *Alternative:* two chapters or two guides. Rejected as
over-scoped for this thread.

**D5 — Anchor to Chapter 9, don't duplicate it.** The new chapter references the existing
scenario matrix and explains the *mechanism* behind each row (e.g., "row C's `wxcc_api_call` is
emitted at `client.py` line ~185 before `_raise_for_status` maps the 403"). Ch. 9 keeps owning
the *drill*; Ch. 10 owns the *why*. Cross-link both directions. Also update the terse
`Reference:` lines in Ch. 1, 3, 4, 7, 9 to point at the new chapter.

**D6 — Cite code with real symbols and stable anchors, tolerate line drift.** Reference by
file + function name (e.g., `client.py._request`, `oauth.py.get_valid_token`,
`_raise_for_status`) rather than hard line numbers where possible, so the guide survives minor
edits. Short illustrative snippets may be pasted (like Ch. 8 already does for the structlog
chain), kept minimal and clearly "abridged."

**D7 — Security framing is explicit.** The auth section states the invariants as rules: tokens
are per-session, encrypted at rest (Fernet, `0o600`), never returned in tool output, never
logged (redaction). This doubles as a security-review talking point and reinforces the existing
redaction section rather than restating it.

## Risks / Trade-offs

- **[Guide length / cognitive load]** → Chapter is reference/self-study and clearly marked
  optional for time-boxed runs; the hands-on chapters are untouched. Dual-lens callouts keep
  each audience reading only its half where they diverge.
- **[Code drift makes citations stale]** → Prefer symbol/function anchors over line numbers
  (D6); keep pasted snippets short and labelled "abridged" so they are illustrative, not
  authoritative.
- **[Over-claiming correctness of `# VERIFY` paths]** → The chapter explicitly frames endpoint
  constants as placeholders and points to the go-live checklist; it never implies the paths are
  confirmed.
- **[Duplicating Chapter 9]** → Mitigated by D5: Ch. 10 explains mechanism and links to Ch. 9's
  drill instead of repeating the matrix.
- **[Scope creep toward prompts/elicitation]** → Explicit non-goals; those are tracked as
  separate changes so this one stays shippable on its own.
