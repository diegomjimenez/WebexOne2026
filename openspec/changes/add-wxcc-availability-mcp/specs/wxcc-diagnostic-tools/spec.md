## ADDED Requirements

### Requirement: Read-only tool contract

Every diagnostic tool SHALL be registered as an MCP tool with a Pydantic input schema and a Pydantic output model, and SHALL perform read operations only. No tool in this phase SHALL create, update, or delete WxCC configuration or state.

#### Scenario: Tool exposes typed schemas

- **WHEN** an MCP client inspects a registered diagnostic tool
- **THEN** the tool advertises a Pydantic-derived input schema and returns a structured, typed output

#### Scenario: No write side effects

- **WHEN** any diagnostic tool executes successfully
- **THEN** it issues only read requests to WxCC APIs and mutates no WxCC configuration or state

### Requirement: get_user tool

`get_user` SHALL accept `identifier` (email or user_id) and `org_id`, and SHALL return `user_id`, `email`, `display_name`, `active`, `licenses[]`, and `last_modified`.

#### Scenario: Resolve user by email

- **WHEN** `get_user` is called with an email `identifier` and an `org_id`
- **THEN** it returns the matching user's id, email, display name, active flag, licenses, and last-modified timestamp

#### Scenario: Unknown user surfaces not-found

- **WHEN** `get_user` is called with an identifier that matches no user
- **THEN** it surfaces a plain-language not-found result derived from `NotFoundError`

### Requirement: get_user_config tool

`get_user_config` SHALL accept `user_id` and `org_id`, and SHALL return `teams[]`, `skill_profile{skills[]}`, `agent_profile`, and `multimedia_profile{channels_enabled[]}`.

#### Scenario: Return full user configuration

- **WHEN** `get_user_config` is called for a valid `user_id`
- **THEN** it returns the user's teams, skill profile with skills, agent profile, and multimedia profile with enabled channels

### Requirement: get_agent_state_history tool

`get_agent_state_history` SHALL accept `user_id`, `org_id`, and `lookback_minutes` (default 120), sourcing data from the Reporting/Search API, and SHALL return `current_state`, `current_state_since`, and `transitions[]` where each transition has `from_state`, `to_state`, `reason_code`, and `timestamp`.

#### Scenario: Return recent state transitions

- **WHEN** `get_agent_state_history` is called with a `user_id` and default lookback
- **THEN** it returns the current state, since-timestamp, and the ordered list of transitions within the lookback window

#### Scenario: Custom lookback window honored

- **WHEN** `get_agent_state_history` is called with `lookback_minutes` set to a custom value
- **THEN** the returned transitions are constrained to that window

### Requirement: get_agent_login_session tool

`get_agent_login_session` SHALL accept `user_id` and `org_id`, sourcing data from the Reporting/Search API, and SHALL return `session_active` (bool), `last_login`, and device/channel info.

#### Scenario: Report active login session

- **WHEN** `get_agent_login_session` is called for an agent with an active session
- **THEN** it returns `session_active = true` with last-login and device/channel details

#### Scenario: Report absent session

- **WHEN** `get_agent_login_session` is called for an agent with no active session
- **THEN** it returns `session_active = false`

### Requirement: get_team tool

`get_team` SHALL accept `team_id` and `org_id`, and SHALL return `team_name`, `site`, `members[]`, and `associated_queues[]`.

#### Scenario: Return team detail

- **WHEN** `get_team` is called for a valid `team_id`
- **THEN** it returns the team name, site, members, and associated queues

### Requirement: get_queue tool

`get_queue` SHALL accept `queue_id` and `org_id`, and SHALL return `queue_name`, `active`, `channel_type`, `required_skills[]`, and `routing_type`.

#### Scenario: Return queue detail

- **WHEN** `get_queue` is called for a valid `queue_id`
- **THEN** it returns the queue name, active flag, channel type, required skills, and routing type

### Requirement: get_skill_profile tool

`get_skill_profile` SHALL accept `profile_id` and `org_id`, and SHALL return `profile_name` and `skills[]` where each skill has `name`, `type`, and `values`.

#### Scenario: Return skill profile detail

- **WHEN** `get_skill_profile` is called for a valid `profile_id`
- **THEN** it returns the profile name and the list of skills with name, type, and values

### Requirement: validate_agent_routing composite tool

`validate_agent_routing` SHALL accept `user_id` and `org_id`, orchestrate the read tools above, and return `{routing_valid, checks[]{check, status, detail}, blocking_issues[]}` where `status` is one of `pass`, `fail`, or `warning`. It SHALL run the checks: `user_active_and_licensed`, `team_assigned`, `team_mapped_to_active_queue`, `skills_match_queue_requirements`, `channel_enabled_in_multimedia_profile`, `no_blocking_state`, and `session_active`. It SHALL rank the most likely blocking issue(s) and cite supporting evidence.

#### Scenario: All checks pass

- **WHEN** `validate_agent_routing` runs for an agent meeting every requirement
- **THEN** it returns `routing_valid = true`, every check with status `pass`, and an empty `blocking_issues` list

#### Scenario: Blocking issue identified and ranked

- **WHEN** an agent fails one or more checks (e.g., skills do not match queue requirements)
- **THEN** it returns `routing_valid = false`, the failing checks with status `fail` and detail, and `blocking_issues` ranked by likelihood with cited evidence

#### Scenario: Warning does not block routing

- **WHEN** a check yields a non-blocking concern
- **THEN** that check is reported with status `warning` and does not by itself set `routing_valid = false`
