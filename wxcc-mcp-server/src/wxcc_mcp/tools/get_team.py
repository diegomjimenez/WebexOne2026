"""Tool: get_team.

Return a team's name, site, members, and associated queues.
Field names in the mapping are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import teams
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import GetTeamInput, GetTeamOutput, QueueRef, TeamMember

logger = get_logger(__name__)


def _map_team(team_id: str, raw: dict[str, Any]) -> GetTeamOutput:
    members = [
        TeamMember(user_id=str(m.get("id", "")), display_name=m.get("name"))  # VERIFY
        for m in (raw.get("members") or raw.get("users") or [])
        if isinstance(m, dict)
    ]
    queues = [
        QueueRef(queue_id=str(q.get("id", "")), queue_name=q.get("name"))  # VERIFY
        for q in (raw.get("queues") or raw.get("associatedQueues") or [])
        if isinstance(q, dict)
    ]
    return GetTeamOutput(
        team_id=team_id,
        team_name=raw.get("name"),  # VERIFY
        site=raw.get("site") or raw.get("siteName"),  # VERIFY
        members=members,
        associated_queues=queues,
    )


async def run(client: WxccApiClient, session_id: str, inp: GetTeamInput) -> GetTeamOutput:
    """Execute the get_team tool."""
    logger.info("tool_invoked", tool="get_team", org_id=inp.org_id)
    raw = await teams.get_team_by_id(client, session_id, inp.org_id, inp.team_id)
    return _map_team(inp.team_id, raw)
