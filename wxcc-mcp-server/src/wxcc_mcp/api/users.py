"""Config API: user endpoints.

Thin async wrappers returning raw JSON. Path constants live in ``config.py`` and
are marked ``# VERIFY`` — confirm them against developer.webex.com.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def find_user_by_email(
    client: WxccApiClient, session_id: str, org_id: str, email: str
) -> dict[str, Any]:
    """Search for a user by email within an organization. VERIFY endpoint."""
    path = config.USERS_PATH.format(org_id=org_id)
    params = {config.USER_BY_EMAIL_QUERY_PARAM: email}  # VERIFY param name
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)


async def get_user_by_id(
    client: WxccApiClient, session_id: str, org_id: str, user_id: str
) -> dict[str, Any]:
    """Fetch a single user by id. VERIFY endpoint."""
    path = config.USER_BY_ID_PATH.format(org_id=org_id, user_id=user_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)


async def get_user_config(
    client: WxccApiClient, session_id: str, org_id: str, user_id: str
) -> dict[str, Any]:
    """Fetch the user's full config (teams, profiles, skills). VERIFY endpoint/source."""
    path = config.USER_CONFIG_PATH.format(org_id=org_id, user_id=user_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)


async def list_users(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    *,
    max_results: int = 100,
) -> Any:
    """List users in an organization with optional result cap.

    Uses the same ``USERS_PATH`` endpoint as the email search but without a
    filter, relying on the API's default ordering. ``max_results`` is passed
    as a query parameter named ``max`` (VERIFY the exact param name against
    developer.webex.com — common alternatives: ``limit``, ``pageSize``).
    """
    path = config.USERS_PATH.format(org_id=org_id)
    params: dict[str, Any] = {"max": max_results}  # VERIFY param name
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)
