"""Resource: agent_state_reference.

Enumerates WxCC agent states, their meaning, and whether each blocks an agent
from going Available. This is the authoritative source for blocking-state logic
used by the ``validate_agent_routing`` composite tool.

NOTE: State names and reason codes are commonly-seen values. VERIFY the exact
set and semantics against WxCC documentation.
"""

from __future__ import annotations

from typing import Any

# Canonical resource URI exposed via MCP.
RESOURCE_URI = "wxcc://reference/agent-states"

# Each entry: state -> {meaning, blocks_available}
# blocks_available=True means an agent in this state cannot currently be routed
# work / is not Available. VERIFY against WxCC docs.
AGENT_STATES: dict[str, dict[str, Any]] = {
    "Available": {
        "meaning": "Agent is ready and eligible to receive routed contacts.",
        "blocks_available": False,
    },
    "Idle": {
        "meaning": "Agent is logged in but not available (often with a reason code).",
        "blocks_available": True,
    },
    "RONA": {
        "meaning": "Redirection On No Answer: agent did not answer an offered contact and "
        "was moved out of Available. Typically requires manual return to Available.",
        "blocks_available": True,
    },
    "NotResponding": {
        "meaning": "Agent's client is not responding to the platform.",
        "blocks_available": True,
    },
    "Connected": {
        "meaning": "Agent is actively handling a contact.",
        "blocks_available": True,
    },
    "Wrapup": {
        "meaning": "Agent is completing after-contact work.",
        "blocks_available": True,
    },
    "LoggedOut": {
        "meaning": "Agent is not logged in.",
        "blocks_available": True,
    },
}

# Reason codes that indicate a forced/system idle state (not agent-chosen).
# VERIFY the exact codes against WxCC docs.
FORCED_IDLE_REASON_CODES: set[str] = {
    "SYSTEM",
    "FORCED_LOGOUT",
    "RONA",
}


def state_blocks_available(state: str | None) -> bool:
    """Return True if the given state blocks going Available.

    Unknown states are treated conservatively as blocking so the diagnosis does
    not falsely report readiness.
    """
    if not state:
        return True
    entry = AGENT_STATES.get(state)
    if entry is None:
        return True  # unknown -> conservative
    return bool(entry["blocks_available"])


def is_forced_idle(reason_code: str | None) -> bool:
    """Return True if a reason code indicates a forced/system idle state."""
    if not reason_code:
        return False
    return reason_code.upper() in FORCED_IDLE_REASON_CODES


def as_dict() -> dict[str, Any]:
    """Return the full reference as a serializable dict (for the MCP resource)."""
    return {
        "description": "WxCC agent states and whether each blocks going Available.",
        "states": AGENT_STATES,
        "forced_idle_reason_codes": sorted(FORCED_IDLE_REASON_CODES),
        "note": "VERIFY state names and reason codes against WxCC documentation.",
    }
