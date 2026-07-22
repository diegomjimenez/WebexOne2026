## Context

The lab MCP server (`wxcc-mcp-server`) models the agent lifecycle and diagnostics for Webex Contact Center. It has two structural problems this change addresses:

1. **Wrong API for agent identity.** `api/users.py` `create_user`/`deactivate_user` build WxCC Config API paths (`/organization/{org_id}/user`) on the `config_api_base` (`https://api.wxcc-REGION.cisco.com`). Webex identities are not created there. Per the [Webex People API](https://developer.webex.com/docs/api/v1/people), agents are provisioned with `POST https://webexapis.com/v1/people` (scope `spark-admin:people_write`) and removed with `DELETE https://webexapis.com/v1/people/{personId}`. The payload also differs: `emails` is an array, and `licenses`/`orgId` are used, not a bare `{"email": ...}`.

2. **Read-only "scenario" that duplicates a diagnostic.** The `diagnose_agent_cannot_go_available` prompt is a read-only flow that largely re-drives `validate_agent_routing`. Replacing it with a scheduled-callback CRUD scenario against the [Callback Schedule API](https://developer.webex.com/webex-contact-center/docs/api/v1/callback-schedule) gives the lab a clean write-path story (create → list → update → delete) with the existing elicitation/confirm safety gate.

The codebase convention is that every externally-defined path/scope is a placeholder annotated `# VERIFY` in `config.py` until confirmed against developer.webex.com. This change keeps that convention.

## Goals / Non-Goals

**Goals:**
- Route agent create/delete through the Webex People API with correct payload/verbs and scopes.
- Introduce a distinct Webex Platform API family so Config, Reporting, and Platform bases/scopes stay separate.
- Preserve WxCC Config API usage for downstream agent configuration (team/skill/multimedia assignment) after the person exists.
- Add create/list/update/delete tools and a guided prompt for scheduled callbacks.
- Remove the `diagnose_agent_cannot_go_available` prompt and its registration.
- Keep all writes behind the existing elicitation/`confirm` dry-run gate.

**Non-Goals:**
- Reworking OAuth broker internals beyond adding the Platform family scopes.
- Migrating to the SCIM 2.0 provisioning API (People API is sufficient for the lab; note it as a future option).
- Changing the read-only diagnostic tool `validate_agent_routing` (only the prompt is removed).
- Implementing license discovery UI; `license_ids` is an optional passthrough.

## Decisions

### Decision 1: Add a `PLATFORM` API family rather than overloading `CONFIG`
`ApiFamily` gains `PLATFORM = "platform"` with `platform_api_base` defaulting to `https://webexapis.com` and scopes `spark-admin:people_read spark-admin:people_write`. `client._base_url` maps the new family; `ENDPOINT_FAMILY` maps the People paths to `PLATFORM`.
- **Why:** `config.py` explicitly states Config and Reporting are distinct families that must not be merged. People API is a third, platform-wide base with its own scopes. Overloading `CONFIG` would send `cjp:*`-scoped tokens to `webexapis.com` and break auth.
- **Alternative considered:** Reuse `CONFIG` with a per-call base override — rejected as it defeats the family/scope separation the client is built around.

### Decision 2: People API payload shape
`create_user` sends `{"emails": [email], "firstName": ..., "lastName": ..., "displayName": ..., "orgId": org_id, "licenses": [...]}`; drop WxCC-only fields (`siteId`, `teamId`, `agentProfileId`, `skillProfileId`, `multimediaProfileId`) from the create call. Those become downstream Config API assignments once the `personId` is returned.
- **Why:** Matches the People API contract; WxCC agent attributes are not accepted by `POST /v1/people`.
- **Alternative considered:** Send everything in one call — rejected; the People API rejects unknown fields and WxCC config lives in a different family.

### Decision 3: Hard delete vs soft deactivate
Offboarding calls `DELETE https://webexapis.com/v1/people/{personId}`. The tool keeps the name `deactivate_user`/`tool_deactivate_user` for lab continuity but performs a People delete; `reason` becomes advisory metadata in the preview only (the People delete has no body).
- **Why:** The People API has no `{"active": false}` semantics; delete is the supported removal.
- **Trade-off:** Delete is destructive and not reversible via this API. Mitigated by keeping the elicitation/confirm gate and a clear preview.

### Decision 4: Callback capability shape
New `api/callbacks.py` (thin async wrappers) + `tools/manage_callbacks.py` with `run_create_callback`, `run_list_callbacks`, `run_update_callback`, `run_delete_callback`. Path constants in `config.py` under the WxCC Config/CC family, annotated `# VERIFY`, e.g. `CALLBACKS_PATH` and `CALLBACK_BY_ID_PATH`. A new prompt `manage_scheduled_callbacks.py` drives the CRUD walkthrough. Reads (list) return raw records; writes reuse the `_helpers.dry_run_response`/`committed_response` and the server-level elicitation gate.
- **Why:** Mirrors the existing `manage_users` structure so the lab stays consistent and teaches the same MCP primitives (tools, prompt, elicitation, progress).
- **Verification note:** Exact callback paths, path params, and body fields are placeholders pending confirmation on developer.webex.com; marked `# VERIFY` like all other endpoints.

### Decision 5: Replace, not deprecate, the diagnose prompt
Delete `prompts/diagnose_agent_cannot_go_available.py`, remove its import and `@mcp.prompt` registration in `server.py`. The diagnostic *tool* stays.
- **Why:** The user asked to replace the scenario; the underlying read capability is still available via `validate_agent_routing`.

## Risks / Trade-offs

- **Unverified endpoint paths** (People email search, callback CRUD) → Keep `# VERIFY` annotations and centralize them in `config.py` so a single grep surfaces everything before live use.
- **New required scopes** (`spark-admin:people_*`) not present in existing tokens → Document in `.env`/README and surface a clear `InsufficientPermissionsError` (403) message; onboarding fails safe until scopes are granted.
- **Destructive delete** replacing soft-deactivate → Preserve elicitation/confirm dry-run default; preview clearly states the person will be deleted.
- **People API sends an activation email on create** → Note in the prompt/README so lab users expect it; not silent provisioning.
- **Breaking change to tool payloads** (`email` string → `emails` array internally) → Tool signatures stay the same for the model; the shape change is internal to `manage_users`/`api.users`.

## Migration Plan

1. Add Platform family (base + scopes) and People/callback path constants to `config.py`.
2. Update `api/users.py` create/delete to the People API; add `api/callbacks.py`.
3. Update `tools/manage_users.py` payload/verbs; add `tools/manage_callbacks.py`.
4. Add callback prompt; remove diagnose prompt.
5. Update `server.py` registrations (drop diagnose prompt, add callback tools + prompt).
6. Update `models/schemas.py` inputs.
7. Update `.env`/README scope docs.
8. Update/adjust tests; add callback CRUD tests.
- **Rollback:** revert the change set; no persistent data migrations are involved.

## Open Questions

- Exact Callback Schedule API base family (WxCC CC base vs platform) and path/params — confirm on developer.webex.com and update the `# VERIFY` constants.
- Whether the lab should also demonstrate license discovery (`GET /v1/licenses`) before create, or keep `license_ids` as an optional passthrough.
