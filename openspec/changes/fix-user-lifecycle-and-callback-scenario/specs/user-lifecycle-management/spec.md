## ADDED Requirements

### Requirement: Agent creation via Webex People API
The system SHALL create a Webex Contact Center agent identity by issuing `POST https://webexapis.com/v1/people` against the Webex Platform API family, using an access token that carries the `spark-admin:people_write` scope. The request body SHALL use `emails` as an array and MAY include `firstName`, `lastName`, `displayName`, `orgId`, and `licenses`. The WxCC Config API SHALL NOT be used to create the identity.

#### Scenario: Create agent with minimal fields
- **WHEN** `tool_create_user` is invoked with an email and the write is confirmed
- **THEN** the server sends `POST https://webexapis.com/v1/people` with body containing `emails: ["<email>"]`
- **AND** the created person's `id` is returned as the resource id

#### Scenario: Create agent with name and license
- **WHEN** `tool_create_user` is invoked with email, first/last name, and one or more license ids, and the write is confirmed
- **THEN** the request body includes `firstName`, `lastName`, and `licenses` as an array
- **AND** the response person `id` is returned

#### Scenario: Dry-run preview before commit
- **WHEN** `tool_create_user` is invoked without confirmation and the client does not approve via elicitation
- **THEN** no HTTP request is sent to the People API
- **AND** a dry-run preview describing the create action is returned

#### Scenario: Missing people scope
- **WHEN** the access token lacks `spark-admin:people_write` and a confirmed create is attempted
- **THEN** the People API returns 403
- **AND** the tool returns a plain-language insufficient-permissions message naming the required scope

### Requirement: Agent deletion via Webex People API
The system SHALL remove a Webex Contact Center agent identity by issuing `DELETE https://webexapis.com/v1/people/{personId}` against the Webex Platform API family with the `spark-admin:people_write` scope. The system SHALL NOT perform a WxCC Config API soft-delete (`{"active": false}`) for offboarding.

#### Scenario: Delete an existing agent
- **WHEN** `tool_deactivate_user` is invoked with a person id and the write is confirmed
- **THEN** the server sends `DELETE https://webexapis.com/v1/people/{personId}`
- **AND** a committed response referencing the person id is returned

#### Scenario: Dry-run preview before delete
- **WHEN** `tool_deactivate_user` is invoked without confirmation and the client does not approve
- **THEN** no delete request is sent
- **AND** a dry-run preview stating the person will be deleted is returned

### Requirement: Distinct Webex Platform API family
The system SHALL define a Webex Platform API family with base URL `https://webexapis.com` and scopes `spark-admin:people_read` and `spark-admin:people_write`, kept separate from the WxCC Config (`cjp:config*`) and Reporting (`cjp:analytics*`) families. People API endpoint paths SHALL be mapped to this family so the correct base URL and token scopes are selected.

#### Scenario: People path routes to platform base
- **WHEN** a People API path (e.g. `/v1/people`) is requested
- **THEN** the client resolves the base URL to `https://webexapis.com`
- **AND** does not use the WxCC Config or Reporting base URLs

#### Scenario: Config assignment still uses Config family
- **WHEN** a downstream agent configuration call (team/skill/multimedia assignment) is made after creation
- **THEN** it routes to the WxCC Config API base with `cjp:config` scopes, not the Platform base

### Requirement: Downstream agent configuration remains on the WxCC Config API
The system SHALL continue to assign team, skill profile, and multimedia profile to an existing agent through the WxCC Config API using the returned `personId`/user id, separate from the People API create call.

#### Scenario: Assign team after creation
- **WHEN** an agent has been created and `tool_assign_agent_to_team` is invoked with the returned id and a team id, confirmed
- **THEN** the assignment is sent to the WxCC Config API user endpoint
- **AND** the create call did not include the team id in the People API body
