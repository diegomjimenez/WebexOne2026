"""Config API: skill profile / skill endpoints.

Path constants live in ``config.py`` and are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def get_skill_profile_by_id(
    client: WxccApiClient, session_id: str, org_id: str, profile_id: str
) -> dict[str, Any]:
    """Fetch a single skill profile by id. VERIFY endpoint."""
    path = config.SKILL_PROFILE_BY_ID_PATH.format(org_id=org_id, profile_id=profile_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)
