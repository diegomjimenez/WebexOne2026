"""Tool: get_user_config.

Return a user's teams, skill profile, agent profile, and multimedia profile.
Field names in the mapping are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import users
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    GetUserConfigInput,
    GetUserConfigOutput,
    MultimediaProfile,
    Skill,
    SkillProfileSummary,
    TeamRef,
)

logger = get_logger(__name__)


def _map_skills(raw_skills: Any) -> list[Skill]:
    skills: list[Skill] = []
    for item in raw_skills or []:
        if not isinstance(item, dict):
            continue
        values = item.get("values")
        if isinstance(values, str):
            values = [values]
        elif not isinstance(values, list):
            values = [str(values)] if values is not None else []
        skills.append(
            Skill(
                name=str(item.get("name", "")),  # VERIFY
                type=str(item.get("type", "unknown")),  # VERIFY
                values=[str(v) for v in values],  # VERIFY
            )
        )
    return skills


def _map_config(user_id: str, raw: dict[str, Any]) -> GetUserConfigOutput:
    """Map a raw user config record. VERIFY field names/shape."""
    teams = [
        TeamRef(team_id=str(t.get("id", "")), team_name=t.get("name"))  # VERIFY
        for t in (raw.get("teams") or [])
        if isinstance(t, dict)
    ]

    sp_raw = raw.get("skillProfile") or {}  # VERIFY
    skill_profile = None
    if isinstance(sp_raw, dict) and sp_raw:
        skill_profile = SkillProfileSummary(
            profile_id=sp_raw.get("id"),  # VERIFY
            profile_name=sp_raw.get("name"),  # VERIFY
            skills=_map_skills(sp_raw.get("skills")),  # VERIFY
        )

    mm_raw = raw.get("multimediaProfile") or {}  # VERIFY
    multimedia_profile = None
    if isinstance(mm_raw, dict) and mm_raw:
        channels = mm_raw.get("channelsEnabled") or mm_raw.get("channels") or []  # VERIFY
        multimedia_profile = MultimediaProfile(
            profile_id=mm_raw.get("id"),
            profile_name=mm_raw.get("name"),
            channels_enabled=[str(c) for c in channels],
        )

    return GetUserConfigOutput(
        user_id=user_id,
        teams=teams,
        skill_profile=skill_profile,
        agent_profile=raw.get("agentProfile") or raw.get("agentProfileName"),  # VERIFY
        multimedia_profile=multimedia_profile,
    )


async def run(
    client: WxccApiClient, session_id: str, inp: GetUserConfigInput
) -> GetUserConfigOutput:
    """Execute the get_user_config tool."""
    logger.info("tool_invoked", tool="get_user_config", org_id=inp.org_id)
    raw = await users.get_user_config(client, session_id, inp.org_id, inp.user_id)
    return _map_config(inp.user_id, raw)
