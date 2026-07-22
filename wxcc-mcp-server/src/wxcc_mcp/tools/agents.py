"""Tools: agent (user) reads + the profile↔agent mapping (all read-only).

These reads let an operator see which desktop profile is assigned to which
agent, so the impact of assigning an address book to a profile is clear.
Response field names are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import agents as api
from ..api import desktop_profiles as profiles_api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    AgentSummary,
    GetAgentInput,
    ListAgentsInput,
    ListAgentsOutput,
    ProfileAgentMapInput,
    ProfileAgentMapOutput,
    ProfileAgentMapping,
)
from ._helpers import extract_items

logger = get_logger(__name__)


def _map_agent(raw: dict[str, Any]) -> AgentSummary:
    """Map a raw user record to an :class:`AgentSummary`. VERIFY field names."""
    return AgentSummary(
        user_id=str(raw.get("id") or raw.get("userId") or ""),  # VERIFY
        email=raw.get("email"),  # VERIFY
        display_name=raw.get("displayName") or raw.get("name"),  # VERIFY
        # The agent→desktop-profile link field name is a VERIFY item.
        desktop_profile_id=raw.get("agentProfileId") or raw.get("desktopProfileId"),  # VERIFY
    )


def _map_profile(raw: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Return (profile_id, name, address_book_id) from a raw profile record. VERIFY."""
    return (
        str(raw.get("id") or raw.get("profileId") or ""),  # VERIFY
        raw.get("name"),  # VERIFY
        raw.get("addressBookId"),  # VERIFY
    )


async def run_list(
    client: WxccApiClient, session_id: str, inp: ListAgentsInput
) -> ListAgentsOutput:
    """List agents (users) in an organization."""
    logger.info("tool_invoked", tool="list_agents", org_id=inp.org_id)
    raw = await api.list_agents(client, session_id, inp.org_id, max_results=inp.max_results)
    agents = [_map_agent(item) for item in extract_items(raw)]
    return ListAgentsOutput(org_id=inp.org_id, total_returned=len(agents), agents=agents)


async def run_get(client: WxccApiClient, session_id: str, inp: GetAgentInput) -> AgentSummary:
    """Get a single agent (user) by id."""
    logger.info("tool_invoked", tool="get_agent", identifier=inp.identifier)
    raw = await api.get_agent(client, session_id, inp.org_id, inp.identifier)
    record = raw if isinstance(raw, dict) else {}
    return _map_agent(record)


async def run_map_profiles_to_agents(
    client: WxccApiClient, session_id: str, inp: ProfileAgentMapInput
) -> ProfileAgentMapOutput:
    """Build a mapping of desktop profile -> assigned agents (derived from reads)."""
    logger.info("tool_invoked", tool="map_profiles_to_agents", org_id=inp.org_id)
    raw_profiles = await profiles_api.list_desktop_profiles(
        client, session_id, inp.org_id, max_results=inp.max_results
    )
    raw_agents = await api.list_agents(client, session_id, inp.org_id, max_results=inp.max_results)
    agents = [_map_agent(item) for item in extract_items(raw_agents)]

    mappings: list[ProfileAgentMapping] = []
    assigned_ids: set[str] = set()
    for raw in extract_items(raw_profiles):
        pid, name, ab_id = _map_profile(raw)
        members = [a for a in agents if a.desktop_profile_id == pid]
        for a in members:
            assigned_ids.add(a.user_id)
        mappings.append(
            ProfileAgentMapping(
                profile_id=pid, profile_name=name, address_book_id=ab_id, agents=members
            )
        )
    unassigned = [a for a in agents if a.user_id not in assigned_ids]
    return ProfileAgentMapOutput(org_id=inp.org_id, mappings=mappings, unassigned_agents=unassigned)
