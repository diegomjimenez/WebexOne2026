"""WxCC Desktop Profile API endpoints (Config family).

Read desktop profiles and assign an address book by updating the profile's
``addressBookId``. Uses the Desktop Profile API (the Agent Profile API is
superseded). The deprecated dial-plan fields (``dialPlans``,
``agentDNValidationCriteria``, ``agentDNValidationCriterions``) are never read or
written here. Path constants live in ``config.py`` and are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def list_desktop_profiles(
    client: WxccApiClient, session_id: str, org_id: str, *, max_results: int = 100
) -> Any:
    """List desktop profiles in an organization."""
    path = config.DESKTOP_PROFILES_PATH.format(org_id=org_id)
    params: dict[str, Any] = {"pageSize": min(max_results, 100)}  # VERIFY param name
    return await client.get(ApiFamily.CONFIG, path, session_id, params=params)


async def get_desktop_profile(
    client: WxccApiClient, session_id: str, org_id: str, profile_id: str
) -> Any:
    """Fetch a single desktop profile by id."""
    path = config.DESKTOP_PROFILE_BY_ID_PATH.format(org_id=org_id, profile_id=profile_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)


async def update_desktop_profile(
    client: WxccApiClient,
    session_id: str,
    org_id: str,
    profile_id: str,
    payload: dict[str, Any],
) -> Any:
    """Update a desktop profile (used to set ``addressBookId``)."""
    path = config.DESKTOP_PROFILE_BY_ID_PATH.format(org_id=org_id, profile_id=profile_id)
    return await client.put(ApiFamily.CONFIG, path, session_id, json_body=payload)
