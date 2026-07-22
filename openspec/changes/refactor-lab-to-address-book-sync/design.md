## Context

`wxcc-mcp-server` is a teaching MCP server for WebexOne. Today it demonstrates the MCP
primitive surface on the *agent lifecycle* (onboard → diagnose → offboard), which spans
three WxCC API families and ~20 tools. That breadth obscures the pedagogical point and
overruns the 20–30 minute lab slot.

This change replaces the scenario with a single, cohesive narrative — **sync CRM contacts
into a WxCC Address Book and provision it for agents** — while retaining the
production-quality infrastructure that makes the server exemplary:

- `auth/oauth.py` — per-session OAuth broker (tokens encrypted at rest, never exposed).
- `api/client.py` — async httpx client with retries, backoff, typed error mapping.
- `logging_config.py` — structured logging with secret redaction.
- `errors.py` — typed exception hierarchy.
- `models/schemas.py` — Pydantic IO contracts (reshaped to new tools).
- The elicitation / dry-run write-safety pattern in `server.py`.

The Address Book, Address Book Entry, and Desktop Profile APIs all live in the **WxCC
Config API family** (`cjp:config_read` / `cjp:config_write`), so the Reporting/Search and
Platform/People families are dropped entirely.

Grounding facts (from developer.webex.com, July 2026):
- Address Book **v1** endpoints are removed 2026-10-15; target **v2**.
- Desktop Profile has a single `addressBookId` field — assignment = update the profile.
- Desktop Profile fields `dialPlans`, `agentDNValidationCriteria`,
  `agentDNValidationCriterions` are deprecated (removed 2026-09-15) — do not use.
- Agent Profile APIs are superseded by Desktop Profile APIs — use Desktop Profile.
- Get-all (list) APIs cap page size at 100.

## Goals / Non-Goals

**Goals:**
- One coherent scenario that exercises **every** MCP primitive: tools, resources, prompts,
  elicitation, progress, client logging, and (optional) sampling.
- Full CRUD coverage of address books and entries (including bulk save).
- Read-only discovery of desktop profiles and agents, including the profile↔agent mapping.
- A gated write to assign an address book to a desktop profile.
- A composite "hero" tool that diffs CRM source data against existing entries and applies
  the delta safely.
- Zero deprecated API usage; single Config scope pair.
- Preserve the reusable infrastructure and the gated-write safety guarantees.

**Non-Goals:**
- Live CRM integration — the CRM source is a static JSON resource in the lab.
- Writing to agents/users or desktop profiles beyond the single `addressBookId` assignment.
- Managing dial plans, outdial ANI, or other outbound-dialing prerequisites beyond the
  address-book link (mentioned in docs, not automated).
- Multi-tenant/remote transport hardening — the lab remains local stdio.

## Decisions

### D1: Replace the scenario, keep the infrastructure
Delete all agent-lifecycle tools/resources/prompts/tests and the Reporting + Platform API
families; retain `auth`, `client`, `logging`, `errors`, typed IO, and the write-safety
pattern. **Why:** the infra is the "doing it right" reference material and is API-agnostic;
only the domain layer is scenario-specific. **Alternative considered:** greenfield rewrite —
rejected as wasteful and it would lose battle-tested infra.

### D2: CRM source as a static JSON resource
Model CRM/directory data as an MCP **resource** (`crm://contacts`) returning a JSON array of
contacts. **Why:** no external dependency, deterministic for a lab, and it showcases
resources as the model's "knowledge" input that drives a write flow. **Alternative:** a
resource template parameterized by department (`crm://contacts/{department}`) — kept as a
possible stretch, but the flat resource is simpler for the core lesson.

### D3: `sync_crm_to_address_book` as the hero composite tool
A single tool reads the CRM resource, lists existing entries, computes an add/update/delete
diff (keyed by phone number in E.164, or by a CRM id attribute), previews it via
elicitation, then applies changes emitting progress + logs; optional sampling summarizes the
result. **Why:** this is the moment that proves "MCP > raw API" — orchestration the model
composes rather than a script the user writes. **Alternative:** rely only on atomic entry
tools + a prompt — kept available, but the composite makes progress/elicitation vivid.

