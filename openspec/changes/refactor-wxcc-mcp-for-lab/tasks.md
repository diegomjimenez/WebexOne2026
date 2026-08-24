## 1. Freeze scope and baseline

- [x] 1.1 Confirm the keep-list of tools (diagnose + support + onboard/offboard) and record it at the top of the change
- [x] 1.2 Capture a baseline: run existing tests and an import smoke test (`python -c "import wxcc_mcp.server"`) so regressions are detectable
- [x] 1.3 Tag/note the current commit so deleted code is easy to recover from git history

## 2. Delete out-of-scenario tools

- [x] 2.1 Delete real-time/supervisory tool modules (queue stats, active agents, org realtime summary, abandoned/live contacts, interval/service-level reports, agent summary stats, force logout, change agent state)
- [x] 2.2 Delete full-CRUD management tool modules (manage_queues, manage_skills, manage_entry_points, manage_sites, manage_agent_profiles, manage_multimedia_profiles, manage_teams-CRUD, manage_users write beyond onboard/offboard as needed)
- [x] 2.3 Delete advanced-admin tool modules (routing strategies, business hours, holiday lists, flows, audio files, webhooks, global variables, outdial ANI, campaigns)
- [x] 2.4 Remove the corresponding `list_*`/`get_*` tools that only served deleted domains, keeping only list_agents, list_teams, list_skill_profiles (ID discovery for the scenario)

## 3. Delete supporting layers for removed tools

- [x] 3.1 Delete now-unused `api/` modules (queues, skills, entry_points, sites, agent_profiles, multimedia_profiles, routing_strategies, business_hours, holiday_lists, flows, audio_files, webhooks, global_variables, outdial_ani, campaigns, realtime, search — keep only what diagnose/onboard/offboard use)
- [x] 3.2 Prune `models/schemas.py` to only the retained tools' input/output models
- [x] 3.3 Delete out-of-scenario prompts, keeping `diagnose_agent_cannot_go_available` and `onboard_new_agent`
- [x] 3.4 Delete out-of-scenario resources, keeping agent_state_reference, troubleshooting_runbook, config_dependency_map, write_safety_guide
- [x] 3.5 Remove now-unused config constants/endpoints in `config.py`

## 4. Rewire the server

- [x] 4.1 Update `server.py` tool/prompt/resource registrations to the curated set
- [x] 4.2 Update `tools/__init__.py`, `prompts/__init__.py`, `resources/__init__.py` exports
- [x] 4.3 Remove the toolset-gating layer (`apply_toolset_filter`, `_CORE/_REALTIME/_WRITE` sets) and its `WXCC_TOOLSETS` config path, verifying nothing else depends on it
- [x] 4.4 Run the import smoke test; confirm the server starts and lists the curated manifest with no dead references

## 5. Add MCP primitive depth

- [x] 5.1 Replace the `confirm=True` write gate with `ctx.elicit` confirmation (preview → elicit approve/reject → commit) in onboard and offboard tools
- [x] 5.2 Provide a safe fallback when the client does not support elicitation (explicit confirm arg or safe abort)
- [x] 5.3 Add `ctx.report_progress` across the onboarding steps (create → assign team → assign skill profile → verify)
- [x] 5.4 Add client-facing logging (`ctx.info`/`ctx.warning`/`ctx.error`) at noteworthy steps in diagnose and onboard/offboard
- [x] 5.5 (Optional/stretch) Add sampling to summarize a diagnosis via `ctx.session`, guarded by a capability check with graceful fallback

## 6. Structure for build-live vs pre-built delivery

- [x] 6.1 Identify/prepare the minimal "starter" surface attendees build live (one tool + one resource + one prompt) and document its boundary
- [x] 6.2 Ensure the pre-built rich flows (diagnose/onboard/offboard) are clearly separated and runnable independently of the starter

## 7. Tests and docs

- [x] 7.1 Delete or rewrite tests that reference removed modules; add tests for the elicitation confirmation path and progress/logging
- [x] 7.2 Run `pytest`, `ruff check .`, `black --check .` and fix fallout
- [x] 7.3 Rewrite `README.md` around the agent-lifecycle scenario, the MCP primitives it demonstrates, and the build-live vs pre-built split; remove references to deleted tools
- [x] 7.4 Update the VERIFY/TODO checklist in the README to match the reduced surface

## 8. Validate

- [x] 8.1 Run `openspec validate refactor-wxcc-mcp-for-lab --strict` and resolve issues
- [x] 8.2 Manually exercise the scenario end-to-end (onboard → diagnose → offboard) against a test org or mocked transport
- [ ] 8.3 Confirm the tool manifest loads in the target MCP client without toolset gating
