"""MCP server entrypoint.

Registers the read-only diagnostic tools, reference resources, and the
diagnostic prompt, and runs over local ``stdio`` transport.

Tokens are brokered per session by :class:`OAuthBroker` and never exposed to the
model. Tools translate typed API errors into plain-language messages.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .api.client import WxccApiClient
from .auth.oauth import OAuthBroker
from .config import get_settings
from .errors import WxccError
from .logging_config import configure_logging, get_logger
from .models.schemas import (
    GetAgentLoginSessionInput,
    GetAgentStateHistoryInput,
    GetQueueInput,
    GetSkillProfileInput,
    GetTeamInput,
    GetUserConfigInput,
    GetUserInput,
    ListAgentsInput,
    ValidateAgentRoutingInput,
)
from .prompts import diagnose_agent_cannot_go_available as diag_prompt
from .resources import (
    agent_state_reference,
    config_dependency_map,
    error_code_catalog,
    troubleshooting_runbook,
)
from .tools import (
    get_agent_login_session,
    get_agent_state_history,
    get_queue,
    get_skill_profile,
    get_team,
    get_user,
    get_user_config,
    list_agents,
    validate_agent_routing,
)
from .tools._common import translate_error

logger = get_logger(__name__)

mcp = FastMCP("wxcc-mcp-server")

_broker: OAuthBroker | None = None
_client: WxccApiClient | None = None


def _get_client() -> WxccApiClient:
    """Return the lazily-initialized broker-backed API client."""
    global _broker, _client
    if _broker is None:
        _broker = OAuthBroker()
    if _client is None:
        _client = WxccApiClient(_broker)
    return _client


def _session_id(ctx: Context | None) -> str:
    """Derive a per-session id from the MCP context.

    Falls back to a stable local id for single-user stdio deployments. A remote
    multi-user deployment MUST map each MCP session to a distinct broker session.
    """
    if ctx is not None:
        for attr in ("client_id", "session_id"):
            value = getattr(ctx, attr, None)
            if value:
                return str(value)
        session = getattr(ctx, "session", None)
        if session is not None and getattr(session, "session_id", None):
            return str(session.session_id)
    return "local-stdio-session"


async def _run_tool(coro_factory: Any, ctx: Context | None) -> dict[str, Any]:
    """Execute a tool coroutine, translating typed errors to plain language."""
    try:
        result = await coro_factory()
        return result.model_dump(mode="json")
    except WxccError as exc:
        return {"error": translate_error(exc)}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tool_get_user(identifier: str, org_id: str, ctx: Context = None) -> dict[str, Any]:
    """Resolve a WxCC user by email or user id."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_user.run(client, sid, GetUserInput(identifier=identifier, org_id=org_id)),
        ctx,
    )


@mcp.tool()
async def tool_get_user_config(user_id: str, org_id: str, ctx: Context = None) -> dict[str, Any]:
    """Return a user's teams, skill profile, agent profile, and multimedia profile."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_user_config.run(
            client, sid, GetUserConfigInput(user_id=user_id, org_id=org_id)
        ),
        ctx,
    )


@mcp.tool()
async def tool_list_agents(
    org_id: str, max_results: int = 100, ctx: Context = None
) -> dict[str, Any]:
    """Return all agents (users) in a WxCC organization."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: list_agents.run(
            client, sid, ListAgentsInput(org_id=org_id, max_results=max_results)
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_agent_state_history(
    user_id: str, org_id: str, lookback_minutes: int = 120, ctx: Context = None
) -> dict[str, Any]:
    """Return an agent's recent state transitions (Reporting/Search API)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_agent_state_history.run(
            client,
            sid,
            GetAgentStateHistoryInput(
                user_id=user_id, org_id=org_id, lookback_minutes=lookback_minutes
            ),
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_agent_login_session(
    user_id: str, org_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Return an agent's current/last login session (Reporting/Search API)."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_agent_login_session.run(
            client, sid, GetAgentLoginSessionInput(user_id=user_id, org_id=org_id)
        ),
        ctx,
    )


@mcp.tool()
async def tool_get_team(team_id: str, org_id: str, ctx: Context = None) -> dict[str, Any]:
    """Return a team's name, site, members, and associated queues."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_team.run(client, sid, GetTeamInput(team_id=team_id, org_id=org_id)), ctx
    )


@mcp.tool()
async def tool_get_queue(queue_id: str, org_id: str, ctx: Context = None) -> dict[str, Any]:
    """Return a queue's name, active flag, channel type, required skills, and routing type."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_queue.run(client, sid, GetQueueInput(queue_id=queue_id, org_id=org_id)), ctx
    )


@mcp.tool()
async def tool_get_skill_profile(
    profile_id: str, org_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Return a skill profile's name and skills."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: get_skill_profile.run(
            client, sid, GetSkillProfileInput(profile_id=profile_id, org_id=org_id)
        ),
        ctx,
    )


@mcp.tool()
async def tool_validate_agent_routing(
    user_id: str, org_id: str, ctx: Context = None
) -> dict[str, Any]:
    """Run all routing readiness checks and return ranked blocking issues."""
    client = _get_client()
    sid = _session_id(ctx)
    return await _run_tool(
        lambda: validate_agent_routing.run(
            client, sid, ValidateAgentRoutingInput(user_id=user_id, org_id=org_id)
        ),
        ctx,
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource(agent_state_reference.RESOURCE_URI)
def resource_agent_states() -> str:
    """WxCC agent states and whether each blocks going Available."""
    return json.dumps(agent_state_reference.as_dict(), indent=2)


@mcp.resource(error_code_catalog.RESOURCE_URI)
def resource_error_codes() -> str:
    """WxCC error/reason codes with likely cause and remediation."""
    return json.dumps(error_code_catalog.as_dict(), indent=2)


@mcp.resource(config_dependency_map.RESOURCE_URI)
def resource_config_dependency_map() -> str:
    """Configuration dependency map for agent availability."""
    return json.dumps(config_dependency_map.as_dict(), indent=2)


@mcp.resource(troubleshooting_runbook.RESOURCE_URI)
def resource_troubleshooting_runbook() -> str:
    """Ordered decision tree for diagnosing agent availability."""
    return json.dumps(troubleshooting_runbook.as_dict(), indent=2)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


@mcp.prompt(name=diag_prompt.PROMPT_NAME, description=diag_prompt.PROMPT_DESCRIPTION)
def prompt_diagnose(agent_identifier: str, org_id: str) -> str:
    """Render the read-only diagnostic prompt."""
    return diag_prompt.build_prompt(agent_identifier=agent_identifier, org_id=org_id)


def main() -> None:
    """Configure logging and run the MCP server over stdio."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("wxcc_mcp_server_starting", transport="stdio")
    mcp.run()


if __name__ == "__main__":
    main()
