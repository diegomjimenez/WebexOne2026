"""Tool: get_skill_profile.

Return a skill profile's name and skills. Field names in the mapping are marked
``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import skills as skills_api
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import GetSkillProfileInput, GetSkillProfileOutput, Skill

logger = get_logger(__name__)


def _map_skills(raw_skills: Any) -> list[Skill]:
    result: list[Skill] = []
    for item in raw_skills or []:
        if not isinstance(item, dict):
            continue
        values = item.get("values")
        if isinstance(values, str):
            values = [values]
        elif not isinstance(values, list):
            values = [str(values)] if values is not None else []
        result.append(
            Skill(
                name=str(item.get("name", "")),  # VERIFY
                type=str(item.get("type", "unknown")),  # VERIFY
                values=[str(v) for v in values],
            )
        )
    return result


def _map_profile(profile_id: str, raw: dict[str, Any]) -> GetSkillProfileOutput:
    return GetSkillProfileOutput(
        profile_id=profile_id,
        profile_name=raw.get("name"),  # VERIFY
        skills=_map_skills(raw.get("skills")),  # VERIFY
    )


async def run(
    client: WxccApiClient, session_id: str, inp: GetSkillProfileInput
) -> GetSkillProfileOutput:
    """Execute the get_skill_profile tool."""
    logger.info("tool_invoked", tool="get_skill_profile", org_id=inp.org_id)
    raw = await skills_api.get_skill_profile_by_id(client, session_id, inp.org_id, inp.profile_id)
    return _map_profile(inp.profile_id, raw)
