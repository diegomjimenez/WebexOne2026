## 1. Config & scopes (Config family only)

- [x] 1.1 Remove Reporting/Search and Platform/People bases, scopes, and endpoint paths from `config.py`
- [x] 1.2 Reduce `ApiFamily` and `ENDPOINT_FAMILY` to the Config family only
- [x] 1.3 Add Address Book v2 paths (`ADDRESS_BOOKS_PATH`, `ADDRESS_BOOK_BY_ID_PATH`) marked `# VERIFY`
- [x] 1.4 Add entry paths (`ADDRESS_BOOK_ENTRIES_PATH`, `ENTRY_BY_ID_PATH`, bulk-save path) marked `# VERIFY`
- [x] 1.5 Add Desktop Profile paths (`DESKTOP_PROFILES_PATH`, `DESKTOP_PROFILE_BY_ID_PATH`) marked `# VERIFY`
- [x] 1.6 Set scopes to `cjp:config_read` / `cjp:config_write`; update `.env.example`

## 2. Remove the agent-lifecycle scenario

- [x] 2.1 Delete agent-lifecycle tools (`get_user`, `get_user_config`, `get_agent_state_history`, `get_agent_login_session`, `get_team`, `get_queue`, `get_skill_profile`, `list_teams`, `list_skill_profiles`, `validate_agent_routing`, `manage_users`, `manage_callbacks`, onboard flow)
- [x] 2.2 Delete corresponding `api/` modules (state, search, teams, skills, queues, callbacks, users lifecycle, People)
- [x] 2.3 Delete agent-lifecycle resources (agent-states, error-codes, config-dependency-map, troubleshooting-runbook, onboarding-checklist)
- [x] 2.4 Delete agent-lifecycle prompts (`onboard_new_agent`, `manage_scheduled_callbacks`)
- [x] 2.5 Delete their tests
- [x] 2.6 Reshape `models/schemas.py`: drop old contracts, keep shared base types

## 3. Address book & entry API + tools

- [x] 3.1 Add `api/address_books.py` (list/get/create/update/delete) using the shared client
- [x] 3.2 Add `api/entries.py` (list with search/filter/attributes, get/create/update/delete, bulk-save)
- [x] 3.3 Add Pydantic IO contracts for books and entries in `models/schemas.py`
- [x] 3.4 Add read tools: `list_address_books`, `get_address_book`, `list_entries`, `get_entry`
- [x] 3.5 Add gated write tools: create/update/delete address book (dry-run + elicitation)
- [x] 3.6 Add gated write tools: create/update/delete entry with E.164 validation
- [x] 3.7 Add gated `bulk_save_entries` tool

## 4. Desktop profile & agent discovery + provisioning

- [x] 4.1 Add `api/desktop_profiles.py` (list/get, update `addressBookId`) avoiding deprecated fields
- [x] 4.2 Add `api/agents.py` read-only (list/get) exposing the assigned profile id (`# VERIFY` field)
- [x] 4.3 Add IO contracts for desktop profiles and agents
- [x] 4.4 Add read tools: `list_desktop_profiles`, `get_desktop_profile`, `list_agents`, `get_agent`
- [x] 4.5 Add a profile↔agent mapping tool (derived from reads)
- [x] 4.6 Add gated `assign_address_book_to_profile` tool preserving other profile fields

## 5. CRM source & composite sync

- [x] 5.1 Add `resources/crm_contacts.py` returning a JSON array of sample contacts (`crm://contacts`)
- [x] 5.2 Add `resources/address_book_schema_guide.py` (naming, E.164, `parentType`)
- [x] 5.3 Retain/adapt `resources/write_safety_guide.py` for address-book/prune risk levels
- [x] 5.4 Implement diff (create/update/delete) matched on CRM id then normalized E.164
- [x] 5.5 Implement composite `sync_crm_to_address_book` tool: preview → elicit → apply with progress + logging; `prune` defaults off
- [x] 5.6 Add optional sampling summary with deterministic fallback

## 6. Prompts & server wiring

- [x] 6.1 Add prompt `sync_crm_to_address_book` (discover → sync → verify)
- [x] 6.2 Add prompt `provision_outbound_dialing` (find/create book → sync → choose profile → assign → verify agents)
- [x] 6.3 Rewire `server.py` to register only the new tools/resources/prompts; remove old registrations
- [x] 6.4 Keep the elicitation/dry-run/progress/logging helpers intact

## 7. Tests

- [x] 7.1 Mocked tests for address book CRUD tools
- [x] 7.2 Mocked tests for entry CRUD + bulk-save tools
- [x] 7.3 Mocked tests for desktop profile/agent reads and the mapping
- [x] 7.4 Mocked tests for `assign_address_book_to_profile` (preview, commit, field preservation)
- [x] 7.5 Mocked tests for the sync diff (create/update/delete + prune off by default)
- [x] 7.6 Retain infra tests (auth, client) and ensure the suite is green

## 8. Docs & verification

- [x] 8.1 Rewrite `wxcc-mcp-server/README.md` for the new scenario and primitive map
- [x] 8.2 Rewrite `lab-materials/lab-guide/lab-guide.md` for the new chapters
- [x] 8.3 Update the VERIFY/TODO checklist (v2 paths, entry paths, profile update verb, agent→profile field, bulk-save shape)
- [x] 8.4 Run `pytest`, `ruff check .`, `black --check .`; fix issues
- [x] 8.5 Run `openspec validate --changes refactor-lab-to-address-book-sync` and resolve any errors
