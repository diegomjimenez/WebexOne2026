# CRM → Address Book Sync, Powered by MCP — Lab Guide

*WebexOne 2026 Technical Training*

Build a Model Context Protocol (MCP) server that lets an AI assistant manage a **Webex Contact
Center (WxCC)** Address Book — create it, populate it with contacts, and provision it for a
specific agent — safely and end to end. This guide follows a **concrete, worked walkthrough**:
you will stand up the server, then drive a real scenario through an MCP client:

> **Create an "Internal Directory" address book → add two contacts → make agent `user2` see
> them on their Agent Desktop.**

Along the way you meet every core MCP primitive and the guardrails that make the writes safe.

---

## About this lab

A common WxCC administration task is to **stand up an address book and make its contacts
available to agents** for outbound dialing. Done with raw REST APIs this means pagination,
diffing, field mapping, deprecation traps, E.164 validation, and no guardrails. This lab shows
how MCP turns the same task into a safe, typed, reviewable capability an AI assistant can drive
— using a **single WxCC API family, the Config API** — with **gated writes** so nothing changes
without explicit approval.

This session will enable you to:

- Understand the MCP primitive surface: **tools, resources, prompts, elicitation,
  progress, client logging, and sampling** — and *why each beats a raw API call*.
- Stand up and connect the `wxcc-mcp-server` to an MCP-capable client.
- Run a real end-to-end flow: **create an address book, add entries, and assign it to the
  desktop profile of a named agent** — each write gated by a preview/approval step.
- Recognize real-world API constraints the server enforces for you: **E.164 phone formatting**,
  **least-privilege read scopes**, and **shared desktop profiles**.

**Scope & format.** ~20–30 minutes. The walkthrough is **hands-on**; the sync hero tool and
"going further" topics are **instructor-run demos**. All code lives in the companion
`wxcc-mcp-server/` — you do not clone a separate repo.

> **Note.** WxCC endpoint paths, OAuth URLs, and scopes ship as `# VERIFY` / `# TODO`
> placeholders. The lab can run against **mocked responses**, or — as shown in this guide —
> against a **live org** by pasting a WxCC-scoped access token into `.env`. The concrete IDs in
> the sample outputs below come from one such live run; yours will differ.

---

## Getting started

You will work with:

- **Python 3.11+**
- **The `wxcc-mcp-server` repository** (already on your workstation)
- **An MCP-capable client** (e.g. Claude Desktop or any MCP client)
- **A code editor** (VS Code recommended)

### Step 0.1: Create and activate a virtual environment

Open a terminal in the repository root and change into the server directory:

```powershell
cd wxcc-mcp-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
```

### Step 0.2: Install the server (with dev extras)

```powershell
pip install -e ".[dev]"
```

### Step 0.3: Create your environment file

```powershell
copy .env.example .env               # macOS/Linux: cp .env.example .env
```

### Step 0.4: Generate a token-encryption key

Access/refresh tokens are encrypted at rest. Generate a key and paste it into `.env`
as `WXCC_TOKEN_ENCRYPTION_KEY`:

```powershell
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

### Step 0.5: (Optional) Point the lab at a live org

To run the walkthrough against real WxCC data (as this guide does), set in `.env`:

- `WXCC_ORG_ID` — your organization id.
- `WXCC_ACCESS_TOKEN` — a WxCC-scoped Webex token with at least `cjp:config_read`
  (and `cjp:config_write` for the create/assign steps).

Leave the token blank to stay fully mocked. **Never commit `.env`.**

### Step 0.6: Run the test suite (mocked — no live APIs)

```powershell
pytest
```

You should see the tests pass. This confirms your environment is ready.

### Step 0.7: Start the server and connect a client

The server speaks **stdio** transport. Start it directly to confirm it launches:

```powershell
wxcc-mcp-server        # or: python -m wxcc_mcp.server
```

Then point your MCP client at it. Example client configuration:

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

Confirm the client lists the WxCC tools, resources, and prompts. You are ready to build.

---

## 1 — Build-live: read before you write  *(hands-on)*

**Objective.** See the smallest complete MCP round-trip and confirm connectivity by listing what
already exists — before you change anything.

Reference: `src/wxcc_mcp/tools/`, `src/wxcc_mcp/resources/`, `src/wxcc_mcp/prompts/`.

### Step 1.1: Read the atomic tool `list_address_books`

Open `src/wxcc_mcp/tools/address_books.py`. Notice:

- `run_list()` accepts a validated `ListAddressBooksInput` and returns a typed
  `ListAddressBooksOutput` — Pydantic contracts, not raw JSON.
- Every mapped response field is marked `# VERIFY` so you know what to confirm against
  developer.webex.com.

