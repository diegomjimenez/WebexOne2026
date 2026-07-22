"""WxCC User (agent) API endpoints (Config family, read-only).

Read-only discovery of agents and the desktop profile assigned to each. Used to
build the profile↔agent mapping so an operator can see the impact of assigning
an address book to a profile. Path constants live in ``config.py`` and are
marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def list_agents(
    client: WxccApiClient, session_id: str, org_id: str, *, max_results: int = 100
) -> Any:
    """List users (agents) in an organization."""
    path = config.USERS_PATH.format(org_id=org_id)
    params: dict[str, Any] = {"pageSize": min(max_results, 100)}  # VERIFY param name
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)


async def get_agent(client: WxccApiClient, session_id: str, org_id: str, user_id: str) -> Any:
    """Fetch a single user (agent) by id."""
    path = config.USER_BY_ID_PATH.format(org_id=org_id, user_id=user_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)
