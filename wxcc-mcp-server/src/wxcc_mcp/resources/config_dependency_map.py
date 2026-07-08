"""Resource: config_dependency_map.

Documents the configuration relationships that determine whether an agent can go
Available, and encodes the rule that Available requires team mapping, skill
match, and channel enablement to all align.
"""

from __future__ import annotations

from typing import Any

RESOURCE_URI = "wxcc://reference/config-dependency-map"

RELATIONSHIPS: list[dict[str, str]] = [
    {
        "from": "user",
        "to": "team(s)",
        "note": "A user is assigned to one or more teams.",
    },
    {
        "from": "team",
        "to": "queue(s)",
        "note": "Teams are mapped to Contact Service Queues; the queue must be active.",
    },
    {
        "from": "queue",
        "to": "required skills",
        "note": "A queue may require specific skills/values for routing.",
    },
    {
        "from": "user",
        "to": "skill profile -> skills",
        "note": "A user's skill profile provides the skills used to match queue requirements.",
    },
    {
        "from": "user",
        "to": "multimedia profile -> channels",
        "note": "A user's multimedia profile enables channels (telephony, chat, email, ...).",
    },
]

# The core rule the diagnostic reasons about.
AVAILABILITY_RULE = (
    "To go Available for routed work, ALL of the following must align: "
    "(1) the user's team is mapped to an active queue, "
    "(2) the user's skills satisfy that queue's required skills, and "
    "(3) the queue's channel is enabled in the user's multimedia profile. "
    "Additionally the user must be active/licensed, logged in, and not stuck in a "
    "blocking state (e.g. RONA/forced idle)."
)


def as_dict() -> dict[str, Any]:
    """Return the dependency map as a serializable dict (for the MCP resource)."""
    return {
        "description": "Configuration dependency map for WxCC agent availability.",
        "relationships": RELATIONSHIPS,
        "availability_rule": AVAILABILITY_RULE,
    }
