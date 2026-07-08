"""Tool: get_user.

Resolve a WxCC user by email or user id. Field names in the mapping are marked
``# VERIFY`` — confirm the real response shape against developer.webex.com.
"""

from __future__ import annotations

from typing import Any

from ..api import users
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import GetUserInput, GetUserOutput, License
from ._common import parse_dt

logger = get_logger(__name__)


def _looks_like_email(identifier: str) -> bool:
    return "@" in identifier


def _map_user(raw: dict[str, Any]) -> GetUserOutput:
    """Map a raw user record to :class:`GetUserOutput`. VERIFY field names."""
    licenses = [
        License(id=str(item.get("id", "")), name=item.get("name"))
        for item in (raw.get("licenses") or [])
        if isinstance(item, dict)
    ]
    return GetUserOutput(
        user_id=str(raw.get("id") or raw.get("userId") or ""),  # VERIFY
        email=raw.get("email"),  # VERIFY
        display_name=raw.get("displayName") or raw.get("name"),  # VERIFY
        active=bool(raw.get("active", raw.get("isActive", False))),  # VERIFY
        licenses=licenses,  # VERIFY
        last_modified=parse_dt(raw.get("lastModified") or raw.get("modified")),  # VERIFY
    )


def _first_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Return the first user record from a search response. VERIFY shape."""
    items = raw.get("items") or raw.get("data") or raw.get("users")
    if isinstance(items, list) and items:
        first = items[0]
        return first if isinstance(first, dict) else {}
    return raw


async def run(client: WxccApiClient, session_id: str, inp: GetUserInput) -> GetUserOutput:
    """Execute the get_user tool.

    Args:
        client: The WxCC API client.
        session_id: MCP session id for token resolution.
        inp: Validated tool input.

    Returns:
        The resolved user.
    """
    logger.info("tool_invoked", tool="get_user", org_id=inp.org_id)
    if _looks_like_email(inp.identifier):
        raw = await users.find_user_by_email(client, session_id, inp.org_id, inp.identifier)
        record = _first_record(raw)
    else:
        record = await users.get_user_by_id(client, session_id, inp.org_id, inp.identifier)
    return _map_user(record)
