## Why

The lab MCP server currently creates and deletes agents against the wrong API. `create_user` and `deactivate_user` route through the WxCC Config API (`https://api.wxcc-REGION.cisco.com/organization/{org_id}/user`), which has no such endpoints. Agent identities are actually provisioned through the Webex People API (`POST https://webexapis.com/v1/people`), so onboarding/offboarding cannot work as written. Separately, the write-scenario the lab teaches (`diagnose_agent_cannot_go_available`) is read-only and duplicates the existing `validate_agent_routing` diagnostic; replacing it with a full create/list/update/delete scheduled-callback scenario gives the lab a clean, self-contained CRUD story against a real WxCC API.

## What Changes

- **BREAKING** Repoint agent creation to the Webex People API: `POST https://webexapis.com/v1/people` with the correct payload shape (`emails` as an array, optional `licenses`, `orgId`), replacing the WxCC Config path and the `{"email": ...}` string body.
- **BREAKING** Repoint agent deletion to `DELETE https://webexapis.com/v1/people/{personId}`, replacing the current soft-delete PUT of `{"active": false}`.
- Add a new Webex Platform API family (base `https://webexapis.com`) with its own scopes (`spark-admin:people_read`, `spark-admin:people_write`) distinct from the `cjp:*` Config/Reporting scopes.
- Keep the WxCC Config API only for post-creation agent configuration (team / skill-profile / multimedia assignment).
- **BREAKING** Remove the `diagnose_agent_cannot_go_available` prompt/scenario and its server registration.
- Add a scheduled-callback capability: tools to create, list, update, and delete callback schedules via the WxCC Callback Schedule API, plus a prompt that drives the CRUD scenario.
- Update `.env` / config documentation to list the People API scopes required for onboarding/offboarding.

## Capabilities

### New Capabilities
- `user-lifecycle-management`: Correct create/delete of Webex Contact Center agents via the Webex People API, with WxCC Config API used only for downstream agent configuration.
- `scheduled-callback-management`: Create, list, update, and delete scheduled callbacks via the WxCC Callback Schedule API, exposed as MCP tools and a guided prompt, replacing the read-only diagnose scenario.

### Modified Capabilities
<!-- No existing main specs in openspec/specs/; nothing to modify. -->

## Impact

- Config: `config.py` (new API family, base URL, scopes, People/callback path constants), `.env` (People API scopes).
- API layer: `api/users.py` (People API create/delete), new `api/callbacks.py`, `api/client.py` (route the new family).
- Tools: `tools/manage_users.py` (payload/verb changes), new `tools/manage_callbacks.py`.
- Prompts: remove `prompts/diagnose_agent_cannot_go_available.py`, add `prompts/manage_scheduled_callbacks.py`.
- Server: `server.py` registration (drop diagnose prompt, add callback tools + prompt).
- Models: `models/schemas.py` (People create/delete inputs, callback CRUD inputs).
- Tests: update user-flow tests; add callback CRUD tests.
- Reference: `https://developer.webex.com/docs/api/v1/people` and `https://developer.webex.com/webex-contact-center/docs/api/v1/callback-schedule`.
