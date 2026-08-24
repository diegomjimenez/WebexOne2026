## Context

Contact center admins repeatedly diagnose the same question — *"Why can't this agent go Available?"* — by manually correlating an agent's user record, team, queue(s), skill profile, multimedia profile, and live/recent state across multiple WxCC admin surfaces. WxCC exposes this data through two distinct public API families with different base URLs and scopes: an **Admin/Config API** (users, teams, queues, skill profiles) and a **Reporting/Search API** (agent state history, login sessions). We will build a standalone Python MCP server that brokers per-user OAuth access to these APIs and exposes read-only diagnostic tools, reference resources, and a guided prompt to an AI assistant.

Key constraints:
- **No invented API surface.** Exact endpoint paths, OAuth authorization/token URLs, parameter names, and scope strings are unknown at authoring time and MUST be filled from developer.webex.com. All such values are placeholder constants marked `# VERIFY` / `# TODO`.
- **Read-only** in this phase; the design must remain extensible for a later write phase.
- **Tokens must never reach the model.** The server brokers and refreshes tokens server-side; nothing token-shaped appears in tool output.
- Tests must never hit live APIs — all WxCC responses are mocked.

## Goals / Non-Goals

**Goals:**
- A working, typed, testable MCP server scaffold following the official MCP Python SDK (FastMCP/standard pattern).
- Clean separation of concerns: `config` (settings/constants) → `auth` (token broker) → `api` (HTTP client + per-family endpoint modules) → `tools` (MCP tools) → `resources`/`prompts` (knowledge) → `server` (wiring).
- A composite `validate_agent_routing` tool that orchestrates the atomic tools and returns ranked, evidence-backed blocking issues.
- Deterministic tests with mocked WxCC responses for every tool and for the composite.
- A README that lists every `# VERIFY`/`# TODO` a developer must resolve before live use.

**Non-Goals:**
- Any write/mutation operation (onboarding, config edits). Deferred to Phase 2 with a `propose_change`/`commit_change` two-stage-commit pattern and RBAC guardrails.
- Verifying or discovering the real WxCC endpoint paths/scopes (explicitly left as developer-resolved TODOs).
- A production token store (e.g., HSM/KMS-backed). Phase 1 uses an encrypted, per-session in-memory/local store abstraction with a clear seam for a hardened backend.
- A hosted deployment; Phase 1 targets local `stdio` transport for an MCP-capable client.

## Decisions

### D1. MCP Python SDK with FastMCP-style registration
Use the official `mcp` package. Register tools/resources/prompts in `server.py`, delegating logic to `tools/`, `resources/`, `prompts/` modules. Rationale: first-party SDK, least surprise for MCP clients. Alternative considered: a bespoke JSON-RPC server — rejected (reinvents the SDK, higher maintenance).

### D2. Layered architecture with a single token-brokering seam
All outbound calls flow `tool → api.<family> → api.client → auth.oauth.get_valid_token(session_id)`. Only `auth/oauth.py` and `api/client.py` ever touch tokens. Rationale: one place to enforce "tokens never leave the server," and one place to add refresh/rotation. Alternative: tools calling `httpx` directly — rejected (token handling would be scattered and leak-prone).

### D3. Two API families kept explicitly distinct
`config.py` holds separate `CONFIG_API_BASE` and `REPORTING_API_BASE` constants and separate scope lists. `api/users.py`, `api/teams.py`, `api/queues.py`, `api/skills.py` target the Config family; `api/state.py` targets the Reporting/Search family. Rationale: the families differ in base URL and scopes; conflating them causes subtle auth failures. Every path is a named constant annotated `# VERIFY against developer.webex.com`.

### D4. Placeholder-constant strategy for all external identifiers
Endpoint paths, OAuth URLs, and scopes live as named constants in `config.py` (or module-level constants) with `# VERIFY` / `# TODO` comments; none are inlined or guessed. Rationale: the biggest risk in an API integration is confidently wrong endpoints; centralizing and flagging them makes the "fill from docs" step explicit and greppable. The README enumerates them.

### D5. Typed exception hierarchy mapped at the client boundary
`api/client.py` maps non-2xx to `NotFoundError`, `InsufficientPermissionsError`, `RateLimitError`, `WxccApiError`. Tools catch these and produce plain-language, token-free results. `403` specifically becomes an `InsufficientPermissionsError` → "you don't have rights to do X." Rationale: keeps HTTP concerns out of tools and gives the model actionable, safe messages.

