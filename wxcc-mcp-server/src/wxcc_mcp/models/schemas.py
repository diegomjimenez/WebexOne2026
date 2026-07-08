"""Pydantic models for every tool's inputs and outputs.

These models are the typed contract between the MCP tools and the model. They
double as JSON schema sources for MCP and as fixtures for tests. No model here
carries token material — tokens never appear in tool inputs or outputs.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared / common models
# ---------------------------------------------------------------------------


class OrgScopedInput(BaseModel):
    """Base for inputs that operate within an organization."""

    org_id: str = Field(..., description="Webex Contact Center organization id.")


class License(BaseModel):
    """A license assigned to a user."""

    id: str = Field(..., description="License id.")
    name: str | None = Field(default=None, description="Human-readable license name.")


class Skill(BaseModel):
    """A single skill within a skill profile."""

    name: str = Field(..., description="Skill name.")
    type: str = Field(..., description="Skill type, e.g. text, boolean, proficiency, enum.")
    values: list[str] = Field(
        default_factory=list, description="Configured value(s) for the skill."
    )


class SkillProfileSummary(BaseModel):
    """A user's skill profile as seen from their config."""

    profile_id: str | None = Field(default=None, description="Skill profile id.")
    profile_name: str | None = Field(default=None, description="Skill profile name.")
    skills: list[Skill] = Field(default_factory=list, description="Skills in the profile.")


class MultimediaProfile(BaseModel):
    """A user's multimedia profile."""

    profile_id: str | None = Field(default=None, description="Multimedia profile id.")
    profile_name: str | None = Field(default=None, description="Multimedia profile name.")
    channels_enabled: list[str] = Field(
        default_factory=list,
        description="Channels enabled for the user, e.g. telephony, chat, email.",
    )


class TeamRef(BaseModel):
    """A lightweight reference to a team."""

    team_id: str = Field(..., description="Team id.")
    team_name: str | None = Field(default=None, description="Team name.")


class QueueRef(BaseModel):
    """A lightweight reference to a queue."""

    queue_id: str = Field(..., description="Queue id.")
    queue_name: str | None = Field(default=None, description="Queue name.")


# ---------------------------------------------------------------------------
# 1. get_user
# ---------------------------------------------------------------------------


class GetUserInput(OrgScopedInput):
    """Input for ``get_user``."""

    identifier: str = Field(..., description="User email address or user id.")


class GetUserOutput(BaseModel):
    """Output for ``get_user``."""

    user_id: str
    email: str | None = None
    display_name: str | None = None
    active: bool = False
    licenses: list[License] = Field(default_factory=list)
    last_modified: datetime | None = None


# ---------------------------------------------------------------------------
# 2. get_user_config
# ---------------------------------------------------------------------------


class GetUserConfigInput(OrgScopedInput):
    """Input for ``get_user_config``."""

    user_id: str = Field(..., description="User id.")


class GetUserConfigOutput(BaseModel):
    """Output for ``get_user_config``."""

    user_id: str
    teams: list[TeamRef] = Field(default_factory=list)
    skill_profile: SkillProfileSummary | None = None
    agent_profile: str | None = Field(
        default=None, description="Agent profile name or id assigned to the user."
    )
    multimedia_profile: MultimediaProfile | None = None


# ---------------------------------------------------------------------------
# 3. get_agent_state_history
# ---------------------------------------------------------------------------


class StateTransition(BaseModel):
    """A single agent state transition."""

    from_state: str | None = None
    to_state: str
    reason_code: str | None = None
    timestamp: datetime


class GetAgentStateHistoryInput(OrgScopedInput):
    """Input for ``get_agent_state_history``."""

    user_id: str = Field(..., description="User id.")
    lookback_minutes: int = Field(
        default=120, ge=1, description="How far back to search state history, in minutes."
    )


class GetAgentStateHistoryOutput(BaseModel):
    """Output for ``get_agent_state_history``."""

    user_id: str
    current_state: str | None = None
    current_state_since: datetime | None = None
    transitions: list[StateTransition] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. get_agent_login_session
