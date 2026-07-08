"""Resource: troubleshooting_runbook.

The ordered decision tree for diagnosing why an agent cannot go Available. The
``validate_agent_routing`` tool follows this order, and the diagnostic prompt
cross-references it.
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "wxcc://reference/troubleshooting-runbook"

# Ordered steps. Each: {step, check, if_fail} — evaluate top to bottom.
RUNBOOK_STEPS: list[dict[str, str]] = [
    {
        "step": "1",
        "check": "user_active_and_licensed",
        "question": "Is the user active and licensed for contact center?",
        "if_fail": "Stop: activate/license the user (write action).",
    },
    {
        "step": "2",
        "check": "session_active",
        "question": "Is the agent logged in (active session)?",
        "if_fail": "Stop: have the agent sign in to the Agent Desktop.",
    },
    {
        "step": "3",
        "check": "no_blocking_state",
        "question": "Is the agent free of blocking states (RONA / forced idle)?",
        "if_fail": "Stop: have the agent return to Available.",
    },
    {
        "step": "4",
        "check": "team_assigned",
        "question": "Is the user assigned to a team?",
        "if_fail": "Stop: assign the user to a team (write action).",
    },
    {
        "step": "5",
        "check": "team_mapped_to_active_queue",
        "question": "Is the team mapped to an active queue?",
        "if_fail": "Stop: map the team to an active queue (write action).",
    },
    {
        "step": "6",
        "check": "skills_match_queue_requirements",
        "question": "Do the agent's skills match the queue's required skills?",
        "if_fail": "Stop: update the agent's skill profile (write action).",
    },
    {
        "step": "7",
        "check": "channel_enabled_in_multimedia_profile",
        "question": "Is the queue's channel enabled in the agent's multimedia profile?",
        "if_fail": "Stop: enable the channel in the multimedia profile (write action).",
    },
    {
        "step": "8",
        "check": "escalate",
        "question": "All checks pass but the agent still cannot go Available?",
        "if_fail": "Escalate to WxCC support with the collected evidence.",
    },
]


def as_dict() -> dict[str, Any]:
    """Return the runbook as a serializable dict (for the MCP resource)."""
    return {
        "description": "Ordered decision tree for diagnosing agent availability.",
        "steps": RUNBOOK_STEPS,
    }
