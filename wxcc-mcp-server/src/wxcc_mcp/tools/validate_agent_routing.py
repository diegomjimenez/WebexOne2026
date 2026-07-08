"""Tool: validate_agent_routing (composite).

Orchestrates the atomic read tools to answer "why can't this agent go
Available?" It gathers data (I/O phase) and then evaluates a fixed set of checks
(pure phase) so the ranking/evidence logic is unit-testable without network I/O.

Checks:
  * user_active_and_licensed
  * session_active
  * no_blocking_state
  * team_assigned
  * team_mapped_to_active_queue
  * skills_match_queue_requirements
  * channel_enabled_in_multimedia_profile

Blocking issues (from failing checks) are ranked by likelihood following the
troubleshooting runbook order (more fundamental issues rank higher).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..api.client import WxccApiClient
from ..errors import WxccError
from ..logging_config import get_logger
from ..models.schemas import (
    BlockingIssue,
    CheckStatus,
    GetAgentLoginSessionInput,
    GetAgentLoginSessionOutput,
    GetAgentStateHistoryInput,
    GetAgentStateHistoryOutput,
    GetQueueInput,
    GetQueueOutput,
    GetTeamInput,
    GetTeamOutput,
    GetUserConfigInput,
    GetUserConfigOutput,
    GetUserInput,
    GetUserOutput,
    RoutingCheck,
    RoutingValidationResult,
    ValidateAgentRoutingInput,
)
from ..resources.agent_state_reference import is_forced_idle, state_blocks_available
from . import (
    get_agent_login_session,
    get_agent_state_history,
    get_queue,
    get_team,
    get_user,
    get_user_config,
)
from ._common import translate_error

logger = get_logger(__name__)

# Runbook order: rank 1 = most fundamental / most likely root cause.
CHECK_RANK_ORDER = [
    "user_active_and_licensed",
    "session_active",
    "no_blocking_state",
    "team_assigned",
    "team_mapped_to_active_queue",
    "skills_match_queue_requirements",
    "channel_enabled_in_multimedia_profile",
]


@dataclass
class GatheredData:
    """Raw data gathered for evaluation, with per-source error markers."""

    user_id: str
    user: GetUserOutput | None = None
    user_error: str | None = None
    config: GetUserConfigOutput | None = None
    config_error: str | None = None
    teams: list[GetTeamOutput] = field(default_factory=list)
    teams_error: str | None = None
    queues: list[GetQueueOutput] = field(default_factory=list)
    queues_error: str | None = None
    state_history: GetAgentStateHistoryOutput | None = None
    state_error: str | None = None
    session: GetAgentLoginSessionOutput | None = None
    session_error: str | None = None


async def _gather(
    client: WxccApiClient, session_id: str, inp: ValidateAgentRoutingInput
) -> GatheredData:
    """Gather all data needed for the checks, capturing errors per source."""
    data = GatheredData(user_id=inp.user_id)

    try:
        data.user = await get_user.run(
            client, session_id, GetUserInput(identifier=inp.user_id, org_id=inp.org_id)
        )
    except WxccError as exc:
        data.user_error = translate_error(exc)

    try:
        data.config = await get_user_config.run(
            client, session_id, GetUserConfigInput(user_id=inp.user_id, org_id=inp.org_id)
        )
    except WxccError as exc:
        data.config_error = translate_error(exc)

    # Teams and their queues (Config family).
    if data.config and data.config.teams:
        for team_ref in data.config.teams:
            try:
                team = await get_team.run(
                    client, session_id, GetTeamInput(team_id=team_ref.team_id, org_id=inp.org_id)
                )
                data.teams.append(team)
            except WxccError as exc:
                data.teams_error = translate_error(exc)
                continue
            for queue_ref in team.associated_queues:
                try:
                    queue = await get_queue.run(
                        client,
                        session_id,
                        GetQueueInput(queue_id=queue_ref.queue_id, org_id=inp.org_id),
                    )
                    data.queues.append(queue)
                except WxccError as exc:
                    data.queues_error = translate_error(exc)

    # Reporting/Search family.
    try:
        data.state_history = await get_agent_state_history.run(
            client,
            session_id,
            GetAgentStateHistoryInput(user_id=inp.user_id, org_id=inp.org_id),
        )
    except WxccError as exc:
        data.state_error = translate_error(exc)

    try:
        data.session = await get_agent_login_session.run(
            client,
            session_id,
            GetAgentLoginSessionInput(user_id=inp.user_id, org_id=inp.org_id),
        )
    except WxccError as exc:
        data.session_error = translate_error(exc)

    return data


def _check_user(data: GatheredData) -> RoutingCheck:
    name = "user_active_and_licensed"
    if data.user_error:
        return RoutingCheck(
            check=name, status=CheckStatus.WARNING, detail=f"Could not read user: {data.user_error}"
        )
    if data.user is None or not data.user.user_id:
        return RoutingCheck(check=name, status=CheckStatus.FAIL, detail="User could not be found.")
    if not data.user.active:
        return RoutingCheck(
            check=name, status=CheckStatus.FAIL, detail="User account is not active."
        )
    if not data.user.licenses:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="User is active but no contact-center license was detected.",
        )
    return RoutingCheck(
        check=name,
        status=CheckStatus.PASS,
        detail=f"User is active with {len(data.user.licenses)} license(s).",
    )


def _check_session(data: GatheredData) -> RoutingCheck:
    name = "session_active"
    if data.session_error:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail=f"Could not read login session: {data.session_error}",
        )
    if data.session is None:
        return RoutingCheck(
            check=name, status=CheckStatus.WARNING, detail="No session data available."
        )
    if data.session.session_active:
        return RoutingCheck(
            check=name, status=CheckStatus.PASS, detail="Agent has an active login session."
        )
    return RoutingCheck(
        check=name, status=CheckStatus.FAIL, detail="Agent is not logged in (no active session)."
    )


def _check_no_blocking_state(data: GatheredData) -> RoutingCheck:
    name = "no_blocking_state"
    if data.state_error:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail=f"Could not read state history: {data.state_error}",
        )
    if data.state_history is None or data.state_history.current_state is None:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="Current agent state is unknown; treat as uncertain.",
        )
    current = data.state_history.current_state
    last_reason = (
        data.state_history.transitions[-1].reason_code if data.state_history.transitions else None
    )
    if state_blocks_available(current) or is_forced_idle(last_reason):
        reason = f" (reason code: {last_reason})" if last_reason else ""
        return RoutingCheck(
            check=name,
            status=CheckStatus.FAIL,
            detail=f"Agent is in a blocking state '{current}'{reason}.",
        )
    return RoutingCheck(
        check=name, status=CheckStatus.PASS, detail=f"Agent state '{current}' does not block."
    )


def _check_team_assigned(data: GatheredData) -> RoutingCheck:
    name = "team_assigned"
    if data.config_error:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail=f"Could not read user config: {data.config_error}",
        )
    if data.config is None or not data.config.teams:
        return RoutingCheck(
            check=name, status=CheckStatus.FAIL, detail="No team is assigned to the user."
        )
    return RoutingCheck(
        check=name,
        status=CheckStatus.PASS,
        detail=f"User is assigned to {len(data.config.teams)} team(s).",
    )


def _check_team_mapped_to_active_queue(data: GatheredData) -> RoutingCheck:
    name = "team_mapped_to_active_queue"
    if data.config is None or not data.config.teams:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="No team assigned; queue mapping cannot be evaluated.",
        )
    if data.teams_error or data.queues_error:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="Could not fully read team/queue mappings.",
        )
    if not data.queues:
        return RoutingCheck(
            check=name,
            status=CheckStatus.FAIL,
            detail="The user's team(s) are not mapped to any queue.",
        )
    active_queues = [q for q in data.queues if q.active]
    if not active_queues:
        return RoutingCheck(
            check=name,
            status=CheckStatus.FAIL,
            detail="The user's team(s) map only to inactive queue(s).",
        )
    return RoutingCheck(
        check=name,
        status=CheckStatus.PASS,
        detail=f"Team(s) mapped to {len(active_queues)} active queue(s).",
    )


def _user_skill_values(data: GatheredData) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if data.config and data.config.skill_profile:
        for skill in data.config.skill_profile.skills:
            result.setdefault(skill.name.lower(), set()).update(v.lower() for v in skill.values)
    return result


def _check_skills_match(data: GatheredData) -> RoutingCheck:
    name = "skills_match_queue_requirements"
    active_queues = [q for q in data.queues if q.active]
    if not active_queues:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="No active queue available to compare skills against.",
        )
    if data.config is None or data.config.skill_profile is None:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="User skill profile is unknown; cannot compare to queue requirements.",
        )
    user_skills = _user_skill_values(data)
    missing: list[str] = []
    for queue in active_queues:
        for req in queue.required_skills:
            key = req.name.lower()
            if key not in user_skills:
                missing.append(f"{queue.queue_name or queue.queue_id}:{req.name}")
                continue
            if req.values:
                if not (set(v.lower() for v in req.values) & user_skills[key]):
                    missing.append(f"{queue.queue_name or queue.queue_id}:{req.name}")
    if not any(q.required_skills for q in active_queues):
        return RoutingCheck(
            check=name,
            status=CheckStatus.PASS,
            detail="Active queue(s) require no skills.",
        )
    if missing:
        return RoutingCheck(
            check=name,
            status=CheckStatus.FAIL,
            detail=f"User is missing required skill(s): {', '.join(sorted(set(missing)))}.",
        )
    return RoutingCheck(
        check=name,
        status=CheckStatus.PASS,
        detail="User skills satisfy the active queue requirements.",
    )


def _check_channel_enabled(data: GatheredData) -> RoutingCheck:
    name = "channel_enabled_in_multimedia_profile"
    active_queues = [q for q in data.queues if q.active]
    if not active_queues:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="No active queue available to compare channels against.",
        )
    if data.config is None or data.config.multimedia_profile is None:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="Multimedia profile is unknown; cannot verify channel enablement.",
        )
    enabled = {c.lower() for c in data.config.multimedia_profile.channels_enabled}
    required_channels = {q.channel_type.lower() for q in active_queues if q.channel_type}
    if not required_channels:
        return RoutingCheck(
            check=name,
            status=CheckStatus.WARNING,
            detail="Active queue channel type is unknown.",
        )
    if required_channels & enabled:
        return RoutingCheck(
            check=name,
            status=CheckStatus.PASS,
            detail="Required queue channel(s) are enabled in the multimedia profile.",
        )
    return RoutingCheck(
        check=name,
        status=CheckStatus.FAIL,
        detail=(
            "None of the active queue channel(s) "
            f"({', '.join(sorted(required_channels))}) are enabled in the multimedia profile "
            f"({', '.join(sorted(enabled)) or 'none'})."
        ),
    )


_REMEDIATION = {
    "user_active_and_licensed": "Activate the user and assign a contact-center license "
    "(WRITE action — not performed by this read-only tool).",
    "session_active": "Have the agent sign in to the Agent Desktop.",
    "no_blocking_state": "Have the agent manually return to Available (e.g. clear RONA/Idle).",
    "team_assigned": "Assign the user to a team (WRITE action — not performed).",
    "team_mapped_to_active_queue": "Map the team to an active queue (WRITE action — not "
    "performed).",
    "skills_match_queue_requirements": "Update the user's skill profile to meet queue "
    "requirements (WRITE action — not performed).",
    "channel_enabled_in_multimedia_profile": "Enable the required channel in the user's "
    "multimedia profile (WRITE action — not performed).",
}


def evaluate(data: GatheredData) -> RoutingValidationResult:
    """Evaluate all checks against gathered data (pure function)."""
    checks = [
        _check_user(data),
        _check_session(data),
        _check_no_blocking_state(data),
        _check_team_assigned(data),
        _check_team_mapped_to_active_queue(data),
        _check_skills_match(data),
        _check_channel_enabled(data),
    ]

    failing = [c for c in checks if c.status == CheckStatus.FAIL]
    failing.sort(key=lambda c: CHECK_RANK_ORDER.index(c.check))

    blocking_issues = [
        BlockingIssue(
            check=c.check,
            rank=idx + 1,
            summary=c.detail,
            evidence=c.detail,
            remediation=_REMEDIATION.get(c.check),
        )
        for idx, c in enumerate(failing)
    ]

    return RoutingValidationResult(
        user_id=data.user_id,
        routing_valid=len(failing) == 0,
        checks=checks,
        blocking_issues=blocking_issues,
    )


async def run(
    client: WxccApiClient, session_id: str, inp: ValidateAgentRoutingInput
) -> RoutingValidationResult:
    """Execute the validate_agent_routing composite tool."""
    logger.info("tool_invoked", tool="validate_agent_routing", org_id=inp.org_id)
    data = await _gather(client, session_id, inp)
    return evaluate(data)