### Step 1.2: List existing address books

From your MCP client, invoke `tool_list_address_books` with your `org_id`. A live org returns
the books already present — this both proves connectivity and shows you the starting state:

```json
{
  "org_id": "<ORG_ID>",
  "total_returned": 2,
  "address_books": [
    { "address_book_id": "516379fb-…", "name": "test1", "parent_type": "SITE" },
    { "address_book_id": "87ac75ea-…", "name": "AB",    "parent_type": "ORGANIZATION" }
  ]
}
```

### Step 1.3: Read the reference resources

- `src/wxcc_mcp/resources/crm_contacts.py` (`crm://contacts`) — the sample CRM export that
  serves as a **source of truth** for the sync demo.
- `src/wxcc_mcp/resources/address_book_schema_guide.py`
  (`wxcc://reference/address-book-schema`) — naming rules, **E.164** phone formatting, and
  what an address book's `parentType` (`ORGANIZATION` vs `SITE`) means.

> **Solution.** The round-trip works because each primitive has one job: the **tools** fetch and
> change typed data, and the **resources** supply the source data and domain rules the model
> needs to interpret it. Listing first is the safe habit the write-safety guide encourages — you
> always know the before-state.

---

## 2 — Create the address book  *(hands-on)*

**Objective.** Create a new organization-wide address book called **Internal Directory** — with
a preview/approve gate so nothing commits by accident.

Reference: `src/wxcc_mcp/tools/address_books.py`, `wxcc://reference/write-safety-guide`.

### Step 2.1: Understand the create contract

`tool_create_address_book` requires `name` and `parent_type` (`ORGANIZATION` or `SITE`), with an
optional `description`. Like every write tool it takes a `confirm` flag: without approval it
returns a **dry-run preview**; only an approved call (or `confirm=True`) commits.

### Step 2.2: Create "Internal Directory"

Invoke `tool_create_address_book` with `parent_type = ORGANIZATION` so every site can use it.
On approval you get the committed record and its new id:

```json
{
  "committed": true,
  "resource_id": "9ba275fa-…",
  "result": {
    "id": "9ba275fa-…",
    "name": "Internal Directory",
    "description": "Organization-wide internal contact directory",
    "parentType": "ORGANIZATION",
    "addressBookEntries": []
  }
}
```

Keep the returned `address_book_id` — you need it for every step that follows.

> **Solution.** The gate is structural: the tool builds the payload, previews it, and commits
> only after approval. Choosing `ORGANIZATION` here is a deliberate scope decision the model
> surfaces rather than hides.

---

## 3 — Add contacts (and meet E.164)  *(hands-on)*

**Objective.** Add two contacts — **Mo** and **DO** — and learn why the server rejects
malformed phone numbers *before* they ever reach WxCC.

Reference: `src/wxcc_mcp/tools/entries.py`, `wxcc://reference/address-book-schema`.

### Step 3.1: First attempt — watch validation catch a bad number

Call `tool_create_entry` for **Mo** with number `05` and **DO** with number `98`. The server
refuses both, with a typed validation error:

```text
Value error, Phone number '05' is not valid E.164 (e.g. +14155551234).
```

This is the schema contract doing its job: WxCC address book entries must be **E.164**
(`+` country code, then the full number). Catching it in the tool means no half-broken write
hits the API.

### Step 3.2: Retry with valid E.164 numbers

Re-call `tool_create_entry` with proper numbers (here, placeholders while real DIDs are pending):

| Contact | Number         | Result entry id |
|---------|----------------|-----------------|
| **Mo**  | `+10500000000` | `3b5cafdf-…`    |
| **DO**  | `+19800000000` | `b41b8706-…`    |

Each returns `committed: true`. You can update them with real numbers later via
`tool_update_entry`.

> **Solution.** Validation lives in the typed input model (`CreateEntryInput`), so the assistant
> gets an actionable message and the org data stays clean. A raw API call would have either
> failed opaquely or stored garbage.

---

## 4 — Provision for agent `user2`: gated writes  *(hands-on)*

**Objective.** Make the new address book visible to a **named agent** — `user2` — on their Agent
Desktop, showing exactly who is affected before committing.

Reference: `wxcc://reference/write-safety-guide`, `src/wxcc_mcp/tools/agents.py`,
`src/wxcc_mcp/tools/desktop_profiles.py`.

### Step 4.1: Find the agent and their profile

