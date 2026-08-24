## Context

`wxcc-mcp-server` currently registers ~100 tools, 13 prompts, and 13 resources over four
phases (read, real-time/supervisory, CRUD, advanced). It has a per-session OAuth broker,
an async API client with two API families (Config + Reporting/Search), typed Pydantic
schemas, structured logging with secret redaction, and a toolset-gating layer that exists
only because the manifest is too large for some clients.

The end goal is a **WebexOne hands-on lab** teaching MCP server principles. The custom-
server section is ~90 minutes across three domains; WxCC gets ~20–30 minutes. The lab must
be teachable, not comprehensive. Decisions already made with the stakeholder:

- Slim the existing server **in place** (refactor, not a parallel repo).
- **Delete** out-of-scenario breadth (no archive branch, no hidden gating).
- Unify on **one scenario**: the agent lifecycle (onboard → diagnose → offboard).
- Delivery shape: attendees **build a minimal server live**, the rich flows are **pre-built**.
- **Touch every MCP primitive**, including elicitation, progress, and client logging.

## Goals / Non-Goals

**Goals:**
- Reduce to ~12 tools / ~4 resources / ~2 prompts serving the agent-lifecycle scenario.
- Demonstrate the full MCP primitive surface: tools, resources, prompts, elicitation,
  progress notifications, client-facing logging, and (optionally) sampling.
- Keep the manifest small enough to drop the toolset-gating workaround.
- Preserve production-quality infra (OAuth broker, client, typed IO, error translation,
  redacted logging) as teaching examples of "doing it right."
- Ship a lab-oriented README and a clear "build-live starter vs pre-built" separation.

**Non-Goals:**
- Webex Calling troubleshooting or any multi-domain coverage (deferred).
- Backward compatibility with the deleted tools (this is intentionally BREAKING).
- Building the Meetings-MCP or Webex-Bot sections of the lab (separate lab modules).
- Live remote/multi-tenant deployment; stdio single-user remains the target.

## Decisions

### D1: Refactor in place and delete breadth (vs. branch/gate)
Delete Phase 2/3/4 tools, their `api/` modules, schema classes, prompts, and resources
outright. Rationale: dead or hidden code confuses learners reading the repo; the stakeholder
explicitly chose the cleanest surface. Git history preserves the removed work if ever needed.
*Alternative considered:* keep them behind toolset gating — rejected because it leaves a
large, distracting manifest and gating logic that isn't part of the lesson.

### D2: One scenario expressed as three acts
Keep the tools that serve onboard, diagnose, offboard:
```
Diagnose (read):  get_user, get_user_config, get_agent_state_history,
                  get_agent_login_session, get_team, get_queue,
                  get_skill_profile, validate_agent_routing (composite)
Support (read):   list_agents, list_teams, list_skill_profiles   (to pick IDs)
Onboard/Offboard: create_user, assign_skill_profile, assign_agent_to_team,
                  deactivate_user
```
Rationale: a single narrative is easier to teach than a catalog; each act maps to a
different MCP capability class (read vs write) and different primitives.

### D3: Elicitation replaces the confirm boolean
Write tools currently gate on `confirm=True` and return a preview when false. Change the
primary confirmation mechanism to `ctx.elicit`: the tool builds a preview, elicits an
approve/reject (and possibly missing fields), then commits. Rationale: elicitation is a
core MCP primitive and a far stronger teaching moment than a boolean flag. Keep a
preview-first step regardless.
*Alternative considered:* keep `confirm=True` — rejected; it hides the primitive we want to teach.
*Trade-off:* elicitation requires client support; see R2.

### D4: Progress + client logging in onboarding
Onboarding is naturally multi-step (create → assign team → assign skill profile → verify).
Wrap it with `ctx.report_progress` and `ctx.info/warning` so learners observe these
notification channels. Rationale: cheap to add, directly demonstrates two more primitives.

### D5: Sampling is optional/stretch
Demonstrate `ctx.session` sampling to summarize a diagnosis, guarded by a capability check
with graceful fallback. Rationale: rounds out "all primitives" but must not break clients
that lack sampling; kept optional to protect the lab timebox.

### D6: Two-layer code layout for build-live vs pre-built
Present the server so the "starter" (one tool + one resource + one prompt) is obviously
separable from the pre-built rich flows — e.g. a documented minimal example plus the full
implementation, with README callouts. Rationale: supports the chosen delivery format.

### D7: Retain infra, trim schemas
Keep `auth/oauth.py`, `api/client.py`, `config.py`, `logging_config.py`, `errors.py`.
Prune `models/schemas.py` to only the retained tools' IO models. Remove now-unused config
constants (endpoints for deleted entities). Rationale: infra is exemplary and reusable;
schemas must not reference deleted flows.

## Risks / Trade-offs

- **Large deletion breaks imports** → Refactor `server.py`, `tools/__init__.py`,
  `prompts/__init__.py`, `resources/__init__.py`, and `models/schemas.py` together;
  run an import smoke test and the trimmed test suite after each removal batch.
- **Elicitation client support varies** → Provide a fallback path (e.g. honor an explicit
  `confirm` argument or abort safely) so the lab still runs on clients without elicitation.
- **Losing genuinely useful tooling** → Accepted; git history retains it, and the deferred
  Calling/advanced work can cherry-pick later.
- **Toolset-gating removal** → Verify no other code path depends on `apply_toolset_filter`
  before deleting it; keep `WXCC_TOOLSETS` as a no-op or remove its config cleanly.
- **Tests reference deleted modules** → Delete/rewrite affected tests in the same batches
  to keep the suite green.
- **README drift** → The current README already under-describes the server; rewrite it as
  part of this change rather than patching.

## Migration Plan

1. Freeze the tool keep-list (D2); everything else is a deletion target.
2. Delete in dependency-safe batches: tools → prompts → resources → api modules → schema
   classes → config constants, re-running an import smoke test each batch.
3. Rewire `server.py` registrations and remove toolset gating.
4. Add elicitation to writes; add progress + ctx-logging to onboarding; (optional) sampling.
5. Trim/rewrite tests; rewrite README around the lab scenario and primitive coverage.
6. Rollback strategy: revert the change branch; deleted code remains in git history.

## Open Questions

- Should `validate_agent_routing` be the single "hero" tool attendees study, or the tool
  they build live? (Leaning: they build a *tiny* read tool; `validate_agent_routing` is
  pre-built and studied.)
- Is sampling worth the timebox, or documented-but-not-implemented? (Leaning: implement
  behind a capability check only if time allows.)
- Do we keep `list_*` helpers as tools, or fold ID discovery into prompts to shrink the
  manifest further?