### D4: Diff strategy — match on a stable key
Entries are matched CRM↔WxCC on a stable key: prefer a CRM-provided id stored in an entry
attribute; fall back to normalized E.164 phone number. Unmatched CRM contacts → create;
matched with changed fields → update; existing WxCC entries absent from CRM → delete
(delete requires explicit approval and is off by default via a `prune` flag). **Why:**
avoids accidental mass-deletion and makes the safety story concrete. **Alternative:**
name-based matching — rejected (names are not unique/stable).

### D5: Assignment = update the Desktop Profile's `addressBookId`
`assign_address_book_to_profile` reads the target profile, sets `addressBookId`, and writes
it back (PUT/PATCH per VERIFY), never touching deprecated fields. **Why:** matches the API
contract. **Alternative:** a dedicated assignment endpoint — none exists.

### D6: Placeholders remain `# VERIFY` / `# TODO`
Exact v2 paths, entry sub-paths, the agent→profile field name, PUT-vs-PATCH for profile
update, and response field names ship as annotated placeholders; tests use mocked responses.
**Why:** consistent with the existing lab convention (run offline, verify before live).

### D7: Read-only discovery is first-class
`list_desktop_profiles`, `get_desktop_profile`, `list_agents`, `get_agent`, and a derived
profile↔agent mapping are read tools so the model (and attendee) can *choose* which profile
to provision — this makes the "attach" write meaningful rather than arbitrary.

### D8: Two prompts
`sync_crm_to_address_book` (discover → sync → verify) and `provision_outbound_dialing`
(find/create book → sync from CRM → attach to a chosen profile → verify agents). **Why:**
the second prompt is what gives the desktop-profile/agent read tools a payoff and shows the
end-to-end arc. **Alternative:** one prompt — leaves discovery tools underused.

## Risks / Trade-offs

- **[Deleting the old scenario loses working tests/coverage]** → The retained infra keeps
  its tests; new tools get new mocked tests. Net coverage maintained, not reduced.
- **[Diff/prune could delete real contacts]** → `prune` (delete-missing) defaults off and is
  always elicitation-gated with an explicit preview count; write-safety guide documents it
  as HIGH risk.
- **[Wrong assumptions on v2 paths / field names break live use]** → All such values are
  `# VERIFY` placeholders; lab runs on mocks; README carries a VERIFY/TODO checklist.
- **[Address Book v1 removal (2026-10-15) / Desktop Profile field removal (2026-09-15)]** →
  Target v2 and avoid deprecated fields from the outset; note the dates in docs.
- **[Bulk-save semantics differ from per-entry writes]** → Provide both paths; the composite
  can use per-entry writes for clear progress and reserve bulk-save for a documented fast
  path, keyed by a `# VERIFY` on payload shape.
- **[Scope creep into dial-plan/outdial prerequisites]** → Explicitly a Non-Goal; docs note
  the manual prerequisites without automating them.

## Migration Plan

1. Add the new Config-family API modules, tools, resources, and prompts alongside the old
   ones (no import wiring yet).
2. Rewire `server.py` to register only the new surface; remove old registrations.
3. Delete the agent-lifecycle tools/resources/prompts/api modules and their tests.
4. Trim `config.py` to the Config family (drop Reporting/Platform bases, scopes, paths) and
   add Address Book v2 / Entry / Desktop Profile paths.
5. Reshape `models/schemas.py` to the new IO contracts.
6. Rewrite README and lab guide for the new scenario and primitive map.
7. Run `pytest`, `ruff`, `black`; verify the mocked suite is green.

**Rollback:** the change is confined to the domain layer plus docs; revert the commit to
restore the previous scenario. No data migration is involved (mocked lab).

## Open Questions

- Exact Address Book **v2** paths and the **entry** sub-resource path shape (`.../entry` vs
  `.../entries`) — VERIFY.
- The **agent→desktop-profile** link field name on the user record — VERIFY.
- **PUT vs PATCH** for the Desktop Profile update, and whether a full-object round-trip is
  required to avoid clobbering other fields — VERIFY.
- **Bulk-save** request/response shape and whether it upserts or replaces — VERIFY.
- Whether to ship the CRM source as a flat resource or a department-parameterized template
  (D2 stretch).
