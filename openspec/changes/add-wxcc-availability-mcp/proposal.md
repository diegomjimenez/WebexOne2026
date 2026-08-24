## Why

Contact center administrators frequently field the same escalation — *"Why can't this agent go Available?"* — and answering it requires manually cross-referencing an agent's user config, team, queue, skill profile, multimedia profile, and live state across several disconnected Webex Contact Center (WxCC) admin screens and APIs. This is slow, error-prone, and hard to delegate. Exposing the WxCC public Admin/Config and Reporting/Search APIs to an AI assistant through a purpose-built MCP server lets an admin ask the question in plain language and get a ranked, evidence-backed diagnosis in seconds. Building it read-only first establishes a safe, auditable foundation before any write/onboarding automation is added.

## What Changes

- Introduce a new standalone Python (3.11+) **MCP server** (`wxcc-mcp-server`) built on the official MCP Python SDK that brokers access to WxCC public APIs for an AI assistant.
- Add a **per-user OAuth 2.0 token broker** that acquires, stores (encrypted, per-session), and refreshes tokens server-side. Tokens are NEVER exposed to the model or returned in tool outputs.
- Add an **async HTTP client** wrapping `httpx` with bearer-token injection, exponential backoff/`Retry-After` handling for `429`/`5xx`, and mapping of non-2xx responses to typed exceptions (`NotFoundError`, `InsufficientPermissionsError`, `RateLimitError`, `WxccApiError`).
- Add **seven read-only diagnostic tools**: `get_user`, `get_user_config`, `get_agent_state_history`, `get_agent_login_session`, `get_team`, `get_queue`, `get_skill_profile`.
- Add one **composite read-only tool** `validate_agent_routing` that orchestrates the above and returns ranked, evidence-backed blocking issues.
- Add **four MCP resources** (reference data): `agent_state_reference`, `error_code_catalog`, `config_dependency_map`, `troubleshooting_runbook`.
- Add one **MCP prompt** `diagnose_agent_cannot_go_available` that drives a read-only diagnostic session following the runbook decision tree.
- Ship `pyproject.toml` (pinned deps), `.env.example`, `README.md`, and `pytest` suites with mocked WxCC responses (no live API calls in tests).
- All WxCC endpoint paths, OAuth URLs, and scopes are **placeholder constants** marked `# VERIFY` / `# TODO` against developer.webex.com — no invented endpoints.
- **Non-breaking / additive only.** No write operations in this phase (reads only). Write capabilities (onboarding, config changes with guardrails) are explicitly deferred to a future phase, and the architecture is kept extensible for them.

## Capabilities

### New Capabilities
- `wxcc-mcp-auth`: Per-session OAuth 2.0 token broker — acquisition, encrypted per-session storage, automatic refresh, scope coverage for both Config and Reporting/Search API families, and typed permission-error mapping. Tokens are never exposed to the model.
- `wxcc-api-client`: Async WxCC API client — bearer injection, retry/backoff with `Retry-After`, distinct base URLs for Config vs. Reporting/Search families, and typed exception mapping for non-2xx responses.
- `wxcc-diagnostic-tools`: The seven read-only MCP tools plus the composite `validate_agent_routing` tool, each with typed Pydantic input/output schemas.
- `wxcc-diagnostic-knowledge`: The MCP resources (agent-state reference, error-code catalog, config-dependency map, troubleshooting runbook) and the `diagnose_agent_cannot_go_available` prompt that together encode read-only diagnostic guidance.

### Modified Capabilities
<!-- None. This is a greenfield addition; no existing specs change. -->

## Impact

- **New project/component:** `wxcc-mcp-server/` (self-contained; does not modify existing workspace code).
- **APIs consumed:** WxCC public Admin/Config API and Reporting/Search API (two distinct families, distinct base URLs and scopes). All paths are placeholder constants pending verification.
- **Dependencies added:** `mcp`, `httpx`, `pydantic`, `pydantic-settings`, `structlog` (or stdlib JSON logging), plus dev deps `pytest`, `ruff`, `black`.
- **Secrets/config:** Requires OAuth client credentials, redirect URI, org ID, API base URLs, and token scopes supplied via `.env` (never hardcoded).
- **Security posture:** Read-only in this phase; no destructive operations. Tokens brokered server-side and never surfaced to the model. `403`s surface as plain-language permission messages.
- **Out of scope (deferred):** Phase 2 write operations (onboarding, config changes) with `propose_change`/`commit_change` two-stage-commit pattern and RBAC guardrails.