Agents inherit their address book from the **desktop profile** assigned to them, so first find
which profile `user2` uses.

> **Least-privilege note.** `tool_get_agent` may return *"Permission denied … does not have
> rights to read this WxCC data"* if your token lacks the per-user read scope. That is expected
> — fall back to `tool_list_agents`, which lists every agent with their `desktop_profile_id`:

```json
{
  "agents": [
    { "email": "user1@…", "desktop_profile_id": "89dea615-…" },
    { "email": "user2@…", "desktop_profile_id": "89dea615-…" },
    { "email": "admin@…", "desktop_profile_id": null }
  ]
}
```

Here `user2` uses profile **`89dea615-…` ("Agent-Profile")**.

### Step 4.2: See who else shares the profile

Call `tool_list_desktop_profiles` (or `tool_map_profiles_to_agents`). Note two things before you
write:

- "Agent-Profile" currently points at the **"AB"** address book — assigning ours **replaces** it.
- **`user1` shares the same profile**, so they will see the new contacts too.

This is the real-world caveat: profiles are shared, so a "make one agent see it" request can
affect several. Surface it, don't hide it.

### Step 4.3: Assign the address book and approve

Call `tool_assign_address_book_to_profile(profile_id, address_book_id)`. The preview shows the
current vs proposed `addressBookId`. **Approve** it. The committed profile reflects the change:

```json
{
  "committed": true,
  "result": {
    "id": "89dea615-…",
    "name": "Agent-Profile",
    "addressBookId": "9ba275fa-…"
  }
}
```

The tool changes only `addressBookId`, preserves every other (non-deprecated) profile field, and
never touches the deprecated dial-plan fields.

### Step 4.4: Verify

`tool_get_desktop_profile` confirms the new `addressBookId`. When `user2` next logs into the
Agent Desktop, **Mo** and **DO** appear in their address book — and, as noted, so will they for
`user1`.

> **Solution.** Safety is structural, not advisory: every write is gated by elicitation with a
> `confirm=True` dry-run fallback, tokens are never returned to the model, the assignment
> preserves unrelated fields, and the shared-profile impact is made explicit before commit.

---

## 5 — The sync hero tool  *(instructor-run demo)*

**Objective.** Reconcile an address book with the CRM in one call, with a safe preview — the
scalable version of the manual entry adds you did in Chapter 3.

Reference: `src/wxcc_mcp/tools/sync.py`, `crm://contacts`,
`wxcc://reference/write-safety-guide`.

- **Preview (dry-run).** `tool_sync_crm_to_address_book(org_id, address_book_id)` without
  approval reads the CRM source, lists existing entries, and reports how many to **create**,
  **update**, and **delete** (delete only when pruning is on).
- **Diff logic.** `sync.compute_diff` matches CRM contacts to existing entries **by CRM id
  first, then by normalized E.164 number**, classifying each as create / update / skip. Pruning
  is **off by default**.
- **Approve and apply.** On approval the tool applies the plan, streaming **progress** per entry
  and **client logs** per change, with an optional natural-language **summary** (sampling) and a
  deterministic fallback.

> **Solution.** The "hero" experience comes from composition: one tool orchestrates reads,
> diffing, and gated writes, while progress, logging, and optional sampling make it observable.
> Doing this by hand — as in Chapter 3, one entry at a time — does not scale.

---

## 6 — Going further  *(instructor-run demo)*

- **Sampling.** The sync tool can ask the client's model to summarize the result
  (`ctx.session`), guarded by a capability check — optional, with a deterministic fallback.
- **Debugging.** Set `WXCC_LOG_FILE` (and `WXCC_LOG_LEVEL=DEBUG`) in the client's `env` block to
  capture structured JSON logs with secrets redacted. Tail with
  `Get-Content <file> -Wait -Tail 20`.
- **Avoid deprecation.** The server targets **Address Book v2** and never uses the deprecated
  Desktop Profile dial-plan fields — check API lifecycles before going live.
- **Go live.** Resolve every `# VERIFY` / `# TODO` (base URL, OAuth endpoints, scopes, endpoint
  paths, response field mappings) against
  [developer.webex.com](https://developer.webex.com). See the README's VERIFY/TODO checklist.
- **Extend the narrative.** New tools slot into the same pattern: typed IO, structured logging,
  and — for writes — the elicitation/dry-run gate.

---

## References

- Model Context Protocol: <https://modelcontextprotocol.io>
- Webex Contact Center for Developers: <https://developer.webex.com/docs/contact-center>
- Server README and VERIFY/TODO checklist: `wxcc-mcp-server/README.md`
