"""Reporting/Search API: agent state and session endpoints.

This is a DIFFERENT API family from the Config API — separate base URL and
scopes. Path constants live in ``config.py`` and are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def search_agent_state_history(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    user_id: str,
    lookback_minutes: int,
) -> dict[str, Any]:
    """Search an agent's recent state transitions. VERIFY endpoint/params."""
    path = config.AGENT_STATE_HISTORY_PATH.format(org_id=org_id)
    # VERIFY the exact query/param names for user and time window.
    params = {"agentId": user_id, "lookbackMinutes": lookback_minutes}
    return await client.get(ApiFamily.REPORTING, path, session_id, params=params)


async def search_agent_session(
    client: WxccApiClient, session_id: str, org_id: str, user_id: str
) -> dict[str, Any]:
    """Search an agent's current/last login session. VERIFY endpoint/params."""
    path = config.AGENT_SESSION_PATH.format(org_id=org_id)
    params = {"agentId": user_id}  # VERIFY param name
    return await client.get(ApiFamily.REPORTING, path, session_id, params=params)
