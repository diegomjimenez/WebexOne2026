# WxCC Address Book Sync MCP Server (WebexOne Lab)

A hands-on [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for the
**WebexOne lab**. It connects an AI assistant to the **Webex Contact Center (WxCC)** public
**Config API** and is deliberately scoped to a **single narrative** so it can be taught in
~20–30 minutes:

> **Synchronize CRM/directory contacts into a WxCC Address Book, then provision it for
> agents by attaching it to a Desktop Profile.**

The server is small on purpose. Instead of a large catalog of tools, it demonstrates the
**full MCP primitive surface** on one coherent scenario, backed by production-quality
infrastructure (OAuth broker, typed IO, structured logging) that you can study as examples
of "doing it right." Every call uses one API family — the WxCC **Config API**
(`cjp:config_read` / `cjp:config_write`).

> **Important:** All WxCC endpoint paths, OAuth URLs, and scopes ship as **placeholders**
> marked `# VERIFY` / `# TODO`. Resolve them against
> [developer.webex.com](https://developer.webex.com) before running against live APIs.
> See the [checklist](#verify--todo-checklist) below. The test suite uses mocked responses
> and needs none of this.

## Why MCP over raw APIs?

The lab's whole point is to make the value of MCP tangible. The same task — "keep our
address book in sync with the CRM and give agents access" — is painful with raw REST calls
(pagination, diffing, field mapping, deprecation traps, no guardrails) but natural with MCP:

- **Tools** turn multi-step REST choreography into one typed call with a safe dry-run.
- **Resources** give the model the CRM source of truth and the schema rules it needs, so it
  doesn't guess field formats (e.g. E.164) or scopes.
- **Prompts** encode the correct end-to-end workflow so the model follows the safe path.
- **Elicitation / progress / logging / sampling** make writes reviewable, observable, and
  explainable — things a raw API can't offer.

## What this lab teaches

Every MCP primitive is demonstrated on the address-book scenario:

| Primitive | Where you see it |
| --- | --- |
| **Tools** | 19 curated tools (address book & entry CRUD, desktop profile/agent reads, a mapping, gated assignment, and the composite sync) |
| **Resources** | 3 reference documents: the CRM source, a schema guide, and a write-safety guide |
| **Prompts** | 2 guided workflows (sync, end-to-end provisioning) |
| **Elicitation** (`ctx.elicit`) | Write tools ask the admin to approve before committing |
| **Progress** (`ctx.report_progress`) | The composite sync reports each entry as it is applied |
| **Client logging** (`ctx.info/warning/error`) | Noteworthy steps stream to the client |
| **Sampling** (`ctx.session`) | Optional sync summary, guarded by a capability check |

## The curated surface

### Tools (19)

**Address books (read + gated writes):**
`tool_list_address_books`, `tool_get_address_book`, `tool_create_address_book`,
`tool_update_address_book`, `tool_delete_address_book`.

**Entries (read + gated writes, E.164-validated):**
`tool_list_entries` (supports `search` / `filter` / `attributes`), `tool_get_entry`,
`tool_create_entry`, `tool_update_entry`, `tool_delete_entry`, `tool_bulk_save_entries`.

**Desktop profiles & agents (read-only discovery + one gated write):**
`tool_list_desktop_profiles`, `tool_get_desktop_profile`, `tool_list_agents`,
`tool_get_agent`, `tool_map_profiles_to_agents` (shows which agents each profile serves),
and `tool_assign_address_book_to_profile` (sets only `addressBookId`, preserving other
fields and dropping deprecated dial-plan fields).

**Composite sync (the "hero" tool):**
`tool_sync_crm_to_address_book` — reads the CRM source, diffs it against existing entries
(matched by CRM id, then normalized E.164), returns a dry-run preview, and on approval
applies create/update/delete with progress + logging. Pruning is **off by default**.

### Resources (3)

- `crm://contacts` — the sample CRM/directory export used as the sync source of truth.
- `wxcc://reference/address-book-schema` — naming, E.164, and `parentType` rules.
- `wxcc://reference/write-safety-guide` — write policies and per-operation risk levels.

### Prompts (2)

- `sync_crm_to_address_book` (args: `org_id`, optional `address_book_id`, `prune`) — drives
  discover → preview → sync → verify.
- `provision_outbound_dialing` (args: `org_id`, optional `book_name`, `profile_id`) — the
  full arc: find/create a book → sync from CRM → choose a profile → assign → verify agents.

## The write-safety pattern

Every write is **gated**:

1. When the MCP client supports **elicitation**, the tool builds a preview and asks the
   admin to approve interactively before committing.
2. When elicitation is unavailable, the tool falls back to a **dry-run**: it returns a
   preview and only commits when called with `confirm=True`.

Deletes and pruning are **HIGH risk** and always preview exactly what will be removed. Read
`wxcc://reference/write-safety-guide` for the full policy.

## Avoiding deprecated APIs

- **Address Book v1** is removed 2026-10-15 — the paths target **v2**.
- The deprecated **Desktop Profile** dial-plan fields (`dialPlans`,
  `agentDNValidationCriteria`, `agentDNValidationCriterions`, removed 2026-09-15) are never
  read or written; assignment touches only `addressBookId`.

## Requirements

- Python 3.11+

## Setup

```bash
cd wxcc-mcp-server
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the environment template and fill in your values:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Generate a token encryption key and paste it into `.env` as `WXCC_TOKEN_ENCRYPTION_KEY`:

```bash
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

## OAuth configuration

1. Create a Webex integration and obtain a **client id** and **client secret**.
2. Register the **redirect URI** (default `http://localhost:8765/oauth/callback`).
3. Grant the **Config API** scopes and set them in `.env`:
   - `WXCC_CONFIG_API_SCOPES` — e.g. `cjp:config_read cjp:config_write` (reads + writes)
4. Set the **authorization** and **token** endpoints (`WXCC_OAUTH_AUTHORIZE_URL`,
   `WXCC_OAUTH_TOKEN_URL`) and the single **Config API base URL** for your region
   (`WXCC_CONFIG_API_BASE`).

> The exact endpoints, scope strings, and API paths are environment-/region-specific.
> Confirm every `# VERIFY` / `# TODO` item below.

## Running the server

```bash
wxcc-mcp-server           # console script
# or
python -m wxcc_mcp.server
```

The server runs over **stdio** transport, suitable for a local MCP-capable client.

## Connecting an MCP client

Example client configuration (adapt to your client's config format):

```json
{
  "mcpServers": {
    "wxcc": {
      "command": "C:\\path\\to\\wxcc-mcp-server\\.venv\\Scripts\\wxcc-mcp-server.exe",
      "cwd": "C:\\path\\to\\wxcc-mcp-server"
    }
  }
}
```

### Debug logging to a file

Set `WXCC_LOG_FILE` in the `env` block to capture structured JSON logs to a file. Useful
when the MCP client manages the process lifecycle (e.g. Claude Desktop) and you cannot
redirect stderr manually.

```json
{
  "mcpServers": {
    "wxcc": {
      "command": "C:\\path\\to\\wxcc-mcp-server\\.venv\\Scripts\\wxcc-mcp-server.exe",
      "cwd": "C:\\path\\to\\wxcc-mcp-server",
      "env": {
        "WXCC_LOG_FILE": "C:\\path\\to\\wxcc-mcp-server\\wxcc_debug.log",
        "WXCC_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Logs are appended across restarts. Sensitive fields (tokens, secrets) are always redacted.
To tail the file in PowerShell:

```powershell
Get-Content "C:\path\to\wxcc-mcp-server\wxcc_debug.log" -Wait -Tail 20
```

## Testing

Tests use mocked WxCC responses (`httpx.MockTransport`) and never hit live APIs:

```bash
pytest
ruff check .
black --check .
```

## Project layout

```
src/wxcc_mcp/
  server.py            # MCP entrypoint (registers tools/resources/prompts + MCP primitives)
  config.py            # Settings + VERIFY/TODO Config API endpoint & scope constants
  errors.py            # Typed exception hierarchy
  logging_config.py    # Structured logging with secret redaction
  auth/oauth.py        # Per-session OAuth token broker (encrypted at rest)
  api/                 # Async client + endpoint modules (address_books, entries,
                       #   desktop_profiles, agents)
  tools/               # Curated tools (address_books, entries, desktop_profiles, agents, sync)
  resources/           # crm_contacts, address_book_schema_guide, write_safety_guide
  prompts/             # sync_crm_to_address_book, provision_outbound_dialing
  models/schemas.py    # Pydantic IO contracts (incl. E.164 validation)
tests/                 # Mocked-response tests
```

## VERIFY / TODO checklist

Resolve **every** item below against developer.webex.com before live use. Grep the code
for `VERIFY` and `TODO` to find them in context.

### `.env` / `config.py`
- [ ] `WXCC_CONFIG_API_BASE` — Config API base URL for your region. **VERIFY**
- [ ] `WXCC_OAUTH_AUTHORIZE_URL` — OAuth authorization endpoint. **VERIFY**
- [ ] `WXCC_OAUTH_TOKEN_URL` — OAuth token endpoint. **VERIFY**
- [ ] `WXCC_CONFIG_API_SCOPES` — exact scope strings for Config reads/writes
      (`cjp:config_read cjp:config_write`). **VERIFY**

### Endpoint paths (`config.py`)
- [ ] `ADDRESS_BOOKS_PATH` / `ADDRESS_BOOK_BY_ID_PATH` — Address Book **v2** collection and
      item paths. **VERIFY**
- [ ] `ADDRESS_BOOK_ENTRIES_PATH` / `ADDRESS_BOOK_ENTRY_BY_ID_PATH` — entry sub-resource
      shape (`.../entry` vs `.../entries`). **VERIFY**
- [ ] `ADDRESS_BOOK_ENTRIES_BULK_PATH` — bulk-save path and payload shape
      (upsert vs replace). **VERIFY**
- [ ] `DESKTOP_PROFILES_PATH` / `DESKTOP_PROFILE_BY_ID_PATH` — Desktop Profile paths and the
      update verb (PUT vs PATCH). **VERIFY**
- [ ] `USERS_PATH` / `USER_BY_ID_PATH` — user (agent) list/get. **VERIFY**

### Response field mappings (`tools/*.py`, `api/*.py`)
- [ ] Address book fields (`id`, `name`, `description`, `parentType`). **VERIFY**
- [ ] Entry fields (`id`, `name`, `number` vs `phoneNumber`, the attribute used to store the
      originating CRM id). **VERIFY**
- [ ] Desktop profile `addressBookId` field name. **VERIFY**
- [ ] Agent→desktop-profile link field name (`agentProfileId` vs `desktopProfileId`). **VERIFY**
- [ ] List pagination param names (`pageSize` / `page`) and the bulk-save request/response
      shape. **VERIFY**

### OAuth flow (`auth/oauth.py`)
- [ ] Authorization URL parameter names. **TODO/VERIFY**
- [ ] Token exchange request shape and response fields (`access_token`, `refresh_token`,
      `expires_in`, `scope`). **TODO/VERIFY**
- [ ] Refresh grant request/response shape. **TODO/VERIFY**

## Security notes

- No hardcoded secrets — all credentials come from the environment / `.env`.
- Access/refresh tokens are encrypted at rest and never logged (redaction) or returned to
  the model.
- Writes are gated behind elicitation (with a dry-run fallback); nothing commits without
  explicit approval. Deletes and pruning always preview exactly what will be removed.
- Phone numbers are validated as E.164 at the schema boundary before any API call.



======================================================================================================================
/// user guide

Entering explore mode — let's walk the user experience end to end, grounded in the tools/prompts/resources we just built. No code changes here, just tracing what it actually *feels* like to use.

Let me frame the whole journey first, then zoom into each step.

```
   THE USER (a WxCC admin, chatting in an MCP client like Claude Desktop)
        │
        ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  ONE-TIME SETUP        →   DAILY USE                                 │
 │  (install + connect)       (talk to the assistant in natural lang)   │
 └────────────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
   pip install,               "Sync our CRM contacts into an
   .env, connect               address book and give the Sales
   client over stdio           team access."
```

The key mental shift: **the admin never sees an API.** They talk to the assistant; the assistant picks MCP tools; the server keeps them safe.

---

## Part A — One-time setup (the "getting ready" experience)

```
Step 0.1  cd wxcc-mcp-server; python -m venv .venv; activate
Step 0.2  pip install -e ".[dev]"
Step 0.3  copy .env.example .env
Step 0.4  paste a token-encryption key into .env
Step 0.5  pytest            ← proves it works with MOCKED data (no live API needed)
Step 0.6  add to client's mcpServers config → restart client
```

After Step 0.6 the client shows the server's capabilities. From the user's chair this looks like:

```
 MCP client sidebar
 ┌─────────────────────────────┐
 │ 🔌 wxcc                      │
 │   Tools ........ 19          │
 │   Resources .... 3           │
 │   Prompts ...... 2           │
 └─────────────────────────────┘
```

That's the first "aha": they didn't wire up 19 REST endpoints — they connected one server and got a curated, safe surface.

---

## Part B — The guided (recommended) experience: running a prompt

This is the "on-rails" path. The user picks a **prompt** instead of poking tools one by one.

```
User → invokes prompt  provision_outbound_dialing(org_id="org1")
                        │
        ┌───────────────┴───────────────────────────────────────────┐
        │ The prompt injects a workflow into the conversation:       │
        │  Phase 1  address book   Phase 2  sync   Phase 3  choose   │
        │  Phase 4  assign + verify                                  │
        └───────────────────────────────────────────────────────────┘
```

Step by step, what the user actually sees:

**1. Discovery (read-only, no scary moments)**
The assistant reads `crm://contacts`, calls `tool_list_address_books`, and says something like: *"You have 2 address books. The CRM export has 7 contacts. I suggest reusing 'CRM — Enterprise Accounts' (ab1)."*

**2. Preview the sync (the dry-run moment)**
The assistant calls `tool_sync_crm_to_address_book` **without committing**. The user sees a plan, not a change:

```
 Sync preview for ab1:
   + create : 5      ~ update : 1      - delete : 0      = skip : 1
 (pruning OFF — nothing will be deleted)
```

**3. Approval (elicitation — the safety gate)**
A dialog pops in the client:

```
 ┌──────────────────────────────────────────────┐
 │ Confirm write action: sync CRM into ab1        │
 │                                                │
 │        [ Approve ]      [ Decline ]            │
 └──────────────────────────────────────────────┘
```

Nothing has changed yet. The user is in control.

**4. Apply (progress + logging — the "watch it work" moment)**
On approval, they see a live stream:

```
 [▓▓▓▓▓▓░░░░] 3/6   create Globex — Support Desk
 info: create: Initech — Sales (+14155550104)
 ...
 [▓▓▓▓▓▓▓▓▓▓] 6/6   done
```

**5. Choose who gets it (read-only again)**
`tool_map_profiles_to_agents` shows the impact *before* the change:

```
 Desktop profile   current book   agents
 ─────────────────────────────────────────
 Sales Desktop     (none)         a1, a2
 Support Desktop   ab2            a3
 (unassigned: a4)
```

*"Assign to 'Sales Desktop' and 2 agents gain access."*

**6. Assign + verify (second gated write)**
Preview shows `current: none → proposed: ab1`, user approves, then `tool_get_desktop_profile` confirms it landed.

---

## Part C — The power-user experience: atomic tools

Some users skip prompts and just say what they want. The assistant maps intent → single tools:

```
 "add a contact +1 415 555 9999 named 'VIP Desk' to ab1"
        │
        ▼
 tool_create_entry(...)  → normalizes to +14155559999 (E.164 validated)
                         → dry-run preview → elicit → commit
```

Same safety rails apply to every write, no matter the entry point.

---

## Part D — What each MCP primitive *feels* like (why it beats raw APIs)

```
 Primitive       User-facing sensation
 ───────────     ─────────────────────────────────────────────
 Tool            "I asked for a thing and got a clean result"
 Resource        assistant already "knows" the CRM data + E.164 rule
 Prompt          "it walked me through it correctly"
 Elicitation     "it asked before changing anything"
 Progress        "I can watch it happen"
 Logging         "I can see what it did, line by line"
 Sampling        "it summarized the outcome in plain English"
```

---

A few threads we could pull on next, depending on what you're after:

- **Whose experience?** The *admin using* it (what I traced above), the *developer studying* the code as a reference, or the *lab attendee* being taught? Each has a different "step by step."
- **First-run friction:** the very first tool call triggers the OAuth broker — should we trace the *auth* experience (browser sign-in vs. `WXCC_ACCESS_TOKEN` dev bypass) as its own step-by-step?
- **Failure UX:** what the user sees when a token's missing, a number's invalid, or they *decline* an approval — the "unhappy paths" are often where UX is judged.

Want me to go deeper on one of these? And if any of this is worth keeping, I can capture it as a "User Experience / walkthrough" section (e.g. in the lab guide or a design note) — just say the word.