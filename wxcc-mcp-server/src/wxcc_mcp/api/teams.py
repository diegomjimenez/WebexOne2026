"""Config API: team endpoints.

Path constants live in ``config.py`` and are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..config import ApiFamily
from .client import WxccApiClient


async def get_team_by_id(
    client: WxccApiClient, session_id: str, org_id: str, team_id: str
) -> dict[str, Any]:
    """Fetch a single team by id. VERIFY endpoint."""
    path = config.TEAM_BY_ID_PATH.format(org_id=org_id, team_id=team_id)
    return await client.get(ApiFamily.CONFIG, path, session_id)
