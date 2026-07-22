## 1. Config: Platform family, scopes, and paths

- [x] 1.1 Add `PLATFORM = "platform"` to `ApiFamily` in `config.py`
- [x] 1.2 Add `platform_api_base` setting (default `https://webexapis.com`) and `platform_api_scopes` (default `spark-admin:people_read spark-admin:people_write`) to `Settings`
- [x] 1.3 Include Platform scopes in `combined_scopes` so brokered tokens cover people reads/writes
- [x] 1.4 Add People API path constants (`PEOPLE_PATH = "/v1/people"`, `PERSON_BY_ID_PATH = "/v1/people/{person_id}"`) with `# VERIFY` and reference URL
- [x] 1.5 Add Callback Schedule path constants (`CALLBACKS_PATH`, `CALLBACK_BY_ID_PATH`) with `# VERIFY` and reference URL
- [x] 1.6 Map People paths to `PLATFORM` and callback paths to their family in `ENDPOINT_FAMILY`

## 2. API client routing

- [x] 2.1 Extend `client._base_url` to return `platform_api_base` for `ApiFamily.PLATFORM`
- [x] 2.2 Confirm token-scope selection covers the Platform family (broker/settings)

## 3. User lifecycle API (People API)

- [x] 3.1 Rewrite `api/users.py` `create_user` to `POST` `PEOPLE_PATH` on `ApiFamily.PLATFORM` with `{emails: [...], firstName, lastName, displayName, orgId, licenses}`
- [x] 3.2 Rewrite `api/users.py` `deactivate_user` to `DELETE` `PERSON_BY_ID_PATH` on `ApiFamily.PLATFORM` (person id)
- [x] 3.3 Point `find_user_by_email`/`list_users` at the People API (`GET /v1/people?email=`/`?orgId=`) or confirm they stay on Config; annotate `# VERIFY`
- [x] 3.4 Keep `update_user` (team/skill/multimedia assignment) on the WxCC Config API

## 4. User lifecycle tools

- [x] 4.1 Update `tools/manage_users.py` `run_create` to build the People API payload (emails array, licenses) and read `id` from the response
- [x] 4.2 Update `run_deactivate` to perform the People delete; keep `reason` in the preview only
- [x] 4.3 Update `models/schemas.py` create/deactivate inputs (add `license_ids`, treat `user_id` as personId; keep WxCC assignment inputs unchanged)
- [x] 4.4 Verify `tool_create_user`/`tool_deactivate_user` signatures in `server.py` still map correctly and keep the elicitation gate

## 5. Scheduled-callback API + tools

- [x] 5.1 Add `api/callbacks.py` with `create_callback`, `list_callbacks`, `update_callback`, `delete_callback` thin async wrappers
- [x] 5.2 Add callback CRUD input models to `models/schemas.py`
- [x] 5.3 Add `tools/manage_callbacks.py` with `run_create_callback`, `run_list_callbacks`, `run_update_callback`, `run_delete_callback` using `_helpers` dry-run/committed responses
- [x] 5.4 Register `tool_create_callback`, `tool_list_callbacks`, `tool_update_callback`, `tool_delete_callback` in `server.py` with the elicitation/confirm gate on writes

## 6. Prompt swap

- [x] 6.1 Add `prompts/manage_scheduled_callbacks.py` (PROMPT_NAME, PROMPT_DESCRIPTION, `build_prompt`, `prompt_arguments`) driving the create→list→update→delete walkthrough
- [x] 6.2 Register the new prompt in `server.py`
- [x] 6.3 Remove `prompts/diagnose_agent_cannot_go_available.py`
- [x] 6.4 Remove the diagnose prompt import and `@mcp.prompt` registration from `server.py`

## 7. Docs and config

- [x] 7.1 Document `spark-admin:people_read`/`spark-admin:people_write` scopes and `WXCC_PLATFORM_API_BASE` in `.env`/README
- [x] 7.2 Note in the People-based onboarding docs that create sends an activation email (no silent provisioning)

## 8. Tests

- [x] 8.1 Update user-flow tests to assert People API base URL, `DELETE` verb, and `emails` array payload
- [x] 8.2 Add callback CRUD tests (create/list/update/delete, including dry-run vs confirmed)
- [x] 8.3 Remove/replace any tests referencing the diagnose prompt
- [x] 8.4 Run the full test suite and fix regressions
