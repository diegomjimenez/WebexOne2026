## 1. Project scaffold, config & models

- [x] 1.1 Create the `wxcc-mcp-server/` directory tree exactly as specified in the build brief (`src/wxcc_mcp/{auth,api,tools,resources,prompts,models}` with `__init__.py` files, plus `tests/`).
- [x] 1.2 Write `pyproject.toml` with pinned dependencies: `mcp`, `httpx`, `pydantic`, `pydantic-settings`, `structlog`; dev deps `pytest`, `pytest-asyncio`, `ruff`, `black`; configure `ruff`/`black` and the `src/` package layout.
- [x] 1.3 Write `.env.example` listing every required var with placeholder values: `client_id`, `client_secret`, `redirect_uri`, `org_id`, `config_api_base`, `reporting_api_base`, and token scopes.
- [x] 1.4 Implement `config.py` with `pydantic-settings` Settings loading `.env`, and centralized named constants for `CONFIG_API_BASE`, `REPORTING_API_BASE`, OAuth authorization/token URLs, and scope lists — each marked `# VERIFY`/`# TODO` against developer.webex.com. Keep Config and Reporting/Search families distinct.
- [x] 1.5 Implement `models/schemas.py` with Pydantic input and output models for all seven atomic tools and the composite `validate_agent_routing` (`RoutingValidationResult` with `checks[]{check,status,detail}` and ranked `blocking_issues[]`).
- [ ] 1.6 **PAUSE for review** of scaffold, `pyproject.toml`, `config.py`, and `models/schemas.py` before continuing (per build brief).

## 2. Auth broker & API client

- [x] 2.1 Implement `auth/oauth.py`: OAuth 2.0 Authorization Code flow with `get_valid_token(session_id)`, per-session encrypted-at-rest token storage, and automatic refresh. Add `# TODO` placeholders for exact IdP endpoints/scopes (reference `config.py` constants; never invent URLs).
- [x] 2.2 Ensure per-session isolation (session A cannot read session B's token) and that tokens are never returned to callers/model.
- [x] 2.3 Define the typed exception hierarchy (`WxccApiError`, `NotFoundError`, `InsufficientPermissionsError`, `RateLimitError`) and an auth-error type; raise `InsufficientPermissionsError` on `403`.
- [x] 2.4 Implement `api/client.py`: async `httpx.AsyncClient` wrapper injecting the bearer token per session, selecting the correct family base URL, with exponential backoff + jitter for `429`/`5xx`, `Retry-After` handling, no retries on other 4xx, and non-2xx → typed-exception mapping.
- [x] 2.5 Add structured logging (`structlog`) of every API call and tool invocation, with redaction of tokens/Authorization headers.
- [x] 2.6 Implement per-family endpoint modules `api/users.py`, `api/teams.py`, `api/queues.py`, `api/skills.py` (Config family) and `api/state.py` (Reporting/Search family), each with named path constants marked `# VERIFY`.

## 3. Atomic read-only tools (with tests)

- [x] 3.1 Implement `tools/get_user.py` (identifier email/user_id + org_id → user_id, email, display_name, active, licenses[], last_modified).
- [x] 3.2 Implement `tools/get_user_config.py` (user_id + org_id → teams[], skill_profile{skills[]}, agent_profile, multimedia_profile{channels_enabled[]}).
- [x] 3.3 Implement `tools/get_agent_state_history.py` (user_id + org_id + lookback_minutes=120 → current_state, current_state_since, transitions[]) via Reporting/Search API.
- [x] 3.4 Implement `tools/get_agent_login_session.py` (user_id + org_id → session_active, last_login, device/channel info) via Reporting/Search API.
- [x] 3.5 Implement `tools/get_team.py` (team_id + org_id → team_name, site, members[], associated_queues[]).
- [x] 3.6 Implement `tools/get_queue.py` (queue_id + org_id → queue_name, active, channel_type, required_skills[], routing_type).
- [x] 3.7 Implement `tools/get_skill_profile.py` (profile_id + org_id → profile_name, skills[]{name,type,values}).
- [x] 3.8 Add `tests/conftest.py` with fixtures providing mocked WxCC API responses (no live calls) and a mocked auth broker.
- [x] 3.9 Add `tests/test_tools.py` covering each atomic tool's success path, not-found (`404`→NotFoundError), and permission (`403`→plain-language) behavior.

## 4. Composite validate_agent_routing (with tests)

- [x] 4.1 Implement `tools/validate_agent_routing.py` orchestrating the atomic tools and evaluating checks: `user_active_and_licensed`, `team_assigned`, `team_mapped_to_active_queue`, `skills_match_queue_requirements`, `channel_enabled_in_multimedia_profile`, `no_blocking_state` (RONA/forced idle from state history), `session_active`.
- [x] 4.2 Implement ranking of blocking issues by likelihood with cited evidence; keep check evaluation a pure function of gathered data for testability. Treat stale/uncertain state data as `warning`, not `pass`.
- [x] 4.3 Add `tests/test_validate_routing.py`: all-pass case, single-blocking-cause case (ranked with evidence), warning-does-not-block case, and a partial-failure case (e.g., 403 on Reporting API → warning).

## 5. Resources (reference data)

- [x] 5.1 Implement `resources/agent_state_reference.py` enumerating WxCC states, meaning, and Available-blocking flag (RONA, Idle+reason codes, Available, Not Responding).
- [x] 5.2 Implement `resources/error_code_catalog.py` as structured `{code, meaning, likely_cause, remediation}` seeded with placeholders and `# TODO: populate from WxCC docs`.
- [x] 5.3 Implement `resources/config_dependency_map.py` documenting user→team(s)→queue(s)→skills, user→skill profile→skills, user→multimedia profile→channels, and the Available-requires-alignment rule.
- [x] 5.4 Implement `resources/troubleshooting_runbook.py` as the ordered decision tree ending in escalation.

## 6. Diagnostic prompt

- [x] 6.1 Implement `prompts/diagnose_agent_cannot_go_available.py` with required args `agent_identifier`, `org_id`; set a READ-ONLY admin-assistant role forbidding executing/suggesting direct changes as actions; instruct following runbook order and stopping early on a confirmed blocking cause; cross-reference `troubleshooting_runbook`, `agent_state_reference`, `error_code_catalog`; require ranked, evidence-cited causes with remediations (flagging write-required remediations without performing them), in plain-language bullets.

## 7. Server wiring & docs

- [x] 7.1 Implement `server.py` as the MCP server entrypoint (official MCP Python SDK / FastMCP pattern) registering all tools, resources, and the prompt; run over local `stdio` transport.
- [x] 7.2 Write `README.md` covering setup, OAuth configuration steps, running the server, connecting an MCP-capable client, and a clearly labeled checklist of every `# VERIFY`/`# TODO` to resolve against developer.webex.com before live use.
- [x] 7.3 Run `ruff`, `black`, and `pytest`; ensure the suite passes against mocked responses and no live API calls occur.
