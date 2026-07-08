"""Tool: get_agent_state_history.

Return an agent's recent state transitions from the Reporting/Search API.
Field names in the mapping are marked ``# VERIFY``.
"""

from __future__ import annotations

from typing import Any

from ..api import state
from ..api.client import WxccApiClient
from ..logging_config import get_logger
from ..models.schemas import (
    GetAgentStateHistoryInput,
    GetAgentStateHistoryOutput,
    StateTransition,
)
from ._common import parse_dt

logger = get_logger(__name__)


def _map_transitions(raw: dict[str, Any]) -> list[StateTransition]:
    items = raw.get("items") or raw.get("data") or raw.get("transitions") or []  # VERIFY
    transitions: list[StateTransition] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ts = parse_dt(item.get("timestamp") or item.get("time") or item.get("startTime"))
        if ts is None:
            continue
        transitions.append(
            StateTransition(
                from_state=item.get("fromState") or item.get("previousState"),  # VERIFY
                to_state=str(item.get("toState") or item.get("state") or "unknown"),  # VERIFY
                reason_code=item.get("reasonCode") or item.get("reason"),  # VERIFY
                timestamp=ts,
            )
        )
    transitions.sort(key=lambda t: t.timestamp)
    return transitions


async def run(
    client: WxccApiClient, session_id: str, inp: GetAgentStateHistoryInput
) -> GetAgentStateHistoryOutput:
    """Execute the get_agent_state_history tool."""
    logger.info(
        "tool_invoked",
        tool="get_agent_state_history",
        org_id=inp.org_id,
        lookback_minutes=inp.lookback_minutes,
    )
    raw = await state.search_agent_state_history(
        client, session_id, inp.org_id, inp.user_id, inp.lookback_minutes
    )
    transitions = _map_transitions(raw)
    current = transitions[-1] if transitions else None
    return GetAgentStateHistoryOutput(
        user_id=inp.user_id,
        current_state=current.to_state if current else raw.get("currentState"),  # VERIFY
        current_state_since=current.timestamp if current else None,
        transitions=transitions,
    )
