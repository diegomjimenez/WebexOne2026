"""Tests for the seven atomic read-only tools using mocked API responses."""

from __future__ import annotations

import pytest

from wxcc_mcp.errors import InsufficientPermissionsError, NotFoundError
from wxcc_mcp.models.schemas import (
    GetAgentLoginSessionInput,
    GetAgentStateHistoryInput,
    GetQueueInput,
    GetSkillProfileInput,
    GetTeamInput,
    GetUserConfigInput,
    GetUserInput,
)
from wxcc_mcp.tools import (
    get_agent_login_session,
    get_agent_state_history,
    get_queue,
    get_skill_profile,
    get_team,
    get_user,
    get_user_config,
)
from wxcc_mcp.tools._common import translate_error

ORG = "org1"


async def test_get_user_by_email(client):
    out = await get_user.run(client, "s1", GetUserInput(identifier="agent@example.com", org_id=ORG))
    assert out.user_id == "u1"
    assert out.email == "agent@example.com"
    assert out.active is True
    assert out.licenses and out.licenses[0].name == "CC Premium"


async def test_get_user_by_id(client):
    out = await get_user.run(client, "s1", GetUserInput(identifier="u1", org_id=ORG))
    assert out.user_id == "u1"
    assert out.display_name == "Agent One"


async def test_get_user_not_found(client_factory):
    client = client_factory(errors={"user": 404})
    with pytest.raises(NotFoundError):
        await get_user.run(client, "s1", GetUserInput(identifier="u1", org_id=ORG))


async def test_get_user_permission_denied_plain_language(client_factory):
    client = client_factory(errors={"user": 403})
    with pytest.raises(InsufficientPermissionsError) as excinfo:
        await get_user.run(client, "s1", GetUserInput(identifier="u1", org_id=ORG))
    message = translate_error(excinfo.value)
    assert "permission" in message.lower()
    # The plain-language message must not leak any token material.
    assert "fake-access-token" not in message


async def test_get_user_config(client):
    out = await get_user_config.run(client, "s1", GetUserConfigInput(user_id="u1", org_id=ORG))
    assert [t.team_id for t in out.teams] == ["t1"]
    assert out.skill_profile and out.skill_profile.skills[0].name == "English"
    assert out.multimedia_profile and out.multimedia_profile.channels_enabled == ["telephony"]
    assert out.agent_profile == "Default Agent Profile"


async def test_get_agent_state_history(client):
    out = await get_agent_state_history.run(
        client, "s1", GetAgentStateHistoryInput(user_id="u1", org_id=ORG)
    )
    assert out.current_state == "Available"
    assert len(out.transitions) == 1
    assert out.transitions[0].to_state == "Available"


async def test_get_agent_login_session(client):
    out = await get_agent_login_session.run(
        client, "s1", GetAgentLoginSessionInput(user_id="u1", org_id=ORG)
    )
    assert out.session_active is True
    assert out.device_type == "desktop"
    assert out.channels == ["telephony"]


async def test_get_team(client):
    out = await get_team.run(client, "s1", GetTeamInput(team_id="t1", org_id=ORG))
    assert out.team_name == "Team Alpha"
    assert out.site == "Site 1"
    assert [q.queue_id for q in out.associated_queues] == ["q1"]


async def test_get_queue(client):
    out = await get_queue.run(client, "s1", GetQueueInput(queue_id="q1", org_id=ORG))
    assert out.queue_name == "Sales Queue"
    assert out.active is True
    assert out.channel_type == "telephony"
    assert out.required_skills[0].name == "English"


async def test_get_skill_profile(client):
    out = await get_skill_profile.run(
        client, "s1", GetSkillProfileInput(profile_id="sp1", org_id=ORG)
    )
    assert out.profile_name == "Sales"
    assert out.skills[0].name == "English"


async def test_tool_output_contains_no_token(client):
    """A tool's serialized output must never contain token material."""
    out = await get_user.run(client, "s1", GetUserInput(identifier="u1", org_id=ORG))
    dumped = out.model_dump_json()
    assert "fake-access-token" not in dumped
    assert "Authorization" not in dumped