# ---------------------------------------------------------------------------


class GetAgentLoginSessionInput(OrgScopedInput):
    """Input for ``get_agent_login_session``."""

    user_id: str = Field(..., description="User id.")


class GetAgentLoginSessionOutput(BaseModel):
    """Output for ``get_agent_login_session``."""

    user_id: str
    session_active: bool = False
    last_login: datetime | None = None
    device_type: str | None = Field(
        default=None, description="Device/agent type, e.g. desktop, browser, extension."
    )
    channels: list[str] = Field(
        default_factory=list, description="Channels the session is logged into."
    )


# ---------------------------------------------------------------------------
# 5. get_team
# ---------------------------------------------------------------------------


class GetTeamInput(OrgScopedInput):
    """Input for ``get_team``."""

    team_id: str = Field(..., description="Team id.")


class TeamMember(BaseModel):
    """A member of a team."""

    user_id: str
    display_name: str | None = None


class GetTeamOutput(BaseModel):
    """Output for ``get_team``."""

    team_id: str
    team_name: str | None = None
    site: str | None = None
    members: list[TeamMember] = Field(default_factory=list)
    associated_queues: list[QueueRef] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. get_queue
# ---------------------------------------------------------------------------


class GetQueueInput(OrgScopedInput):
    """Input for ``get_queue``."""

    queue_id: str = Field(..., description="Queue (Contact Service Queue) id.")


class GetQueueOutput(BaseModel):
    """Output for ``get_queue``."""

    queue_id: str
    queue_name: str | None = None
    active: bool = False
    channel_type: str | None = None
    required_skills: list[Skill] = Field(default_factory=list)
    routing_type: str | None = None


# ---------------------------------------------------------------------------
# 7. get_skill_profile
# ---------------------------------------------------------------------------


class GetSkillProfileInput(OrgScopedInput):
    """Input for ``get_skill_profile``."""

    profile_id: str = Field(..., description="Skill profile id.")


class GetSkillProfileOutput(BaseModel):
    """Output for ``get_skill_profile``."""

    profile_id: str
    profile_name: str | None = None
    skills: list[Skill] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 8. list_agents
# ---------------------------------------------------------------------------


class ListAgentsInput(OrgScopedInput):
    """Input for ``list_agents``."""

    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of users to return (1–1000).",
    )


class AgentSummary(BaseModel):
    """A brief summary of one agent/user."""

    user_id: str
    email: str | None = None
    display_name: str | None = None
    active: bool = False


class ListAgentsOutput(BaseModel):
    """Output for ``list_agents``."""

    org_id: str
    total_returned: int
    agents: list[AgentSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 9. validate_agent_routing (composite)
# ---------------------------------------------------------------------------


class CheckStatus(StrEnum):
    """Outcome of an individual routing check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class RoutingCheck(BaseModel):
    """The result of a single routing readiness check."""

    check: str = Field(..., description="Stable identifier of the check.")
    status: CheckStatus
    detail: str = Field(..., description="Human-readable explanation and evidence.")


class BlockingIssue(BaseModel):
    """A ranked blocking issue with supporting evidence."""

    check: str = Field(..., description="Identifier of the failing check.")
    rank: int = Field(..., ge=1, description="1 = most likely blocking cause.")
    summary: str = Field(..., description="Plain-language description of the issue.")
    evidence: str = Field(..., description="Evidence gathered from the read tools.")
    remediation: str | None = Field(
        default=None,
        description="Recommended fix. Flag if it would require a write action (not performed).",
    )


class ValidateAgentRoutingInput(OrgScopedInput):
    """Input for ``validate_agent_routing``."""

    user_id: str = Field(..., description="User id to validate for routing readiness.")


class RoutingValidationResult(BaseModel):
    """Output for ``validate_agent_routing``."""

    user_id: str
    routing_valid: bool
    checks: list[RoutingCheck] = Field(default_factory=list)
    blocking_issues: list[BlockingIssue] = Field(default_factory=list)
