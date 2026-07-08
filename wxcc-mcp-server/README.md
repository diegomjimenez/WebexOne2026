# WxCC Agent Availability MCP Server

A read-only [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
connects an AI assistant to the **Webex Contact Center (WxCC)** public Admin/Config and
Reporting/Search APIs. Its first capability is a diagnostic workflow that answers:
**"Why can't this agent go Available?"**

This phase is **read-only** — no write/onboarding operations. The architecture leaves a
clean seam for a later write phase (with a `propose_change`/`commit_change` two-stage
commit and RBAC guardrails).

> **Important:** All WxCC endpoint paths, OAuth URLs, and scopes ship as **placeholders**
> marked `# VERIFY` / `# TODO`. You must resolve them against
> [developer.webex.com](https://developer.webex.com) before running against live APIs.
> See the [checklist](#verify--todo-checklist) below.

## Features

- **Per-session OAuth broker** — acquires, encrypts (at rest), stores per session, and
  refreshes tokens server-side. **Tokens are never exposed to the model** or returned in
  tool output.
- **Async API client** — bearer injection, retry/backoff with `Retry-After`, distinct base
  URLs for the Config vs. Reporting/Search API families, and typed error mapping.
- **7 read-only tools** + a composite `validate_agent_routing` that returns ranked,
  evidence-backed blocking issues.
- **4 reference resources** and a guided **diagnostic prompt**.

## Requirements

- Python 3.11+

## Setup

```bash
cd wxcc-mcp-server
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the environment template and fill in your values:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Generate a token encryption key and paste it into `.env` as `WXCC_TOKEN_ENCRYPTION_KEY`:

```bash
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

## OAuth configuration

1. Create a Webex integration and obtain a **client id** and **client secret**.
2. Register the **redirect URI** (default `http://localhost:8765/oauth/callback`).
3. Grant scopes that cover **both** Config API reads **and** Reporting/Search API reads,
   and set them in `.env` (`WXCC_CONFIG_API_SCOPES`, `WXCC_REPORTING_API_SCOPES`).
4. Set the **authorization** and **token** endpoints (`WXCC_OAUTH_AUTHORIZE_URL`,
   `WXCC_OAUTH_TOKEN_URL`) and the two **API base URLs** for your region.

> The exact endpoints, scope strings, and API paths are environment-/region-specific.
> Confirm every `# VERIFY` / `# TODO` item below.

## Running the server

```bash
wxcc-mcp-server           # console script
# or
python -m wxcc_mcp.server
```

The server runs over **stdio** transport, suitable for a local MCP-capable client.

## Connecting an MCP client

Example client configuration (adapt to your client's config format):

```json
{
  "mcpServers": {
    "wxcc": {
      "command": "wxcc-mcp-server",
      "cwd": "/absolute/path/to/wxcc-mcp-server"
    }
  }
}
```

Once connected, the client exposes:

- **Tools:** `tool_get_user`, `tool_get_user_config`, `tool_get_agent_state_history`,
  `tool_get_agent_login_session`, `tool_get_team`, `tool_get_queue`,
  `tool_get_skill_profile`, `tool_validate_agent_routing`.
- **Resources:** `wxcc://reference/agent-states`, `wxcc://reference/error-codes`,
  `wxcc://reference/config-dependency-map`, `wxcc://reference/troubleshooting-runbook`.
- **Prompt:** `diagnose_agent_cannot_go_available` (args: `agent_identifier`, `org_id`).

## Testing

Tests use mocked WxCC responses (`httpx.MockTransport`) and never hit live APIs:

```bash
pytest
ruff check .
black --check .
```

## Project layout

```
src/wxcc_mcp/
  server.py            # MCP entrypoint (registers tools/resources/prompt)
  config.py            # Settings + VERIFY/TODO endpoint & scope constants
  errors.py            # Typed exception hierarchy
  logging_config.py    # Structured logging with secret redaction
  auth/oauth.py        # Per-session OAuth token broker (encrypted at rest)
  api/                 # Async client + per-family endpoint modules
  tools/               # 7 read tools + validate_agent_routing composite
  resources/           # Reference data (states, error codes, deps, runbook)
  prompts/             # diagnose_agent_cannot_go_available
  models/schemas.py    # Pydantic I/O contracts
tests/                 # Mocked-response tests
```

## VERIFY / TODO checklist

Resolve **every** item below against developer.webex.com before live use. Grep the code
for `VERIFY` and `TODO` to find them in context.

### `.env` / `config.py`
- [ ] `WXCC_CONFIG_API_BASE` — Config API base URL for your region. **VERIFY**
- [ ] `WXCC_REPORTING_API_BASE` — Reporting/Search API base URL for your region. **VERIFY**
- [ ] `WXCC_OAUTH_AUTHORIZE_URL` — OAuth authorization endpoint. **VERIFY**
- [ ] `WXCC_OAUTH_TOKEN_URL` — OAuth token endpoint. **VERIFY**
- [ ] `WXCC_CONFIG_API_SCOPES` — exact scope string(s) for Config reads. **TODO/VERIFY**
- [ ] `WXCC_REPORTING_API_SCOPES` — exact scope string(s) for Reporting reads. **TODO/VERIFY**

### Endpoint paths (`config.py`)
- [ ] `USERS_PATH` and `USER_BY_EMAIL_QUERY_PARAM` (user search by email). **VERIFY**
- [ ] `USER_BY_ID_PATH` (user by id). **VERIFY**
- [ ] `USER_CONFIG_PATH` (teams / skill profile / agent profile / multimedia profile — one
      endpoint or several?). **VERIFY**
- [ ] `TEAM_BY_ID_PATH`. **VERIFY**
- [ ] `QUEUE_BY_ID_PATH` (Contact Service Queue). **VERIFY**
- [ ] `SKILL_PROFILE_BY_ID_PATH`. **VERIFY**
- [ ] `AGENT_STATE_HISTORY_PATH` + query params. **VERIFY**
- [ ] `AGENT_SESSION_PATH` + query params. **VERIFY**

### OAuth flow (`auth/oauth.py`)
- [ ] Authorization URL parameter names. **TODO/VERIFY**
- [ ] Token exchange request shape and response fields (`access_token`, `refresh_token`,
      `expires_in`, `scope`). **TODO/VERIFY**
- [ ] Refresh grant request/response shape. **TODO/VERIFY**

### Response field mappings (`tools/*.py`, `api/state.py`)
- [ ] Confirm the JSON field names each tool maps (all marked `# VERIFY`), e.g. `displayName`,
      `licenses`, `skillProfile`, `multimediaProfile.channelsEnabled`, state transition fields
      (`toState`, `reasonCode`, `timestamp`), session fields (`active`, `loginTimestamp`).

### Reference data (`resources/*.py`)
- [ ] `agent_state_reference` — confirm state names, blocking semantics, forced-idle reason
      codes. **VERIFY**
- [ ] `error_code_catalog` — populate real codes/remediations. **TODO**

## Security notes

- No hardcoded secrets — all credentials come from the environment / `.env`.
- Access/refresh tokens are encrypted at rest and never logged (redaction) or returned to
  the model.
- Read-only: the server performs no WxCC writes in this phase.
```
