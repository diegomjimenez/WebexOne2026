"""Tool: get_queue.

Return a queue's name, active flag, channel type, required skills, and routing
type. Field names in the mapping are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import queues
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import GetQueueInput, GetQueueOutput, Skill

logger = get_logger(__name__)


def _map_required_skills(raw_skills: Any) -> list[Skill]:
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
                values=[str(v) for v in values],
            )
        )
    return skills


def _map_queue(queue_id: str, raw: dict[str, Any]) -> GetQueueOutput:
    return GetQueueOutput(
        queue_id=queue_id,
        queue_name=raw.get("name"),  # VERIFY
        active=bool(raw.get("active", raw.get("isActive", False))),  # VERIFY
        channel_type=raw.get("channelType") or raw.get("channel"),  # VERIFY
        required_skills=_map_required_skills(
            raw.get("requiredSkills") or raw.get("skillRequirements")  # VERIFY
        ),
        routing_type=raw.get("routingType") or raw.get("queueRoutingType"),  # VERIFY
    )


async def run(client: WxccApiClient, session_id: str, inp: GetQueueInput) -> GetQueueOutput:
    """Execute the get_queue tool."""
    logger.info("tool_invoked", tool="get_queue", org_id=inp.org_id)
    raw = await queues.get_queue_by_id(client, session_id, inp.org_id, inp.queue_id)
    return _map_queue(inp.queue_id, raw)
