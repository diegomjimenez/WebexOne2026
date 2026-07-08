"""Resource: error_code_catalog.

A structured catalog of WxCC error/reason codes and their remediation. The
entries below are PLACEHOLDERS.

# TODO: populate from WxCC docs (https://developer.webex.com and WxCC admin docs).
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "wxcc://reference/error-codes"

# Each entry: {code, meaning, likely_cause, remediation}
# TODO: populate from WxCC docs.
ERROR_CODES: list[dict[str, str]] = [
    {
        "code": "RONA",
        "meaning": "Redirection On No Answer.",
        "likely_cause": "Agent did not answer an offered contact within the ring timeout.",
        "remediation": "Agent must manually return to Available; review ring timeout settings.",
    },
    {
        "code": "AGENT_NOT_LOGGED_IN",  # TODO: VERIFY code string
        "meaning": "Agent has no active login session.",
        "likely_cause": "Agent has not signed in to the Agent Desktop, or session expired.",
        "remediation": "Have the agent sign in.",
    },
    {
        "code": "NO_QUEUE_MAPPING",  # TODO: VERIFY code string
        "meaning": "Agent's team is not mapped to any active queue.",
        "likely_cause": "Team-to-queue mapping missing or queue inactive.",
        "remediation": "Map the team to an active queue.",
    },
    {
        "code": "SKILL_MISMATCH",  # TODO: VERIFY code string
        "meaning": "Agent skills do not satisfy queue requirements.",
        "likely_cause": "Skill profile missing required skills/values.",
        "remediation": "Update the agent's skill profile.",
    },
    {
        "code": "CHANNEL_NOT_ENABLED",  # TODO: VERIFY code string
        "meaning": "Required channel is not enabled in the multimedia profile.",
        "likely_cause": "Multimedia profile does not include the queue's channel.",
        "remediation": "Enable the channel in the multimedia profile.",
    },
]


def as_dict() -> dict[str, Any]:
    """Return the catalog as a serializable dict (for the MCP resource)."""
    return {
        "description": "WxCC error/reason codes with likely cause and remediation.",
        "note": "PLACEHOLDER entries. TODO: populate from WxCC docs.",
        "codes": ERROR_CODES,
    }
