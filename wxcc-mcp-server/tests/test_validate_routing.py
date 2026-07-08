"""Tests for the composite validate_agent_routing tool."""

from __future__ import annotations

import copy

from wxcc_mcp.models.schemas import CheckStatus, ValidateAgentRoutingInput
from wxcc_mcp.tools import validate_agent_routing

from .conftest import DEFAULT_DATASET

ORG = "org1"


def _status(result, check_name: str) -> CheckStatus:
    return next(c.status for c in result.checks if c.check == check_name)


async def test_all_checks_pass(client):
    result = await validate_agent_routing.run(
        client, "s1", ValidateAgentRoutingInput(user_id="u1", org_id=ORG)
    )
    assert result.routing_valid is True
    assert result.blocking_issues == []
    assert all(c.status == CheckStatus.PASS for c in result.checks)


async def test_single_blocking_cause_skill_mismatch(client_factory):
    dataset = copy.deepcopy(DEFAULT_DATASET)
    # Queue now requires Spanish, which the user does not have.
    dataset["queues"]["q1"]["requiredSkills"] = [
        {"name": "Spanish", "type": "boolean", "values": ["true"]}
    ]
    client = client_factory(dataset=dataset)

    result = await validate_agent_routing.run(
        client, "s1", ValidateAgentRoutingInput(user_id="u1", org_id=ORG)
    )
    assert result.routing_valid is False
    assert _status(result, "skills_match_queue_requirements") == CheckStatus.FAIL
    assert len(result.blocking_issues) == 1
    issue = result.blocking_issues[0]
    assert issue.check == "skills_match_queue_requirements"
    assert issue.rank == 1
    assert "Spanish" in issue.evidence
    # Remediation flags that this would be a write action.
    assert issue.remediation and "WRITE" in issue.remediation.upper()


async def test_ranking_orders_by_runbook(client_factory):
    dataset = copy.deepcopy(DEFAULT_DATASET)
    # Two failures: not logged in (session) AND skill mismatch. Session ranks higher.
    dataset["session"]["items"][0]["active"] = False
    dataset["queues"]["q1"]["requiredSkills"] = [
        {"name": "Spanish", "type": "boolean", "values": ["true"]}
    ]
    client = client_factory(dataset=dataset)

    result = await validate_agent_routing.run(
        client, "s1", ValidateAgentRoutingInput(user_id="u1", org_id=ORG)
    )
    assert result.routing_valid is False
    ranks = {issue.check: issue.rank for issue in result.blocking_issues}
    assert ranks["session_active"] < ranks["skills_match_queue_requirements"]


async def test_warning_does_not_block(client_factory):
    dataset = copy.deepcopy(DEFAULT_DATASET)
    # No license -> warning on user check, but nothing fails.
    dataset["user"]["licenses"] = []
    client = client_factory(dataset=dataset)

    result = await validate_agent_routing.run(
        client, "s1", ValidateAgentRoutingInput(user_id="u1", org_id=ORG)
    )
    assert _status(result, "user_active_and_licensed") == CheckStatus.WARNING
    assert result.routing_valid is True
    assert result.blocking_issues == []


async def test_partial_failure_reporting_403_becomes_warning(client_factory):
    # A 403 on the Reporting/Search API (state + session) must degrade to warnings,
    # not crash the whole diagnosis, and must not block routing on its own.
    client = client_factory(errors={"state": 403, "session": 403})

    result = await validate_agent_routing.run(
        client, "s1", ValidateAgentRoutingInput(user_id="u1", org_id=ORG)
    )
    assert _status(result, "no_blocking_state") == CheckStatus.WARNING
    assert _status(result, "session_active") == CheckStatus.WARNING
    # Config-side checks still pass, so nothing hard-fails.
    assert result.routing_valid is True
