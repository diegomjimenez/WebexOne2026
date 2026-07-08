"""Tool: list_agents.

Return all users (agents) in a WxCC organization up to ``max_results``.

The response envelope shape is marked ``# VERIFY`` — confirm the exact field
names against developer.webex.com before going live.
"""

from __future__ import annotations

from typing import Any, Union

from ..api import users
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import AgentSummary, ListAgentsInput, ListAgentsOutput

logger = get_logger(__name__)


def _extract_items(raw: Any) -> list[dict[str, Any]]:
    """Pull the list of user records from the API response.

    The WxCC Config API returns a bare JSON array for this endpoint.
    Fallback envelope keys are kept for forward-compatibility.
    """
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("items", "data", "users", "members"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _map_summary(raw: dict[str, Any]) -> AgentSummary:
    """Map a raw user record to an :class:`AgentSummary`. VERIFY field names."""
    return AgentSummary(
        user_id=str(raw.get("id") or raw.get("userId") or ""),  # VERIFY
        email=raw.get("email"),  # VERIFY
        display_name=raw.get("displayName") or raw.get("name"),  # VERIFY
        active=bool(raw.get("active", raw.get("isActive", False))),  # VERIFY
    )


async def run(
    client: WxccApiClient, session_id: str, inp: ListAgentsInput
) -> ListAgentsOutput:
    """Execute the list_agents tool.

    Args:
        client: The WxCC API client.
        session_id: MCP session id for token resolution.
        inp: Validated tool input.

    Returns:
        A :class:`ListAgentsOutput` with all returned agents.
    """
    logger.info("tool_invoked", tool="list_agents", org_id=inp.org_id)
    raw = await users.list_users(
        client, session_id, inp.org_id, max_results=inp.max_results
    )
    items = _extract_items(raw)
    agents = [_map_summary(item) for item in items]
    return ListAgentsOutput(
        org_id=inp.org_id,
        total_returned=len(agents),
        agents=agents,
    )