### D6. Retry/backoff centralized in the client
Exponential backoff with jitter for `429`/`5xx`, honoring `Retry-After`; no retries for 4xx (except 429). Configurable max attempts. Rationale: resilience without hammering; single implementation shared by all tools.

### D7. Pydantic models as the tool I/O contract
`models/schemas.py` defines input and output models for every tool; `validate_agent_routing` composes sub-results into a `RoutingValidationResult` with `checks[]` and ranked `blocking_issues[]`. Rationale: typed, JSON-serializable contracts that double as test fixtures and MCP schema sources.

### D8. Composite orchestration is pure over atomic tool outputs
`validate_agent_routing` calls the atomic tool functions, then evaluates each check (`user_active_and_licensed`, `team_assigned`, `team_mapped_to_active_queue`, `skills_match_queue_requirements`, `channel_enabled_in_multimedia_profile`, `no_blocking_state`, `session_active`) as a pure function of gathered data, so ranking/evidence logic is unit-testable without I/O. Rationale: deterministic tests, clear evidence trail.

### D9. Resources as loadable structured content
`agent_state_reference`, `error_code_catalog`, `config_dependency_map`, `troubleshooting_runbook` are static/loadable structured data (seeded, with `# TODO: populate from WxCC docs` where real values are needed). Rationale: the prompt cross-references them; keeping them as data (not prose) makes them testable and updatable.

### D10. Structured logging of every API call and tool invocation
Use `structlog` (or stdlib `logging` + JSON formatter). Redact tokens and Authorization headers at the logging boundary. Rationale: auditability and debugging without secret leakage.

### D11. Local `stdio` transport for Phase 1
Run the server over `stdio` for an MCP-capable client; README documents client wiring. Rationale: simplest secure local integration; avoids network-exposure concerns (DNS rebinding, CORS/CSRF) until a remote deployment is actually needed.

## Risks / Trade-offs

- **Wrong/placeholder endpoints or scopes** → Centralize all of them as `# VERIFY`/`# TODO` constants and enumerate them in the README; the server is not expected to run live until resolved. Tests use mocks, so development proceeds without them.
- **Token leakage into logs or tool outputs** → Single brokering seam (D2), redaction at the logging boundary (D10), and an explicit test asserting no token material appears in tool outputs.
- **Per-session isolation bugs** → Session-scoped storage keyed by `session_id`; test that session A cannot read session B's token.
- **Reporting/Search API latency or eventual consistency** (state history may lag) → Tools report timestamps and lookback windows explicitly so the assistant can reason about staleness; `no_blocking_state` treats stale/uncertain data as a `warning`, not a hard `pass`.
- **Over-eager retries causing rate-limit storms** → Honor `Retry-After`, cap attempts, add jitter (D6).
- **Composite tool masking partial failures** → If an atomic call fails (e.g., 403 on Reporting API), the corresponding check returns `warning`/`fail` with the plain-language reason rather than aborting the whole diagnosis.
- **Scope creep toward writes** → Non-Goals explicitly exclude writes; architecture leaves a clean seam (new `writes/` layer + two-stage commit) for Phase 2 without refactoring reads.

## Migration Plan

Greenfield, additive component — no migration of existing data or behavior.
1. Scaffold project (`pyproject.toml`, `config.py`, `models/schemas.py`) and pause for review (per build brief).
2. Implement `auth/oauth.py` (with TODO placeholders) and `api/client.py`.
3. Implement atomic tools (1–7) with mocked-response tests.
4. Implement `validate_agent_routing` (8) + tests.
5. Implement resources, then the prompt.
6. Wire `server.py`, finalize README with the `# VERIFY`/`# TODO` checklist.

Rollback: delete the `wxcc-mcp-server/` directory; no other workspace code is touched.

## Open Questions

- Exact WxCC OAuth authorization/token endpoints and the precise scope strings for Config vs. Reporting/Search reads (developer must supply from developer.webex.com).
- Exact endpoint paths and query/parameter names for each resource family.
- Whether agent state history and login-session data come from one Reporting/Search endpoint or several.
- Long-term token storage backend (in-memory vs. encrypted local file vs. KMS) for beyond Phase 1.
- Whether org context is always a caller-supplied `org_id` or can be derived from the token.
