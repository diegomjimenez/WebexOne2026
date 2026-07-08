"""Tool: get_agent_login_session.

Return an agent's current/last login session from the Reporting/Search API.
Field names in the mapping are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import state
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import GetAgentLoginSessionInput, GetAgentLoginSessionOutput
from ._common import parse_dt

logger = get_logger(__name__)


def _first_session(raw: dict[str, Any]) -> dict[str, Any]:
    items = raw.get("items") or raw.get("data") or raw.get("sessions")  # VERIFY
    if isinstance(items, list) and items:
        first = items[0]
        return first if isinstance(first, dict) else {}
    return raw


def _map_session(user_id: str, raw: dict[str, Any]) -> GetAgentLoginSessionOutput:
    record = _first_session(raw)
    channels = record.get("channels") or record.get("mediaChannels") or []  # VERIFY
    active = record.get("active")
    if active is None:
        # Infer from presence of a logout time. VERIFY exact fields.
        active = bool(record) and not record.get("logoutTimestamp")
    return GetAgentLoginSessionOutput(
        user_id=user_id,
        session_active=bool(active),  # VERIFY
        last_login=parse_dt(record.get("loginTimestamp") or record.get("lastLogin")),  # VERIFY
        device_type=record.get("deviceType") or record.get("channel"),  # VERIFY
        channels=[str(c) for c in channels],
    )


async def run(
    client: WxccApiClient, session_id: str, inp: GetAgentLoginSessionInput
) -> GetAgentLoginSessionOutput:
    """Execute the get_agent_login_session tool."""
    logger.info("tool_invoked", tool="get_agent_login_session", org_id=inp.org_id)
    raw = await state.search_agent_session(client, session_id, inp.org_id, inp.user_id)
    return _map_session(inp.user_id, raw)
