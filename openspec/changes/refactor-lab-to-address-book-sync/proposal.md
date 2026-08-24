## Why

The current `wxcc-mcp-server` lab teaches MCP through the *agent lifecycle* (onboard →
diagnose → offboard), but that scenario sprawls across three API families (Config,
Reporting/Search, Platform/People) and ~20 tools, which is hard to teach in 20–30 minutes
and dilutes the core message. A single, tighter scenario — **synchronizing CRM contacts
into a Webex Contact Center Address Book and provisioning it for agents** — lives entirely
in the Config API family, maps cleanly onto every MCP primitive, and makes the
"why MCP over raw APIs" argument concrete: the model composes discovery, domain knowledge,
and safe writes autonomously.

## What Changes

- **BREAKING**: Remove the entire agent-lifecycle scenario — all user/team/skill/queue/
  state/search/callback tools, resources, and prompts, plus the People (Platform) and
  Reporting/Search API families and their config.
- **Keep the production infrastructure**: OAuth broker, async API client, typed Pydantic
  IO, structured logging with redaction, and the elicitation/dry-run write-safety pattern.
- **New scenario: CRM → Address Book sync + provisioning**, built entirely on the WxCC
  Config API family (`cjp:config_read` / `cjp:config_write`):
  - **Address Book tools (full CRUD)**: list, get, create, update, delete address books.
  - **Entry tools (full CRUD + bulk)**: list (with search/filter/attributes), get, create,
    update, delete, and bulk-save entries.
  - **Desktop Profile & agent discovery (read-only)**: list/get desktop profiles (exposing
    `addressBookId`), list/get agents, and surface which desktop profile is assigned to
    which agent.
  - **Provisioning write (gated)**: assign an address book to a specific desktop profile.
  - **Hero composite (gated + progress)**: `sync_crm_to_address_book` diffs CRM source data
    against existing entries and applies add/update/delete changes.
- **New resources**: a CRM contacts JSON snapshot (the sync source), an address-book schema
  guide (naming rules, E.164 phone format, `parentType` semantics), and the retained
  write-safety guide.
- **New prompts**: `sync_crm_to_address_book` (discover → sync → verify) and
  `provision_outbound_dialing` (full arc including attach-to-profile).
- **Remove all deprecated API usage**: target Address Book **v2** (v1 removed 2026-10-15),
  use Desktop Profile APIs (not Agent Profile), and avoid the deprecated Desktop Profile
  fields (`dialPlans`, `agentDNValidationCriteria`, `agentDNValidationCriterions`).
- **Update lab materials** (README, lab guide) to teach the new single scenario across all
  MCP primitives.

## Capabilities

### New Capabilities
- `address-book-management`: CRUD tools for WxCC address books and their entries, including
  bulk save, backed by typed IO and the gated-write safety pattern.
- `crm-address-book-sync`: the CRM-source resource plus the composite sync tool/prompt that
  diffs CRM contacts against existing entries and applies changes with elicitation,
  progress, and logging.
- `desktop-profile-provisioning`: read-only discovery of desktop profiles and agents (and
  the profile↔agent mapping) plus the gated write to assign an address book to a profile.
- `lab-mcp-primitive-coverage`: the lab narrative and materials that demonstrate every MCP
  primitive (tools, resources, prompts, elicitation, progress, logging, sampling) on this
  one scenario.

### Modified Capabilities
<!-- No existing main specs; all capabilities are new. -->

## Impact

- **Removed code**: `tools/` (get_user, get_user_config, list_agents kept-but-reshaped,
  get_agent_state_history, get_agent_login_session, get_team, get_queue, get_skill_profile,
  list_teams, list_skill_profiles, validate_agent_routing, manage_users, manage_callbacks,
  onboard flow), corresponding `api/` modules (state, search, teams, skills, queues,
  callbacks, users lifecycle, People), `resources/` (agent-states, error-codes,
  config-dependency-map, troubleshooting-runbook, onboarding-checklist),
  `prompts/` (onboard_new_agent, manage_scheduled_callbacks), and their tests.
- **Reshaped code**: `config.py` drops Reporting + Platform families, scopes, and endpoint
  paths; adds Address Book v2, Entry, and Desktop Profile paths (all Config family).
- **New code**: address-book/entry/desktop-profile `api/` modules and `tools/`, CRM +
  schema `resources/`, two new `prompts/`, the composite sync tool, and new tests.
- **Retained infra**: `auth/oauth.py`, `api/client.py`, `logging_config.py`, `errors.py`,
  typed IO in `models/schemas.py` (reshaped to the new contracts), and the
  elicitation/dry-run pattern in `server.py`.
- **Docs**: `wxcc-mcp-server/README.md` and `lab-materials/lab-guide/lab-guide.md` rewritten
  for the new scenario.
- **Security/scopes**: single scope pair `cjp:config_read` / `cjp:config_write`; no more
  People or analytics scopes.
