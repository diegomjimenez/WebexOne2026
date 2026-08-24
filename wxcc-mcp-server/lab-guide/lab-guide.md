# CRM → Address Book Sync, Powered by MCP — Lab Guide

*WebexOne 2026 Technical Training*

Build a Model Context Protocol (MCP) server that lets an AI assistant keep a **Webex Contact
Center (WxCC)** Address Book in sync with a CRM — and provision it for agents — safely and
end to end. This guide follows a **concrete, worked walkthrough**: you will set up the book
manually on Day 1, then watch the system handle a week of CRM drift in seconds.

> **Day 1:** Create an address book, add 3 contacts by hand, assign it to agent `user2`.
> **Monday Morning:** The CRM changed overnight — 4 new contacts, 1 updated number, 1 removal.
> **The payoff:** One sync command resolves it all, with a preview and approval gate.

Along the way you meet every core MCP primitive and the guardrails that make writes safe.

---

## The scenario

Your organization's CRM (Salesforce, HubSpot, Dynamics — doesn't matter which) is the
**source of truth** for outbound contacts: agent speed-dials, partner escalation lines,
customer callback numbers. These change **every week** — new accounts close, employees leave,
vendors get new DIDs.

Today an admin manually exports contacts, diffs them against WxCC, and re-enters changes one
by one. That takes **30–60 minutes per week**, is error-prone (typos, missed deletes, wrong
E.164 formatting), and when the admin is on vacation the address book drifts. Agents dial
stale numbers, callbacks fail, SLA breaches follow.

**This lab builds the fix.** An MCP server that makes the weekly sync a single reviewable
command — whether the CRM changed 3 contacts or 300 — with typed validation, approval gates,
and full observability. You will feel the manual friction first, then experience the
automated relief.

---

## About this lab

This session will enable you to:

- Understand the MCP primitive surface: **tools, resources, prompts, elicitation,
  progress, client logging, and sampling** — and *why each beats a raw API call*.
- Stand up and connect the `wxcc-mcp-server` to an MCP-capable client.
- Experience the **manual workflow** (Day 1) vs. the **automated workflow** (Monday Morning)
  and feel the difference at low scale — then imagine it at 500 contacts.
- Recognize real-world API constraints the server enforces for you: **E.164 phone formatting**,
  **least-privilege read scopes**, and **shared desktop profiles**.

**Scope & format.** ~20–30 minutes. Chapters 1–4 are **hands-on** (setup, manual adds,
provisioning). Chapter 5 is the **"Monday Morning"** reveal. Chapter 6 is the **sync payoff**
(instructor-run demo). All code lives in the companion `wxcc-mcp-server/` — you do not clone
a separate repo.

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

> **"I don't have raw MCP JSON-RPC access" — what does that mean?**
>
> If you ask the LLM inside your client to "run `prompts/list`" or "show me `resources/list`",
> it will likely reply: *"I don't have raw protocol access."* This is correct and expected.
> There are **two levels** of access inside every MCP client:
>
> ```text
>   ┌───────────────────────────────────────────────────────────────────┐
>   │  THE CLIENT (code)          THE LLM (model inside the client)    │
>   │  ─────────────────          ────────────────────────────────     │
>   │                                                                  │
>   │  • Speaks JSON-RPC          • Only sees what the client          │
>   │  • Calls tools/list,          chose to expose                    │
>   │    prompts/list,            • Tools → callable functions ✓       │
>   │    resources/list           • Prompts → maybe (client decides)   │
>   │  • Negotiates capabilities  • Resources → maybe (client decides) │
>   │  • This is CODE             • Has NO protocol access             │
>   │                                                                  │
>   └───────────────────────────────────────────────────────────────────┘
> ```
>
> The **client software** talks to the MCP server using JSON-RPC — it calls `tools/list`,
> `prompts/list`, and `resources/list` during connection setup. But the **LLM** never sees
> those protocol messages. It only sees what the client decided to surface:
>
> | Primitive | Claude Desktop | Cursor | Custom bot |
> |---|---|---|---|
> | Tools | All shown, model-invokable | Progressive load (subset shown) | Translated to OpenAI functions |
> | Prompts | `/` slash-command menu | Not surfaced to model | Not surfaced (unless wired) |
> | Resources | Attachment menu (📎) | Not surfaced to model | Optionally injected at startup |
>
> So if your LLM says "I can't see prompts" — that is **not a server bug**. The server
> registered them correctly. The client simply didn't wire that protocol method into anything
> the model can reach. This is by design: tools are *model-controlled*, but prompts are
> *user-controlled* and resources are *application-controlled* — each has a different actor
> who triggers it.
>
> **To verify all primitives are registered**, use the
> [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) — it shows tools,
> prompts, and resources in separate tabs regardless of what any specific client surfaces.

> **Known client limitations (as of mid-2026).** Even when the server correctly registers
> prompts and resources, current MCP clients have documented gaps:
>
> | Issue | Client | Status | Reference |
> |---|---|---|---|
> | Model cannot call `prompts/list` or `resources/read` programmatically | Claude Desktop | Confirmed by Anthropic: *"not something we have plans to work on in the short term"* | [claude-ai-mcp#23](https://github.com/anthropics/claude-ai-mcp/issues/23) |
> | Resources listed in Settings but LLM ignores them (does web search instead) | Claude Desktop | Open | [typescript-sdk#686](https://github.com/modelcontextprotocol/typescript-sdk/issues/686) |
> | Dynamic resource templates (`greeting://{name}`) broken | Claude Desktop | Tracked as P0 | [layered.dev](https://layered.dev/mcp-resources-the-overlooked-primitive/) |
> | Local stdio prompts fail to invoke (regression on Windows) | Claude Desktop 1.24012.x | Open | [claude-code#82045](https://github.com/anthropics/claude-code/issues/82045) |
> | Prompt title/name parsing — spaces in title break slash commands | Claude Code | Fixed in later builds | [claude-code#10992](https://github.com/anthropics/claude-code/issues/10992) |
> | Agents cannot discover or use prompts (no `ListMcpPromptsTool`) | Claude Code | Closed as "not planned" | [claude-code#37900](https://github.com/anthropics/claude-code/issues/37900) |
> | Prompts and resources not surfaced to model at all | Cursor | By design (tools-only progressive loading) | — |
>
> **Practical workaround.** The community-adopted pattern is to wrap critical resources and
> prompts as **tools** — the one primitive all clients reliably support. This trades the MCP
> control-model separation for universal accessibility:
>
> ```python
> @mcp.tool()
> async def read_schema_guide() -> str:
>     """Read the address book schema reference."""
>     return json.dumps(address_book_schema_guide.as_dict(), indent=2)
> ```
>
> This lab keeps prompts and resources as their proper types (they work in MCP Inspector and
> teach the correct architecture), but be aware that not every client will surface them to
> the model automatically. See the **Appendix — Client primitive support matrix** for the
> full picture.

> **Why does MCP Inspector show resources but Claude Desktop doesn't?**
>
> If you verify your server with MCP Inspector and see `crm://contacts` listed and readable,
> but Claude Desktop's model says *"I'd need a CRM connector"* — this is **expected behavior**,
> not a bug. The reason is the MCP **control model**:
>
> | Primitive | Control actor | Who decides when to use it |
> |-----------|--------------|---------------------------|
> | Tools | **Model** | The AI decides to call a tool autonomously |
> | Prompts | **User** | The human picks from a slash-command menu |
> | Resources | **Application** | The client code decides what to inject into context |
>
> MCP Inspector works because **you** are the application — when you click "Read Resource",
> you're playing the application role and calling `resources/read` yourself. There is no
> model in the loop.
>
> Claude Desktop's position: since resources are *application-controlled*, the model should
> not be able to pull arbitrary data into the conversation without the user's awareness.
> They implemented this as a **manual attachment** (the `+` button) — putting you in control.
> The model itself has no mechanism to call `resources/read`.
>
> Anthropic confirmed this in
> [claude-ai-mcp#23](https://github.com/anthropics/claude-ai-mcp/issues/23):
> *"not something we have plans to work on in the short term."* Their reasoning: allowing the
> model to autonomously read resources would change the security model — the model could pull
> data the user didn't intend to share in that conversation.
>
> **Contrast with Claude Code:** Claude Code *does* have `ListMcpResourcesTool` — it lets the
> agent discover and read resources programmatically. The difference is trust assumptions:
> Claude Code runs in a developer terminal where the user expects the model to access local
> data. Claude Desktop is a consumer product with a broader threat model.
>
> **What this means for the lab:**
>
> - At Step 5.1, when you ask *"What contacts does the CRM have?"*, Claude Desktop's model
>   does not know `crm://contacts` exists. It pattern-matches on "CRM" and hallucinates
>   about connectors from its training data.
> - **Fix:** manually attach the resource via `+` before asking, or ask explicitly:
>   *"Read the crm://contacts resource for me."*
> - The sync tool (`tool_sync_crm_to_address_book`) works fine because it reads the resource
>   **server-side** in Python code — it never asks the model to fetch it.

### Step 0.8: Open the troubleshooting cockpit — one stream, two views

This lab is a **glass box**: every tool call narrates itself as structured JSON on the server's
**stderr** stream. There is a single log stream, but you will watch it through *two* views. Set
both up now — you will use them in every chapter to *correlate* what your client did with the
exact API calls the server ran.

> **Why one stream?** MCP's in-protocol logging (`notifications/message`) was deprecated in
> [SEP-2577](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
> (2026-07-28). New servers log to **stderr**, which the host captures automatically. This
> server follows that guidance: everything you need is on the one stderr stream — Chapter 8
> explains the full picture.

**View 1 — the client's captured server output.** Every MCP host captures the server's stderr
and surfaces it somewhere:

- **Cursor** — the *Output* panel, channel **MCP** (or the per-server log). Note Cursor tags
  every stderr line `[error]` regardless of the JSON's own `level` — that is a *channel* label,
  not the severity (Chapter 8.7).
- **Claude Desktop** — `~/Library/Logs/Claude/mcp*.log` (macOS) or `%APPDATA%\Claude\logs\mcp*.log`
  (Windows).
- **MCP Inspector** — the [official debugging UI](https://modelcontextprotocol.io/docs/tools/debugging);
  its stderr/error view shows the same stream. Launch it with
  `npx @modelcontextprotocol/inspector wxcc-mcp-server`.

**View 2 — a tailed log file.** Point the server at a log file and tail it. In your MCP client's
`env` block (or `.env`), set the file, then follow it:

```powershell
# In .env or the client's env block:
#   WXCC_LOG_FILE=C:\path\to\wxcc-mcp-server\wxcc_debug.log
#   WXCC_LOG_LEVEL=DEBUG
Get-Content .\wxcc_debug.log -Wait -Tail 20
```

Both views show the **same** structured JSON, and every line for one tool call carries the
**same** `request_id`. That shared id is how you match a client action to the exact API calls it
triggered — whether you are reading the client's captured output or your tailed file.

> **The one skill to practice:** for every step, find the `request_id` for your call, then
> grep/scan for it (`Select-String "<id>" .\wxcc_debug.log`) and note **which stages appear** —
> `tool.received` → `wxcc_api_call` → `tool.result`/`tool.error`. Which stages are present or
> absent *is* the diagnosis.

---

## 1 — Build-live: read before you write  *(hands-on)*

**Objective.** See the smallest complete MCP round-trip and confirm connectivity by listing what
already exists — before you change anything.

Reference: `src/wxcc_mcp/tools/`, `src/wxcc_mcp/resources/`, `src/wxcc_mcp/prompts/`. For how a
tool call becomes an authenticated REST call beneath these layers, see **Chapter 10 (Under the
hood)**.

### Step 1.1: Read the atomic tool `list_address_books`

Open `src/wxcc_mcp/tools/address_books.py`. Notice:

- `run_list()` accepts a validated `ListAddressBooksInput` and returns a typed
  `ListAddressBooksOutput` — Pydantic contracts, not raw JSON.
- Every mapped response field is marked `# VERIFY` so you know what to confirm against
  developer.webex.com.

#### Anatomy of an MCP tool — from bare round-trip to a shared pattern

Before you invoke anything, understand the *shape* every tool in `server.py` has. Read this
once and you've read all eighteen.

**1. The bare minimum.** Stripped of everything cross-cutting, an MCP tool is just an async
function registered with `@mcp.tool()` that maps arguments to a Webex call:

```python
@mcp.tool()
async def tool_list_address_books(org_id: str, max_results: int = 100) -> dict:
    """List address books in a WxCC organization (read-only)."""
    client = get_client()
    result = await address_books.run_list(
        client, "local-stdio-session",
        ListAddressBooksInput(org_id=org_id, max_results=max_results),
    )
    return result.model_dump(mode="json")
```

That's a complete round-trip: resolve a client, call the typed function in `tools/`, return
JSON. If the lab had one tool, this is all you'd need.

**2. The repetition problem.** But the lab has **eighteen** tools, and every one of them also
needs to: tag the call with a correlation `request_id`, time it, log `received` / `result` /
`error` to stderr, and translate a raw `WxccError` into plain language — plus every *write*
tool needs an approval gate. Copy‑pasting those ~15 lines into eighteen functions would bury
the one interesting line (the Webex call) under boilerplate, and a fix to the logging shape
would mean eighteen edits.

**3. The extracted pattern.** So that repeated machinery is pulled into one helper,
`run_tool()`, living in `src/wxcc_mcp/_runtime.py`. Each tool hands it a *deferred* call and
some labels:

```python
@mcp.tool()
async def tool_list_address_books(org_id: str, max_results: int = 100, ctx: Context = None) -> dict:
    client = get_client()
    sid = session_id(ctx)
    return await run_tool(
        lambda: address_books.run_list(client, sid, ListAddressBooksInput(org_id=org_id, max_results=max_results)),
        ctx, tool_name="list_address_books", intent=f"listing address books for org {org_id}",
    )
```

The `lambda:` matters: it *defers* the Webex call so `run_tool()` can start its timer and bind
the `request_id` **before** the work runs, then `await` it. Writes add exactly one more move —
`evaluate_write_gate(ctx, summary, confirm)` — which asks the user to approve via elicitation, and
only falls back to the explicit `confirm` flag when no one could be asked. It returns a *decision*
rather than a yes/no, so the tool can also tell the caller why a write previewed instead of
applying. This is why `server.py` reads as a flat catalogue
of tools and `_runtime.py` holds the plumbing: **read `server.py` for *what*, `_runtime.py`
for *how*.**

> **Production note.** In a production server you'd typically go one step further and collapse
> even the `run_tool(lambda: …)` wrapper into a `@wxcc_tool(...)` decorator, so each tool body
> is just the Webex call. This lab deliberately keeps the wrapper *explicit* in every tool: the
> goal is to *see* the pattern, not to hide it behind a decorator. The decorator is the natural
> DRY endpoint once the pattern is understood.

### Step 1.2: List existing address books

In your MCP client, type something like:

> **You:** Show me what address books already exist in my org.

The assistant calls `tool_list_address_books` behind the scenes, returning:

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

> **🔍 Correlate it.** Watch either view for this call — the client's captured output and the
> tailed log show the same JSON, and one `request_id` threads through every stage:
>
> ```text
> {"event":"tool.received","tool":"list_address_books","intent":"listing address books for org <ORG_ID>","request_id":"a1b2c3"}
> {"event":"wxcc_api_call","method":"GET","path":"…/address-book","request_id":"a1b2c3"}
> {"event":"tool.result","summary":"2 item(s)","elapsed_ms":312.0,"request_id":"a1b2c3"}
> ```
>
> The `wxcc_api_call` line proves the tool reached WxCC; the shared `a1b2c3` proves it belongs
> to *your* click. (Your id and timing will differ.)

### Step 1.3: Read the reference resources

Explore what reference data the server provides:

> **You:** What reference information do you have about address book rules and formatting?

Depending on your client, the assistant may read the resources automatically (Claude Code) or
you may need to attach them manually (Claude Desktop — see the client limitations callout in
Step 0.7). In MCP Inspector, switch to the **Resources** tab to browse them directly.

The server exposes two resources:

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

In your MCP client, ask:

> **You:** Create a new organization-wide address book called "Internal Directory" for our
> internal contact directory.

The assistant builds the payload and the server asks you to approve it (elicitation). Clients
that cannot show that prompt fall back to the explicit `confirm` flag and return a dry-run
preview instead. On approval you get the committed record and its new id:

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

> **🔍 Correlate it.** A write records its commit decision in the `intent` of the received
> event, then the result:
>
> ```text
> {"event":"tool.received","tool":"create_address_book","intent":"create address book 'Internal Directory' (commit=True)","request_id":"b4d9f1"}
> {"event":"wxcc_api_call","method":"POST","path":"…/address-book","request_id":"b4d9f1"}
> {"event":"tool.result","summary":"committed (9ba275fa-…)","elapsed_ms":486.0,"request_id":"b4d9f1"}
> ```
>
> Compare a **dry run** (no `confirm`): the received event's intent shows `commit=False`, the
> result summary says `dry-run preview (not committed)`, and there is **no** `wxcc_api_call` —
> nothing hit WxCC.

> **Solution.** The gate is structural: the tool builds the payload, previews it, and commits
> only after approval. Choosing `ORGANIZATION` here is a deliberate scope decision the model
> surfaces rather than hides.

---

## 3 — Day 1: add contacts manually (and meet E.164)  *(hands-on)*

**Objective.** Manually add the **3 contacts** that exist in the CRM today — the way an admin
does it on first setup. Along the way, learn why the server rejects malformed numbers *before*
they reach WxCC.

Reference: `src/wxcc_mcp/tools/entries.py`, `wxcc://reference/address-book-schema`,
`src/wxcc_mcp/resources/crm_contacts.py` (the `DAY1_CONTACTS` list). For *why* a bad number is
rejected before the network (the typed contract), see **Chapter 10.5 (Under the hood)**.

### Step 3.1: First attempt — watch validation catch a bad number

Try adding a contact with a deliberately malformed number:

> **You:** Add a contact called "Test" with phone number 05 to my Internal Directory address book.

The assistant calls `tool_create_entry` — but the server refuses with a typed validation error:

```text
Value error, Phone number '05' is not valid E.164 (e.g. +14155551234).
```

This is the schema contract doing its job: WxCC address book entries must be **E.164**
(`+` country code, then the full number). Catching it in the tool means no half-broken write
hits the API — and the assistant gets an actionable message instead of an opaque `400`.

> **🔍 Correlate it — the tell-tale *absence*.** A validation failure is rejected *before* the
> network, so the story is short:
>
> ```text
> {"event":"tool.received","tool":"create_entry","intent":"create entry 'Acme' (05) (commit=True)","request_id":"c7e2a0"}
> {"event":"tool.error","request_id":"c7e2a0","error":"…not valid E.164…"}
> ```
>
> Notice there is **no `wxcc_api_call`** for `c7e2a0`. That missing stage is the proof the typed
> contract stopped the bad write at the door. Hold this contrast — in Chapter 9 you compare it to
> a `403`, which *does* produce a `wxcc_api_call`.

### Step 3.2: Add the Day 1 baseline (3 contacts)

Now add the three real contacts. You can do them one at a time or ask the assistant to add all
three:

> **You:** Add these contacts to my Internal Directory address book:
> - Acme Corp - Reception, +14155550101
> - Globex - Support Desk, +14155550103
> - Initech - Sales, +14155550104

The assistant will call `tool_create_entry` for each (approving each write). The CRM currently
has 3 contacts — here they are with valid E.164 numbers:

| Contact | Number | CRM id |
|---------|--------|--------|
| **Acme Corp - Reception** | `+14155550101` | crm-1001 |
| **Globex - Support Desk** | `+14155550103` | crm-1003 |
| **Initech - Sales** | `+14155550104` | crm-1004 |

Each `tool_create_entry` call returns `committed: true`. Three contacts — manageable by hand.

### Step 3.3: Pause and reflect

You just added 3 contacts manually. It took a minute or two. **Now imagine doing this every
Monday** when the CRM changes — new accounts close, employees leave, vendors get new numbers.
3 becomes 7, then 20, then 50. Which ones are new? Which numbers changed? Who left?

Keep that thought. You will come back to it in Chapter 5.

> **Solution.** Validation lives in the typed input model (`CreateEntryInput`), so the assistant
> gets an actionable message and the org data stays clean. But validation alone does not solve
> the **scale** problem — doing this for 50 contacts manually every week is the real pain.

---

## 4 — Provision for agent `user2`: gated writes  *(hands-on)*

**Objective.** Make the new address book visible to a **named agent** — `user2` — on their Agent
Desktop, showing exactly who is affected before committing.

Reference: `wxcc://reference/write-safety-guide`, `src/wxcc_mcp/tools/agents.py`,
`src/wxcc_mcp/tools/desktop_profiles.py`. For how a least-privilege `403` becomes the permission
message you see here, see **Chapter 10.3 (Under the hood)**.

### Step 4.1: Find the agent and their profile

Agents inherit their address book from the **desktop profile** assigned to them, so first find
which profile `user2` uses. Ask:

> **You:** List all agents in my org and show me which desktop profile each one is assigned to.

The assistant calls `tool_list_agents` and responds:

> **Assistant:** Here are the agents in your organization:
>
> | Agent | Email | Desktop Profile |
> |-------|-------|-----------------|
> | User 1 | user1@example.com | 89dea615-… (Agent-Profile) |
> | User 2 | user2@example.com | 89dea615-… (Agent-Profile) |
> | Admin  | admin@example.com | (none assigned) |
>
> Both user1 and user2 share the same desktop profile "Agent-Profile".

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

Ask for the profile details:

> **You:** What address book is currently assigned to that Agent-Profile? And who else uses it?

The assistant calls `tool_get_desktop_profile` (or `tool_map_profiles_to_agents`) and responds:

> **Assistant:** Desktop Profile "Agent-Profile" (89dea615-…):
> - Current address book: "AB" (87ac75ea-…)
> - Assigned agents: user1, user2
>
> Note: changing the address book on this profile will affect **both** agents.

Note two things before you write:

- "Agent-Profile" currently points at the **"AB"** address book — assigning ours **replaces** it.
- **`user1` shares the same profile**, so they will see the new contacts too.

This is the real-world caveat: profiles are shared, so a "make one agent see it" request can
affect several. Surface it, don't hide it.

### Step 4.3: Assign the address book and approve

Now make the change:

> **You:** Assign my "Internal Directory" address book to the Agent-Profile so user2 can see
> the contacts on their Agent Desktop.

The assistant calls `tool_assign_address_book_to_profile` and (via elicitation or dry-run)
asks for confirmation:

> **Assistant:** I'll assign "Internal Directory" (9ba275fa-…) to Agent-Profile (89dea615-…).
>
> ⚠️ This will **replace** the current address book "AB" and affect 2 agents:
> - user1@example.com
> - user2@example.com
>
> Should I proceed?

> **You:** Yes, go ahead.

The committed profile reflects the change:

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

Confirm it worked:

> **You:** Show me the Agent-Profile now — confirm it points to the right address book.

> **Assistant:** Verified. Agent-Profile (89dea615-…) now has addressBookId: 9ba275fa-…
> ("Internal Directory"). The change is live.

When `user2` next logs into the Agent Desktop, the Day 1 contacts appear in their address
book — and, as noted, so will they for `user1`.

> **Solution.** Safety is structural, not advisory: every write is gated by elicitation with a
> `confirm=True` dry-run fallback, tokens are never returned to the model, the assignment
> preserves unrelated fields, and the shared-profile impact is made explicit before commit.

**Day 1 is complete.** The address book works. Agents can see contacts. Everything is correct
— *today*. Now fast-forward one week.

---

## 5 — Monday morning: the CRM drifted  *(hands-on)*

**Objective.** See what happens when the CRM changes over a week — and feel the friction of
resolving it manually.

Reference: `src/wxcc_mcp/resources/crm_contacts.py` (`crm://contacts`).

### Step 5.1: Read the CRM resource

Ask the assistant what the CRM currently holds:

> **You:** What contacts does the CRM have right now? Show me the full list.

The assistant reads the `crm://contacts` resource (or, if your client doesn't surface resources
automatically, you can ask: *"Read the crm://contacts resource for me"*). It now shows
**6 contacts** — not the 3 you added on Day 1. What changed?

> **Troubleshooting — "I'd need a CRM connector (HubSpot, Zoho, etc.)"**
>
> If the assistant responds with something like *"I'd need one of the actual CRM connectors —
> none are connected yet"* instead of showing contacts, the model is **not reaching the
> `crm://contacts` resource**. This is a known Claude Desktop limitation (see Step 0.7), not
> a server bug. The server registered the resource correctly; the client simply does not wire
> `resources/read` into the model's callable surface.
>
> **Quick check — Claude Desktop Settings UI:**
>
> 1. Open **Settings → Developer** and click the **wxcc** server entry.
> 2. Confirm `crm://contacts` appears under **PROVIDED RESOURCES**.
> 3. If it is listed, the server is connected and working — the issue is client-side only.
>
> **Fix it — attach the resource manually:**
>
> In the Claude Desktop input area, click the **+** (attachment) button → select
> `crm://contacts` from the resource list → then ask your question again. The model will now
> see the resource content in context.
>
> **Definitive verification — MCP Inspector (no LLM involved):**
>
> MCP Inspector connects directly to your server over stdio and lets you browse tools,
> resources, and prompts independently of any AI client.
>
> 1. Open a **new terminal** (keep your client running in the other one).
>
> 2. Launch Inspector:
>
>    ```powershell
>    npx @modelcontextprotocol/inspector
>    ```
>
> 3. Inspector opens a browser UI (typically `http://localhost:6274`). In the connection
>    form set:
>
>    - **Transport:** `STDIO`
>    - **Command:** the full path to your server executable, e.g.
>      `C:\path\to\wxcc-mcp-server\.venv\Scripts\wxcc-mcp-server.exe`
>      (or `python -m wxcc_mcp.server`)
>    - **Arguments:** leave empty
>    - **Environment Variables:** add any needed vars from your `.env`
>      (`WXCC_ORG_ID`, `WXCC_ACCESS_TOKEN`, `WXCC_TOKEN_ENCRYPTION_KEY`)
>
> 4. Click **Connect**. The left sidebar should populate with three tabs:
>    **Tools**, **Resources**, **Prompts**.
>
> 5. Switch to the **Resources** tab. You should see:
>    - `crm://contacts`
>    - `wxcc://reference/address-book-schema`
>
> 6. Click `crm://contacts` → **Read Resource**. Inspector displays the JSON payload
>    with 6 contacts. This confirms the server is serving the resource correctly.
>
> If Inspector shows the resource but Claude Desktop does not surface it to the model,
> the server is working as intended — use the manual-attach workaround above or continue
> with Inspector for this step.

| Change | Contact | Detail |
|--------|---------|--------|
| **Same** | Acme Corp - Reception | unchanged |
| **NEW** | Acme Corp - Billing | new department contact appeared |
| **UPDATED** | Initech - Sales | number changed: `+14155550104` → `+14155550184` |
| **NEW** | Umbrella - Escalations | new partner |
| **NEW** | Soylent - Accounts | new customer |
| **NEW** | Hooli - Partner Line | new vendor |
| **REMOVED** | Globex - Support Desk | left the partner program (absent from CRM) |

> **How do CRM contacts know which address book to sync into?**
>
> They don't — and that is by design. The `crm://contacts` resource is a flat list of contacts
> (id, name, number) with no address-book assignment, just like a real CRM export. The binding
> happens when you invoke `sync_crm_to_address_book` and pass the `address_book_id` parameter.
> The tool reads the global CRM list, reads the specified address book's current entries, and
> diffs them. The *caller* (you, via the model) decides the target — the CRM data itself has
> no opinion about where it lands.

### Step 5.2: Count the manual work

To bring the address book in line with the CRM, you would need to:

1. **Add 4 entries** — Acme Billing, Umbrella, Soylent, Hooli (format each as E.164, call
   `create_entry` four times, approve each)
2. **Update 1 entry** — find Initech's entry id, call `update_entry` with the new number
3. **Delete 1 entry** — find Globex's entry id, call `delete_entry`, approve the deletion

That is **6 discrete actions** with lookups, validations, and approvals — for a week with modest
changes. In a real org with 200+ contacts and weekly partner-roster churn, this is 30–60 minutes
of tedious, error-prone work **every single Monday**.

### Step 5.3: Ask yourself

> *Would you do this by hand every week? What about when you're on vacation — does it just
> drift until agents start dialling wrong numbers?*

This is the problem the sync tool solves. One command. Let's see it.

---

## 6 — The sync: one command resolves the drift  *(instructor-run demo)*

**Objective.** Watch a single tool call do everything you just counted in Chapter 5 — with a
preview, approval, and per-entry progress — in seconds.

Reference: `src/wxcc_mcp/tools/sync.py`, `crm://contacts`,
`wxcc://reference/write-safety-guide`.

### Step 6.1: Preview the sync (dry-run)

The instructor asks:

> **Instructor:** Sync my CRM contacts into the Internal Directory address book — but show me
> what would change first, don't commit yet.

The assistant invokes `tool_sync_crm_to_address_book` without approval / as a dry-run. The
tool reads `crm://contacts`, compares it to the current address book entries, and returns a
preview:

```json
{
  "dry_run": true,
  "preview": {
    "to_create": 4,
    "to_update": 1,
    "to_delete": 1,
    "unchanged": 1
  }
}
```

That matches exactly what you counted by hand in Step 5.2 — but the tool did the diff for you
in milliseconds.

### Step 6.2: Understand the diff logic

`sync.compute_diff` is a **pure function** — no I/O, no side effects. It takes the CRM
contacts and the existing address book entries and classifies each into one of four actions:

| CRM contact vs. existing entry | Action |
|---|---|
| No match found | **create** — new entry needed |
| Match found, name or number differs | **update** — field changed |
| Match found, identical | **skip** — already in sync |
| Entry exists but absent from CRM | **delete** (only if `prune=True`) |

Matching uses two tiers: **CRM id first**, then **normalized E.164 number**. The two-tier
strategy handles entries originally added manually (no CRM id) that still match on phone
number. Pruning — deleting entries absent from the CRM — is **off by default** because
removing contacts is higher risk than adding them; you must pass `prune=True` explicitly.

### Step 6.3: Approve and apply

> **💡 What is Elicitation?**
>
> Before applying any change, the MCP server **asks you for permission** via a mechanism
> called *elicitation*. Think of it as a consent dialog — the server cannot write anything
> until you explicitly approve.
>
> ```
> ┌─────────────── Your MCP Client (Codex, Claude Desktop, etc.) ───────────────┐
> │                                                                              │
> │  Server says: "Confirm write action: sync CRM → Internal Directory          │
> │               (4 creates, 1 update, 1 delete)"                              │
> │                                                                              │
> │                     [Accept]          [Decline]                              │
> │                                                                              │
> └──────────────────────────────────────────────────────────────────────────────┘
> ```
>
> - **Accept** → the server commits the changes. Clicking Accept *is* the approval; there is
>   no checkbox to tick and no field to fill in. The server reads only which button you
>   pressed, never what the form contained.
> - **Decline / Cancel** → the server returns a dry-run only; nothing is modified. A refusal
>   is final — it cannot be overridden by any tool argument.
> - **Client can't show the dialog** → the tool falls back to the explicit `confirm`
>   parameter, which defaults to `False` (a safe dry-run).
>
> **You don't need to ask the assistant to pass `confirm=True`.** The server requests your
> approval on every write, so simply calling the tool triggers the prompt. `confirm` exists
> only for clients that cannot prompt at all — scripts and tests. This matters because
> assistants often play it safe and pass `confirm=False`; that must not be able to cancel a
> write you approved, and it can't.
>
> This is a **human-in-the-loop safety gate** — one of MCP's design principles. The server
> never mutates data silently. Different clients render this dialog differently: Claude Desktop
> shows an inline approval card; Codex shows a popup; MCP Inspector shows a form. The
> mechanism is the same — your click is the gate.
>
> **Where the trust boundary sits.** *Requesting* consent is the server's job; *showing* the
> request is the client's. The protocol cannot force a client to display anything, so a
> client could in principle answer on your behalf without ever drawing a dialog. That is why
> the next section matters: don't infer what happened from whether a popup appeared — read
> the server's own record of the decision.

> **🔍 Read the decision, don't guess it.** Every write emits one `write_gate` line recording
> how the gate resolved, so you never have to infer consent from whether anything changed:
>
> ```text
> {"event":"write_gate","outcome":"accepted","action":"sync CRM into address book 9ba275fa-…","committed":true,"elicit_ms":4820.5,"client":"Cursor 1.7","request_id":"f0a3c9"}
> ```
>
> `outcome` is most of the story, and the five values are deliberately distinct:
>
> | `outcome` | What it means | `committed` |
> |---|---|---|
> | `accepted` | You approved the prompt | `true` |
> | `declined` | You refused it | `false` |
> | `cancelled` | **Ambiguous** — you dismissed it, *or* the client gave up on its own | `false` |
> | `unsupported` | The client never offered elicitation, so it fell back to `confirm` | value of `confirm` |
> | `error` | The prompt failed; `reason` says why, and it fell back to `confirm` | value of `confirm` |
>
> The distinction between `declined` and `unsupported`/`error` is the point. All three can
> produce a dry-run, but only the first one means *you* said no.
>
> `cancelled` is the one value you cannot read on its own. The specification defines it as
> "dismissed without choosing", but clients also emit it to report their *own* timeouts and
> internal faults. Three companion fields settle it:
>
> - **`elicit_ms`** — how long the client took. Seconds means a human was deciding; a few
>   milliseconds means the client answered by itself.
> - **`client_detail`** — the reason the client attached, when it attached one. A
>   `"Timeout: elicitation cancelled"` here is the client confessing, not you refusing.
> - **`client`** — which client and build answered, so a report from one attendee's setup
>   stays distinguishable from everyone else's.
>
> Only refusals carry `client_detail`. An approval's response body can contain text you typed,
> so it is never logged.

The instructor approves:

> **Instructor:** Looks good — go ahead and apply those changes.

On approval the tool applies the plan, streaming **progress** per entry (an MCP
`notifications/progress` update) and emitting a `sync.entry` event per change to the server log.
In seconds the address book is fully reconciled:

- 4 new entries created (with correct E.164, no manual formatting)
- 1 number updated (Initech)
- 1 stale entry removed (Globex) — only because `prune=True` was explicit

Optionally (with `summarize=True` and a sampling-capable client) the tool adds a
natural-language **summary** of the result — with a deterministic fallback when sampling is
unavailable.

> **🔍 Correlate it — one id, many stages.** The composite sync shares a single id across the
> whole operation, so you can watch it read, then apply each change — every line inherits
> `f0a3c9` from contextvars:
>
> ```text
> {"event":"write_gate","outcome":"accepted","committed":true,"request_id":"f0a3c9"}  ← your click
> {"event":"tool.received","tool":"sync_crm_to_address_book","intent":"sync CRM into address book 9ba275fa-… (commit=True)","request_id":"f0a3c9"}
> {"event":"wxcc_api_call","method":"GET","path":"…/entry","request_id":"f0a3c9"}
> {"event":"wxcc_api_call","method":"POST","path":"…/entry","request_id":"f0a3c9"}  ← ×4 creates
> {"event":"sync.entry","detail":"create: Acme Corp - Billing (+14155550102)","request_id":"f0a3c9"}  ← per-entry
> {"event":"tool.result","summary":"4 create / 1 update / 1 delete","elapsed_ms":1243.0,"request_id":"f0a3c9"}
> ```
>
> Count the `wxcc_api_call` lines for `f0a3c9`: one read plus one write per change. The single id
> turns a multi-step operation into one auditable trace. (Per-entry **progress** still streams to
> the client as `notifications/progress`; the per-entry *log* is the `sync.entry` event above.)

### Step 6.4: What you just saw

Think about what happened in this single tool call:

- **Read** the CRM source (the `crm://contacts` resource)
- **Read** existing address book entries (via `tool_list_entries`)
- **Diffed** by stable CRM id and E.164 — matching, classifying, deciding
- **Previewed** the plan with exact counts — nothing hidden
- **Applied** creates, updates, and deletes with per-entry progress
- **Logged** every change to the client for auditability
- **Gated** the entire operation behind approval

With raw APIs, that is 6+ calls, a hand-written diff, E.164 normalization, error handling for
each, and no preview or undo path. The MCP server encoded all of that **once** — and now any
admin, any Monday, resolves a week of drift in one sentence.

> **Solution.** The value is not the single sync. It is **every future sync** — by any admin,
> at any scale, with full observability — that now takes 30 seconds instead of 30 minutes.

---

## 7 — Going further  *(instructor-run demo)*

- **Sampling.** The sync tool can ask the client's model to summarize the result
  (`ctx.session`), guarded by a capability check — optional, with a deterministic fallback.
- **Debugging.** Set `WXCC_LOG_FILE` (and `WXCC_LOG_LEVEL=DEBUG`) in the client's `env` block to
  capture structured JSON logs with secrets redacted. Tail with
  `Get-Content <file> -Wait -Tail 20`. See the **Troubleshooting playbook** below for how to
  read the stream and correlate stages by `request_id`.
- **Avoid deprecation.** The server targets **Address Book v2** and never uses the deprecated
  Desktop Profile dial-plan fields — check API lifecycles before going live.
- **Go live.** Resolve every `# VERIFY` / `# TODO` (base URL, OAuth endpoints, scopes, endpoint
  paths, response field mappings) against
  [developer.webex.com](https://developer.webex.com). See the README's VERIFY/TODO checklist.
- **Extend the narrative.** New tools slot into the same pattern: typed IO, structured logging,
  and — for writes — the elicitation/dry-run gate. **Chapter 10 (Under the hood)** walks the
  `api/` + `client.py` + `auth/` + `config/` layers a new tool builds on.

---

## 8 — Understanding MCP server logging  *(reference / self-study)*

**Objective.** Understand the logging architecture inside this MCP server — why it logs to
**stderr** rather than over the MCP protocol, how the structured stream is built, and the
different kinds of output you see — so you can extend or debug the server with confidence.

Reference: [MCP debugging guide](https://modelcontextprotocol.io/docs/tools/debugging),
[SEP-2577 (deprecate logging)](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging),
`src/wxcc_mcp/logging_config.py`, `src/wxcc_mcp/_runtime.py` (`run_tool`).

### 8.0: Where does MCP logging live — client or server?

If you are troubleshooting an MCP server for the first time, the natural question is: do I
look at the **client** (Claude Desktop, Cursor, Inspector) or the **server** (your Python
process)?

The short answer: **the server produces all observability; the client just captures and
displays it.** The server decides *what* to log, *how* to correlate it, and *what to redact*.
The client's only job is to capture the server's stderr stream (because it spawned the server
as a child process) and surface it in a UI — a log tab, a file, a panel.

```text
  ┌────────────────────────────────┐        ┌────────────────────────────────┐
  │      MCP SERVER (yours)        │        │      MCP CLIENT (host)         │
  │                                │        │                                │
  │  Produces:                     │        │  Consumes:                     │
  │  • Structured JSON on stderr   │─stderr─▶  • Displays in logs tab       │
  │  • Correlation IDs             │        │  • Writes to mcp*.log          │
  │  • Secret redaction            │        │  • (No filtering or transform) │
  │  • Event lifecycle             │        │                                │
  │  • Level filtering             │        │  Also sees:                    │
  │                                │        │  • Protocol messages (JSON-RPC)│
  │  Controls:                     │        │  • Tool results (content)      │
  │  • What is logged              │        │  • Connection lifecycle         │
  │  • What is redacted            │        │                                │
  │  • The log level threshold     │        │                                │
  └────────────────────────────────┘        └────────────────────────────────┘
```

| If you want to… | Look at… |
|---|---|
| Debug why a tool failed | Server logs (stderr or `WXCC_LOG_FILE`) |
| Trace an API call end-to-end | Server logs (grep by `request_id`) |
| See what the LLM received back | Client UI (conversation view) |
| Verify the server started | Either (client shows stderr; server writes it) |
| Monitor production health | Server side (structured JSON, alertable) |
| Understand the protocol conversation | Client side (JSON-RPC request/response) |

**Why not in-protocol?** MCP *used* to let servers push log events to the client through the
protocol itself (`notifications/message`). That was deprecated in 2026 (§8.1 explains why).
The modern model is simpler: **stderr IS the log**. The host captures it. End of story.

This means your debugging workflow is always:

1. **Set `WXCC_LOG_LEVEL=DEBUG`** (or `INFO` for less noise)
2. **Optionally set `WXCC_LOG_FILE`** so you can grep a persistent file
3. **Read the stderr stream** — either in your client's logs tab or by tailing the file
4. **Grep by `request_id`** to correlate a single tool call across all stages

The rest of this chapter explains *how* that stream is built (§8.2), *what* is redacted
(§8.3), *how* correlation works (§8.4), and *where* the client surfaces it (§8.5).

### 8.1: MCP protocol logging — deprecated, and why this server doesn't use it

MCP *used* to define logging as a first-class protocol primitive with two messages:

- **`notifications/message`** (server → client) — the server pushes a log entry to the client,
  carrying a `level` (severity), an optional `logger` name, and a `data` payload.
- **`logging/setLevel`** (client → server) — the client tells the server the minimum severity
  it wants to receive.

In the SDK this surfaced as `ctx.info(...)` / `ctx.warning(...)` / `ctx.error(...)` inside a
tool, which the framework translated into a JSON-RPC notification on the transport.

**This capability is now deprecated.** [SEP-2577](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
(Final) deprecated protocol-level logging in the **2026-07-28** version of the MCP
specification. Key points:

- Existing connections to clients on *earlier* protocol versions still work, but on current
  versions calling these methods emits an **`MCPDeprecationWarning`**.
- **New servers should not use in-protocol logging.** They should log with Python's `logging`
  module (or a structured wrapper like structlog) to **stderr**, which the host captures
  automatically — no MCP round-trip required. `MCPServer` even configures a stderr handler at
  whatever `log_level` you pass its constructor, so logs from inside a tool land in the right
  place on their own.

Accordingly, **this server does not call `ctx.info`/`warning`/`error` at all.** It previously
bridged each tool stage to the client via helpers called `_emit_log`/`_glass_log`; those have
been removed. Everything you need is on the single stderr stream described next, and the tool
lifecycle is fully observable there (§8.4).

The old severity model still matters, because the stderr stream tags each event with a level.
MCP followed [RFC 5424](https://datatracker.ietf.org/doc/html/rfc5424#section-6.2.1) severities;
this server uses four of them:

| Level | Description | Used by this server? |
|-------|-------------|----------------------|
| `debug` | Detailed debugging info | Yes — e.g. `wxcc_mcp_server_starting` |
| `info` | Informational messages | Yes — tool received/result, API calls, `sync.entry` |
| `notice` | Normal but significant | No |
| `warning` | Warning conditions | Yes — tool errors (non-fatal) |
| `error` | Error conditions | No (translated tool failures log at `warning`) |
| `critical` | Critical conditions | No |
| `alert` | Action needed immediately | No |
| `emergency` | System is unusable | No |

Most tool activity is logged at `info`; handled tool failures at `warning`.

### 8.2: Server-side structured logging — structlog and JSON (the stderr-native model)

This is the **recommended replacement** for protocol logging and the server's single source of
truth: a structured JSON stream on **stderr** (and optionally a log file). It is exactly what
your MCP host captures and what you tail in the cockpit (Step 0.8).

The server uses [structlog](https://www.structlog.org/) to produce structured JSON on stderr
(and optionally a log file). The configuration lives in `logging_config.py` and sets up a
five-stage processor chain:

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # 1. inject request_id, tool name
        structlog.processors.add_log_level,        # 2. stamp the severity level
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # 3. ISO 8601 timestamp
        _redact,                                   # 4. scrub secrets
        structlog.processors.JSONRenderer(),        # 5. serialize to JSON
    ],
    wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
    logger_factory=structlog.PrintLoggerFactory(file=log_stream),
    cache_logger_on_first_use=True,
)
```

Each stage transforms the log event in order:

1. **`merge_contextvars`** — copies any values stored in the current async context (like
   `request_id` and `tool`) into the event dict. This is how a single correlation id appears
   on every log line for a given tool invocation without being passed explicitly.
2. **`add_log_level`** — adds the `"level"` field (`debug`, `info`, etc.).
3. **`TimeStamper`** — adds a UTC ISO 8601 timestamp.
4. **`_redact`** — scrubs secrets (see below).
5. **`JSONRenderer`** — serializes the event dict to a single JSON line.

**The level filter** is set by `make_filtering_bound_logger(numeric_level)`, where
`numeric_level` comes from `WXCC_LOG_LEVEL` in `.env`. When you set `WXCC_LOG_LEVEL=DEBUG`,
the filter passes everything from DEBUG upward. When set to `INFO`, debug-level records are
silently dropped before they reach the processor chain.

**The output target** is `PrintLoggerFactory(file=log_stream)`. When `WXCC_LOG_FILE` is set,
`log_stream` is a `_TeeStream` that writes each line to **both** stderr and the log file
simultaneously — same JSON, same redaction, two destinations.

### 8.3: Secret redaction

The `_redact` processor runs on every log event before it is serialized. It checks each
top-level key against a set of sensitive names:

`authorization`, `access_token`, `refresh_token`, `token`, `client_secret`,
`token_encryption_key`, `bearer`, `password`, `secret`

Any matching value is replaced with `***REDACTED***`. If the event contains a `headers` dict
(common in HTTP logging), the same check runs on each header key.

This means secrets **never** appear in the log stream — the same redacted JSON goes to stderr
and to `WXCC_LOG_FILE`, so neither your tailed file nor the client's captured output ever
carries raw token material.

### 8.4: Correlation — one id threads through everything

Every tool invocation gets a unique **correlation id** — 6 hex characters generated by
`secrets.token_hex(3)` (e.g. `a1b2c3`). The orchestration happens in `run_tool` (in
`src/wxcc_mcp/_runtime.py`):

```python
request_id = request_id or new_request_id()                 # 1. generate "a1b2c3"
tokens = bind_request_context(request_id=request_id, tool=tool_name)  # 2. bind to contextvars
logger.info("tool.received", tool=tool_name, intent=intent) # 3. structured stderr event
try:
    result = await coro_factory()                            # 4. execute the tool
    logger.info("tool.result", tool=tool_name, summary=summary, elapsed_ms=elapsed_ms)
except ...:
    logger.warning("tool.error", tool=tool_name, error=message, elapsed_ms=elapsed_ms)
finally:
    reset_request_context(tokens)                            # 5. clean up contextvars
```

Notice there is **no** client-facing emit — every stage is a plain `logger.*` call to the
stderr-native stream. That is the SEP-2577 pattern in practice.

The `request_id or …` in step 1 is what lets a **write** tool mint the id *before* its approval
gate runs and pass the same one to both, so the `write_gate` line and the tool's lifecycle share
a trace (§8.7).

Step 2 is the key: `bind_request_context` stores the `request_id` in a Python
[`contextvar`](https://docs.python.org/3/library/contextvars.html). Because
`merge_contextvars` is the first processor in the structlog chain, **every** `logger.info()`
or `logger.debug()` call made anywhere downstream — in the API client, the auth broker, the
tool implementation — automatically gets `request_id` stamped into its JSON without anyone
passing it as an argument. That is how a single id threads through an entire multi-step
operation and makes the server log file greppable:

```powershell
Select-String "a1b2c3" .\wxcc_debug.log
```

### 8.5: How the host captures stderr — one stream, two views

Because the server writes to stderr (not the MCP protocol), you never build a "bridge" to the
client — the **host does it for you**. When your MCP client launches the server as a stdio
subprocess, it captures the process's stderr and surfaces it. So the *same* JSON line appears
both in your tailed `WXCC_LOG_FILE` and in whatever your client shows:

| Client | Where captured stderr appears |
|---|---|
| **Cursor** | *Output* panel → **MCP** channel (or the per-server log). Every line is tagged `[error]` — that is the channel, not the severity (see §8.7). |
| **Claude Desktop** | `%APPDATA%\Claude\logs\mcp*.log` (Windows) or `~/Library/Logs/Claude/mcp*.log` (macOS). |
| **MCP Inspector** | The stderr/error view of the [Inspector](https://modelcontextprotocol.io/docs/tools/debugging). (Its old *Notifications* pane showed `notifications/message` — now unused, so it stays empty for this server.) |

That is the whole "two views" idea in Step 0.8: **one** stderr stream, read either from the
client's capture or from your own tailed file. No duplicate formatting path, no protocol
round-trip, and — thanks to `request_id` — still perfectly correlatable:

```text
{"event":"tool.received","tool":"list_address_books","intent":"…","request_id":"a1b2c3"}
{"event":"wxcc_api_call","method":"GET","path":"…/address-book","request_id":"a1b2c3"}
{"event":"tool.result","summary":"2 item(s)","elapsed_ms":312.0,"request_id":"a1b2c3"}
```

### 8.6: The third stream — stdlib and third-party libraries

If you watch the server's stderr output closely, you will notice lines that are **not**
structured JSON:

```text
Processing request of type ListResourcesRequest
Processing request of type CallToolRequest
HTTP Request: GET https://api.wxcc-us1.cisco.com/... "HTTP/1.1 200 OK"
```

These come from **third-party libraries** — the MCP SDK framework and httpx (the HTTP client)
— which use Python's built-in `logging` module, not structlog. The line in `configure_logging`
that enables them is:

```python
logging.basicConfig(format="%(message)s", level=numeric_level, stream=sys.stderr)
```

This sets the **stdlib root logger** threshold to `numeric_level`. When `WXCC_LOG_LEVEL=DEBUG`,
every library that calls `logging.debug(...)` will dump to stderr alongside your structured
JSON.

These plain-text lines are:

- **Not structured** — no JSON, no consistent field names
- **Not redacted** — the `_redact` processor only runs in the structlog chain
- **Not correlated** — no `request_id`, no way to match them to a specific tool invocation

They are a side effect of sharing a log level across all of Python's logging. Raising
`WXCC_LOG_LEVEL` to `INFO` silences most of them; setting it to `DEBUG` lets everything
through.

### 8.7: "Why does it say `info` when I set the level to `DEBUG`?"

A common source of confusion. When you see this in the log file:

```json
{"tool":"list_address_books","event":"tool_invoked","level":"info","timestamp":"…"}
```

…you might wonder: "I set `WXCC_LOG_LEVEL=DEBUG` — why does this line say `info`?"

The answer: the `"level"` field in the JSON reflects the **severity the developer chose** when
writing `logger.info(...)`. The `WXCC_LOG_LEVEL` setting controls the **filter threshold** —
which levels are allowed through. These are independent:

- `WXCC_LOG_LEVEL=DEBUG` means: pass everything at `DEBUG` or above (i.e., everything).
- The code calls `logger.info("tool_invoked", ...)` because tool invocations are operationally
  significant — you would want them in a production log even at `INFO` level.
- `logger.debug(...)` is reserved for internal plumbing (like `wxcc_mcp_server_starting`).

The filter decides **what passes**. The code decides **what level to tag it as**. Both are
correct and intentional.

**A related trap — the `[error]` channel label.** In Cursor, *every* captured line shows up in
the Output panel prefixed `[error]`, even a cheerful `"level":"info"` event. That prefix is
Cursor labelling the **channel** (stderr is conventionally the diagnostic channel), not reading
your JSON's severity. So there are really *three* independent notions of "level" to keep
straight:

1. **`WXCC_LOG_LEVEL`** — the filter threshold (what gets written at all).
2. **`"level"` in the JSON** — the severity the developer chose for that event.
3. **The client's channel label** (e.g. Cursor's `[error]`) — just "this came from stderr".

Don't panic when the Output panel is full of `[error]` lines: open one and read its JSON
`level`.

### 8.8: One filter now — recap

Protocol logging is gone, so `logging/setLevel` no longer applies to this server. There is a
**single** log-level control:

| Filter | What it controls | How to change it |
|--------|------------------|------------------|
| Server-side (`WXCC_LOG_LEVEL`) | What is written to stderr and `WXCC_LOG_FILE` (and therefore what your client captures) | Set in `.env` / the client's `env` block (takes effect at startup) |

If the stream looks too quiet, lower `WXCC_LOG_LEVEL` to `DEBUG`; if it is too noisy, raise it
to `INFO`. Whatever passes the filter is what *both* views (client capture and tailed file)
show — there is no separate client-side threshold to reconcile any more.

> **Further reading.**
> - Deprecation of protocol logging (SEP-2577): <https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging>
> - MCP debugging guide: <https://modelcontextprotocol.io/docs/tools/debugging>

---

## 9 — Troubleshooting playbook: read the stream by `request_id`  *(reference)*

**Objective.** Turn "it failed" into a diagnosis by scanning the stderr stream for one
`request_id`. The trick is not any single line — it is **which stages are present or absent**
for a given id.

Reference: [MCP debugging guide](https://modelcontextprotocol.io/docs/tools/debugging),
`src/wxcc_mcp/_runtime.py` (`run_tool`), `src/wxcc_mcp/api/client.py`. This chapter reads the
*symptoms*; **Chapter 10 (Under the hood)** shows the code that produces each stage.

### One log-level filter

Since protocol logging was retired (§8.1), there is a **single** level control — no separate
client-side threshold to reconcile:

| Filter | Controls | Set via |
|---|---|---|
| Server-side level | What is written to stderr / `WXCC_LOG_FILE` (and therefore what your client captures) | `WXCC_LOG_LEVEL` (startup-time) |

Whatever passes `WXCC_LOG_LEVEL` is what both views show. If the stream looks quiet, lower it to
`DEBUG`; if it is noisy, raise it to `INFO`.

### Scenario matrix

Each scenario is the same drill: pick the `request_id` for your call, scan for it
(`Select-String "<id>" .\wxcc_debug.log`), and note which stages appear.

| # | Scenario | Terminal event | Stages for that id | The tell |
|---|---|---|---|---|
| A | **Happy read** | `tool.result` (`summary: N item(s)`) | `tool.received` → `wxcc_api_call` → `tool.result` | full chain present |
| B | **Missing/expired token** | `tool.error` (`Not authorized: complete the Webex OAuth sign-in`) | `tool.received` → `tool.error` | **no** `wxcc_api_call` — failed before the network |
| C | **Permission denied (403)** | `tool.error` (`Permission denied … ask an administrator`) | `tool.received` → `wxcc_api_call` → `tool.error` | `wxcc_api_call` **present** — request left the server, WxCC refused |
| D | **E.164 validation** | `tool.error` (`… not valid E.164`) | `tool.received` → `tool.error` | **no** `wxcc_api_call` — typed contract rejected it |
| E | **Rate limited (429)** | `tool.result` after a pause (or `tool.error` if exhausted) | `wxcc_api_call` → `wxcc_api_retry` → `wxcc_api_call` | `wxcc_api_retry` line(s) present |
| F | **"I approved but nothing changed"** | `tool.result` (`summary: dry-run preview (not committed)`) | `write_gate` → `tool.received` → `tool.result` | read `write_gate.outcome` — see below |

### Scenario F: approved, but it came back a dry-run

A dry-run after you clicked Accept has several very different causes, and the `write_gate`
line names which one. Find it by `request_id`, then read `outcome`:

| `outcome` | Diagnosis | What to do |
|---|---|---|
| `declined` | The server received an explicit refusal | You answered no — re-run and accept |
| `cancelled` | **Ambiguous.** Read `elicit_ms` and `client_detail` first | See below |
| `unsupported` | The client never negotiated elicitation, so nothing was ever asked. It fell back to `confirm`, which defaulted to `False` | Use a client that supports elicitation, or pass `confirm=True` deliberately |
| `error` | The prompt was attempted and failed; `reason` carries the exception | Read `reason` — a transport or client-side fault, not a permissions problem |
| `accepted` with `committed: true` | Consent was fine; the dry-run came from somewhere else | Look past the gate — check `tool.received`'s `intent` and the API stages |

**Splitting a `cancelled`.** The action alone cannot tell a dismissal from a client that gave
up, so use the two companion fields:

```text
{"event":"write_gate","outcome":"cancelled","elicit_ms":3.1,"client_detail":"Timeout: elicitation cancelled","client":"some-client 1.4"}
```

`elicit_ms` of `3.1` is nobody's decision — that is the client answering on its own, and
`client_detail` says so outright. A dismissal you actually performed looks like `elicit_ms`
in the thousands with no `client_detail`. If the fields point at the client, the fault is in
its elicitation handling, not in the server or your permissions; note the `client` value and
report it upstream.

A quiet variant is worth knowing because a lab machine may hit it. If you saw **no dialog at
all** and the event carries a low `elicit_ms` with *no* `client_detail`, the client declared
elicitation support during the handshake and then cancelled the request itself — it never
asked you. That is indistinguishable from a real dismissal from the protocol's point of view,
which is why the tool's response says the prompt may not have appeared rather than offering
you a way to retry. Codex `codex-mcp-client 0.149.0-alpha.4.1` is the known build with this
behaviour, observed cancelling in as little as 3ms. There is no server-side workaround; use a
client that completes the elicitation round-trip.

**If your client cannot prompt at all.** Some clients never negotiate elicitation, so there is
no dialog to click and the gate resolves `unsupported` every time. The tool's own response says
so and tells you what to do — it comes back with `gate_outcome: "unsupported"` and a `next_step`
asking for `confirm=true`. This is the one case where passing `confirm` is correct: nobody could
be asked, so the flag is the only approval path there is. It cannot be used to slip past someone
who refused, because a `declined` or `cancelled` outcome ignores it.

Note the trap all of this replaces: an approval that produced no change used to be
indistinguishable from a refusal, because both simply returned a preview. The `outcome` field
exists precisely so consent failures cannot hide as "nothing happened".

### Read it like a detective

- **B vs D look identical in shape** (both end in `tool.error` with no API stage) but differ in
  the `error` message — one is an auth problem, the other a data problem. Fix the cause, not the
  symptom.
- **C vs D is the key contrast:** both end in `tool.error`, but C has a `wxcc_api_call` and D
  does not. That single line tells you whether the request ever reached WxCC — the difference
  between a *permissions* fix (ask an admin for scope) and a *data* fix (correct the phone
  number).
- If a tool call in your client produced **no `tool.received` at all**, the failure is in the
  client/transport, not the tool — check the MCP debugging guide's connection-problems checklist.

---

## 10 — Under the hood: from tool call to authenticated REST call  *(reference / self-study)*

**Objective.** Follow one tool call — `list_address_books` — all the way down through the
server's layers and back, so you can see *how a tool becomes an authenticated Webex REST call*,
*how a failure becomes the plain-language message the glass box shows*, and *where every
external identifier and token lives*. Chapters 8–9 taught you to read the **symptoms** in the
log stream; this chapter shows the **code that produces them**.

Reference: `src/wxcc_mcp/api/` (`address_books.py`, `client.py`), `src/wxcc_mcp/auth/oauth.py`,
`src/wxcc_mcp/config.py`, `src/wxcc_mcp/errors.py`, `src/wxcc_mcp/models/schemas.py`.

> **How to read this chapter.** It is **optional** for the timed hands-on run (Chapters 1–6)
> and written for *two* readers at once. **Operator** callouts tell you *what a broken layer
> looks like and where to look*; **Builder** callouts tell you *the pattern to reuse if you were
> writing this server*. Read whichever half serves you — or both.

The server is a six-layer onion. A single tool call falls straight down it and the result (or a
typed error) climbs back up:

```text
   MCP client  (Cursor / Claude / Inspector)
        │  "list address books for org X"
        ▼
┌──────────────────────────────────────────────────────────────┐
│ server.py        @mcp.tool / @mcp.resource / @mcp.prompt       │  the MCP surface
├──────────────────────────────────────────────────────────────┤
│ _runtime.py      run_tool · evaluate_write_gate · emit_progress │  cross-cutting
├──────────────────────────────────────────────────────────────┤
│ tools/*.py       validate → map raw→typed → dry-run/commit     │  business logic
├──────────────────────────────────────────────────────────────┤
│ models/schemas.py   Pydantic *Input / *Output · E.164          │  the CONTRACTS
├──────────────────────────────────────────────────────────────┤
│ api/*.py         path = config constant · pick family          │  REST wrappers
│ api/client.py    bearer header · retry/backoff · err→typed     │
├──────────────────────────────────────────────────────────────┤
│ auth/oauth.py    OAuthBroker · Fernet token store · PAT        │  auth
│ config.py        Settings(env) · endpoint paths (# VERIFY)     │  config
│ errors.py        typed exception hierarchy                     │  error taxonomy
└──────────────────────────────────────────────────────────────┘
        │  Authorization: Bearer <token>   (redacted in logs)
        ▼
   WxCC Config API   api.wxcc-REGION.cisco.com
```

### 10.1: One call, down the layers

When you invoke `tool_list_address_books`, the request passes through five named stops before it
leaves the process. You can open each file and read the function named here:

1. **`server.py` → `tool_list_address_books`** (`@mcp.tool()`) — resolves the client and session,
   then hands a deferred call to `run_tool` (the anatomy from Chapter 1).
2. **`_runtime.py` → `run_tool`** — binds the `request_id`, logs `tool.received`, and awaits the
   work. Everything below inherits that id via contextvars (Chapter 8.4).
3. **`tools/address_books.py` → `run_list`** — logs `tool_invoked`, calls the API wrapper, then
   maps each raw record to a typed `AddressBookItem` (every mapped field carries `# VERIFY`).
4. **`api/address_books.py` → `list_address_books`** — builds the path from a `config.py`
   constant and calls the shared client:

```python
path = config.ADDRESS_BOOKS_PATH.format(org_id=org_id)   # "/organization/{org_id}/address-book"
params = {"pageSize": min(max_results, 100)}             # VERIFY param name
return await client.get(ApiFamily.CONFIG, path, session_id, params=params)
```

5. **`api/client.py` → `get` → `_request`** — the single choke-point that authenticates, calls
   WxCC, retries, and returns parsed JSON (next section).

The other 17 tools have the **same shape** — only the `config` path constant, the API wrapper,
and the typed model differ. Read one and you can read them all.

### 10.2: The shared HTTP client — auth, retries, JSON

Every read and write funnels through `client.py._request`. It is the only place that talks to
the network, so it is the only place that needs auth, retry, and error logic. Abridged:

```python
# api/client.py — _request (abridged)
url = f"{self._base_url(family)}{path}"          # family → base URL (config.py)
for attempt in range(1, max_attempts + 1):
    token = await self._broker.get_valid_token(session_id)   # ← auth side-quest (10.4)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    logger.info("wxcc_api_call", method=method, family=family, path=path, attempt=attempt)
    resp = await client.request(method, url, headers=headers, params=params, json=json_body)
    if 200 <= resp.status_code < 300:
        return resp.json() if resp.content else {}
    if self._handle_error_status(resp, family, attempt, max_attempts):  # 429/5xx → retry?
        await self._sleep_backoff(attempt, _retry_after_seconds(resp))
        continue
    self._raise_for_status(resp, family)          # ← failure path (10.3)
```

Three things happen here that you saw as log symptoms in Chapter 9:

- **The `wxcc_api_call` event** is emitted *right before* the network call — its presence proves
  the request left the server (this is the whole basis of the Chapter 9 C-vs-D contrast).
- **`429` and `5xx` are retried** with exponential backoff + jitter, honoring the `Retry-After`
  header when present — each retry logs `wxcc_api_retry` (Chapter 9, scenario E).
- **A `2xx` returns parsed JSON**; anything else falls to `_raise_for_status`.

> **Builder.** One authenticated choke-point is the pattern worth stealing: wrappers in `api/*.py`
> stay dumb (build a path, pick a family, call `get/post/put/delete`), and *all* cross-cutting
> concerns — token injection, retry policy, error mapping, the `wxcc_api_call` log — live once in
> `_request`. Adding an endpoint never re-implements any of it.

### 10.3: The failure path — HTTP status to plain language

When WxCC returns a non-2xx, `_raise_for_status` maps the HTTP status to a **typed exception**
from `errors.py`, and `tools/_common.py → translate_error` turns that into the token-free
sentence the model (and you) actually read:

```text
   HTTP status        errors.py type                     translate_error() → message
   ──────────         ───────────────────────────        ─────────────────────────────────
   404          →     NotFoundError                  →    "Not found: … does not exist …"
   403          →     InsufficientPermissionsError   →    "Permission denied: … ask an admin …"
   429          →     RateLimitError                 →    "Rate limited: … retry shortly."
   (other)      →     WxccApiError                   →    "WxCC API error: <safe detail>"
   auth/token   →     AuthError (from auth/oauth.py) →    "Not authorized: complete … sign-in"
```

This is exactly the machinery behind the Chapter 9 scenario matrix — now you can see *where each
row is produced*:

- **Row C (permission denied, 403).** The `wxcc_api_call` event is logged in `_request` **before**
  `_raise_for_status` maps the `403` → `InsufficientPermissionsError`; `run_tool` catches it and
  `translate_error` renders the permission message as `tool.error`. The request *did* reach WxCC —
  that is why a `wxcc_api_call` is present.
- **Row D (E.164 validation).** The bad number is rejected inside the typed input model
  (`CreateEntryInput._validate_number → normalize_e164`) **before** `run_tool` ever calls the
  API — so there is **no** `wxcc_api_call`. Same `tool.error` shape as C, opposite cause.

That single presence-or-absence of `wxcc_api_call` is the difference between a *permissions* fix
(ask an admin for scope) and a *data* fix (correct the number) — see the Chapter 9 matrix for the
full drill.

> **Operator.** In the log stream, read the terminal event and the API stage together:
> `tool.error` **with** a preceding `wxcc_api_call` → the request reached WxCC and it refused
> (403/404/429 — a permissions/target/throttling problem). `tool.error` **without** a
> `wxcc_api_call` → it never left the server (auth not completed, or a typed-contract rejection
> like E.164). No `tool.received` at all → the client never invoked the tool (transport problem).

### 10.4: Authentication — the token broker

`_request` calls `self._broker.get_valid_token(session_id)` on every attempt. That broker lives
in `auth/oauth.py` and hides all of the OAuth machinery behind one method:

- **Personal-access-token bypass (what the lab uses).** If `WXCC_ACCESS_TOKEN` is set,
  `get_valid_token` logs `using_static_access_token` and returns that token directly — skipping
  the browser-based authorization-code flow entirely. This is why the lab can run against a live
  org with just a token pasted into `.env` (Step 0.5).
- **Full OAuth flow (production).** Otherwise the broker loads the session's stored `TokenSet`,
  and if it `is_expired()` (with a 60-second skew to avoid races) it refreshes it via the
  configured token endpoint, logging `oauth_token_refreshed`. If there is no token it raises
  `AuthError` → the "complete the Webex OAuth sign-in" message.

**Token security invariants** (stated as rules, because they are load-bearing):

- Tokens are stored **per session** and **encrypted at rest** with Fernet
  (`EncryptedTokenStore`); each session's token is a separate file written `0o600`.
- One session **cannot read another session's** token (reads are keyed by `session_id`).
- Tokens are **never returned** in any tool input or output (no model in `schemas.py` carries
  token material), and **never written to logs** — the `_redact` processor (§8.3) scrubs
  `authorization`, `access_token`, `refresh_token`, etc. before any line is serialized.

> **Builder.** Note the deliberate seam: `get_valid_token` is the *only* function that returns a
> raw token, and it is called *only* by the API client to build the `Authorization` header. That
> single exit point is what makes "tokens never leak" auditable. The OAuth endpoints, client
> id/secret, scopes, and redirect URI are all configuration (`config.py`, sourced from env) — the
> broker hardcodes none of them.

### 10.5: Configuration and typed contracts

**Configuration (`config.py`).** `Settings` (a `pydantic-settings` model with the `WXCC_` env
prefix) is the single source of truth for everything externally defined: OAuth endpoints, the
Config API base URL, scopes, the token store dir, and the log level/file. **Every endpoint path
is a placeholder marked `# VERIFY`** (e.g. `ADDRESS_BOOKS_PATH`,
`ADDRESS_BOOK_ENTRIES_PATH`), and the base URL is `https://api.wxcc-REGION.cisco.com  # VERIFY`.
Going live means resolving every `# VERIFY` / `# TODO` against
[developer.webex.com](https://developer.webex.com) (Chapter 7's checklist) — grep for those
markers to find them all.

**Contracts (`models/schemas.py`).** The typed `*Input` / `*Output` models are the contract the
tools enforce *before* any network call. The clearest example is the E.164 gate you met in
Chapter 3:

```python
# models/schemas.py
class CreateEntryInput(WriteInput):
    number: str = Field(..., description="Phone number in E.164 (required).")

    @field_validator("number")
    @classmethod
    def _validate_number(cls, value: str) -> str:
        return normalize_e164(value)   # raises ValueError on non-E.164 → rejected pre-network
```

Because `run_tool` constructs the `*Input` model at the top of the call, a malformed number
raises `ValueError` **before** `run_tool` reaches the API — which is exactly why the Chapter 3
bad-number attempt produced a `tool.error` with no `wxcc_api_call`. `WriteInput` also carries the
`confirm` fallback flag — consulted **only** when the gate could not reach a human at all, never
to override a refusal — and `WriteOutput` is the shared dry-run-or-committed result shape, which
also carries `gate_outcome`, `gate_reason`, and `next_step` so a blocked write explains itself to
the caller and not just to the log.

### 10.6: Which file do I open when X breaks?

Use this as an operator quick-reference once you've read the layers above:

| Symptom (in the log stream / client) | Open this file | Why |
|---|---|---|
| Repeated `wxcc_api_retry`, then a slow `tool.result` or a `429` error | `api/client.py` (`_handle_error_status`, `_sleep_backoff`) | retry/backoff policy and `Retry-After` handling live here |
| `tool.error` = "Not authorized … sign-in" with **no** `wxcc_api_call` | `auth/oauth.py` (`get_valid_token`) | token missing/expired, or `WXCC_ACCESS_TOKEN` not set |
| Translated `403` / `404` / generic API error (a `wxcc_api_call` **is** present) | `api/client.py` (`_raise_for_status`) → `errors.py` → `tools/_common.py` (`translate_error`) | HTTP-status → typed-error → message mapping |
| `tool.error` = "not valid E.164" (or other field error), **no** `wxcc_api_call` | `models/schemas.py` (the `*Input` validator) | typed contract rejected the data before the network |
| Wrong base URL / 404 on every call / go-live prep | `config.py` (`# VERIFY` paths, `config_api_base`) | endpoint placeholders not yet confirmed for your region |
| "Stored token could not be decrypted" / tokens don't persist | `auth/oauth.py` (`EncryptedTokenStore`) + `.env` `WXCC_TOKEN_ENCRYPTION_KEY` | Fernet key missing/changed, or no `token_store_dir` |
| Secrets appear in a log line | `logging_config.py` (`_redact`) | a new sensitive key needs adding to the redaction set (§8.3) |

> **Full drill:** pair this map with the Chapter 9 **scenario matrix** — that chapter turns a
> `request_id` into a diagnosis by which stages are present or absent; this chapter tells you
> which file owns the behavior once you've localized it.

---

## Appendix — Log-correlation cheat-sheet

Every tool invocation narrates the same lifecycle on the stderr stream. Match the stages by
their shared `request_id` (all fields below are keys in the structured JSON):

| Stage | Structured event (JSON) | Key fields | Meaning |
|---|---|---|---|
| Gate *(writes only)* | `write_gate` | `outcome`, `action`, `committed`, `reason`, `elicit_ms`, `client`, `client_detail` | how consent resolved, how long the client took, and who answered — precedes `tool.received` |
| Received | `tool.received` | `tool`, `intent`, `request_id` | the tool round-trip started |
| Auth | `using_static_access_token` / `oauth_token_refreshed` | *(inherits `request_id`)* | token brokered (redacted) |
| API | `wxcc_api_call` | `method`, `path` | a real WxCC REST call went out |
| Retry | `wxcc_api_retry` | `attempt` | 429/5xx backoff in progress |
| Sync entry | `sync.entry` | `detail` | one create/update/delete during a sync |
| Result | `tool.result` | `summary`, `elapsed_ms` | success + typed output + timing |
| Error | `tool.error` | `error`, `elapsed_ms` | failure (translated, token-free) |

**What a *missing* stage tells you:**

- No `tool.received` for an id you expected → the client never invoked the tool (check the
  client/transport connection state).
- `tool.received` but no `wxcc_api_call` → rejected before the network (auth, validation, or a
  dry-run with `commit=False`).
- `wxcc_api_call` but no `tool.result` → the call reached WxCC and failed there (see `tool.error`).
- A write with `commit=False` in its `intent` → read the `write_gate` line for that id to learn
  *why* consent was not obtained (§9, Scenario F).

`write_gate` appears **before** `tool.received` rather than inside the tool's timed region, and
that ordering is deliberate: the gate blocks on a human, so timing it would make every
`elapsed_ms` a measure of how fast the operator clicks. The correlation id is minted before the
gate and handed to both, which is what keeps the two on one trace.

> **Security note.** Secrets never appear in the stream: the `_redact` processor scrubs
> sensitive keys (`access_token`, `authorization`, `client_secret`, …) to `***REDACTED***`
> before any line is written, and tool events carry only intents, summaries, and translated
> messages — never token material.

> **Note on protocol logging.** This server logs to **stderr only**; MCP in-protocol logging
> (`notifications/message`) was deprecated by
> [SEP-2577](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging).
> Your client captures the stderr stream (see §8.5).

---

## What you built vs. what it replaces

You built the MCP server once. Here is what that buys — every week, for every admin, forever:

| | Manual (today) | MCP server (this lab) |
|---|---|---|
| **Time per sync** | 30–60 min (export, diff, re-enter, verify) | ~30 seconds (one command + approve) |
| **Error handling** | Opaque HTTP 400; google the field name | Typed message: "not valid E.164" |
| **Scope awareness** | Admin must know profiles are shared | Tool surfaces affected agents before commit |
| **Scale** | Effort grows linearly with contact count | Same effort: 3 contacts or 300 |
| **Audit trail** | Hope you remember what you changed | Every change previewed, approved, logged |
| **Knowledge required** | API docs, E.164 rules, deprecation traps | Natural language — "sync my CRM contacts" |
| **Vacation coverage** | It drifts; agents dial wrong numbers | Any admin (or a scheduled job) runs it |

The server is not a tool for one task. It is **institutional knowledge encoded as capability** —
the validation rules, the safety gates, the domain expertise — available to anyone with an MCP
client and a sentence describing what they need.

Build once. Use every Monday. The math does itself.

---

## Appendix — Client primitive support matrix  *(reference)*

MCP defines three core primitives (tools, resources, prompts), but client support varies
significantly. This appendix documents the current state so you know what to expect from each
client — and why MCP Inspector is the authoritative verification tool.

### How each client surfaces the three primitives

| Capability | Claude Desktop | Claude Code (agents) | Cursor | Custom bot (e.g. Webex) | MCP Inspector |
|---|---|---|---|---|---|
| `tools/list` → model can invoke | All tools shown | All tools shown | Progressive load (subset) | All as OpenAI functions | Full list + invoke |
| `prompts/list` called at startup | Yes | Yes | Unknown | Yes (bridge method) | Yes |
| Prompts visible to **user** | `/` slash commands | `/mcp__server__name` | No | No (unless wired) | Yes (Prompts tab) |
| Prompts visible to **model** | **No** | **No** | **No** | **No** (unless wired) | N/A |
| `resources/list` called at startup | Yes | Yes | Unknown | Yes (bridge method) | Yes |
| Resources visible to **user** | Settings > PROVIDED RESOURCES | Via synthetic tools | No | No | Yes (Resources tab) |
| Resources visible to **model** | **No** (user must manually attach) | **Yes** (`ListMcpResourcesTool`) | **No** | Partial (injected at startup) | N/A |
| Elicitation support | Partial | Yes | Unknown | Via `ctx.elicit` | Yes |

### Known issues with prompts (as of mid-2026)

| Issue | Client | Impact | Workaround | Reference |
|---|---|---|---|---|
| Local stdio prompts fail to invoke | Claude Desktop (Windows 1.24012.x) | Prompts list but clicking them shows "Failed to get prompt" | Use remote server, or wrap as tool | [#82045](https://github.com/anthropics/claude-code/issues/82045) |
| Title/name confusion — spaces break slash commands | Claude Code | `/server:Prompt Title` cut at first space → "Unknown slash command" | Set title = name (no spaces) | [#10992](https://github.com/anthropics/claude-code/issues/10992) |
| Arguments after slash command break parsing | Claude Code | `/server:prompt arg` → "Unknown slash command" | Invoke without trailing text | [#6657](https://github.com/anthropics/claude-code/issues/6657) |
| Agents cannot discover prompts | Claude Code | No `ListMcpPromptsTool` equivalent | Wrap prompts as tools | [#37900](https://github.com/anthropics/claude-code/issues/37900) |
| `prompts/list` sent before `notifications/initialized` | Claude Code/Desktop | Timeout on slow servers | Ensure fast server startup | [#9011](https://github.com/anthropics/claude-code/issues/9011) |

### Known issues with resources (as of mid-2026)

| Issue | Client | Impact | Workaround | Reference |
|---|---|---|---|---|
| Model cannot call `resources/read` autonomously | Claude Desktop | User must manually attach via `+` button | Wrap as tool, or inject at startup | [#23](https://github.com/anthropics/claude-ai-mcp/issues/23) |
| LLM ignores registered resources, does web search instead | Claude Desktop | Resources listed in settings but never read | Disable web search, or wrap as tool | [typescript-sdk#686](https://github.com/modelcontextprotocol/typescript-sdk/issues/686) |
| Dynamic resource templates broken | Claude Desktop | `resources/templates/list` not called | Use static resources only | [layered.dev](https://layered.dev/mcp-resources-the-overlooked-primitive/) |
| Large resources cause stack size errors | Claude Desktop | Resources over ~100KB fail silently | Paginate or summarize content | [layered.dev](https://layered.dev/mcp-resources-the-overlooked-primitive/) |

### Why this server keeps prompts and resources as proper types

Despite these client limitations, this lab registers prompts and resources as their spec-defined
types (not wrapped as tools) because:

1. **Correct architecture.** The MCP control model exists for a reason — resources are
   application-controlled reference data, prompts are user-triggered workflow templates. Wrapping
   everything as tools collapses these distinctions and loses the safety boundary (tools run with
   model agency; resources do not).

2. **MCP Inspector works.** The lab's verification tool shows all three primitives correctly.
   Participants learn the real architecture, not a workaround.

3. **Future-proof.** Client support is improving (Claude Code already added resource tools for
   agents). Servers built correctly today will gain capabilities as clients catch up.

4. **The custom bot bridges it.** The lab's Webex bot (`mcp_bridge.py`) has `list_prompts_sync`,
   `get_prompt_sync`, `list_resources_sync`, and `read_resource_sync` — the wiring exists, it
   just needs to be surfaced to the LLM or user depending on the use case.

### The pragmatic workaround (when you need it)

If you need resources or prompts to be model-accessible in production across all clients today,
the community pattern is to expose them as tools:

```python
@mcp.tool()
async def read_schema_guide() -> str:
    """Read the address book schema reference (naming, E.164, parentType rules)."""
    return json.dumps(address_book_schema_guide.as_dict(), indent=2)

@mcp.tool()
async def get_sync_workflow(org_id: str, address_book_id: str) -> str:
    """Get the CRM sync workflow instructions for a given org and address book."""
    return sync_prompt.build_prompt(org_id=org_id, book_name="", address_book_id=address_book_id)
```

This makes the content universally discoverable (every client supports `tools/list`), at the
cost of losing the control-model separation. Use this pattern selectively — for content the
model genuinely needs to access autonomously — and keep the proper types for everything else.

---

## References

- Model Context Protocol: <https://modelcontextprotocol.io>
- MCP debugging guide (Inspector, server logging, common issues):
  <https://modelcontextprotocol.io/docs/tools/debugging>
- MCP Inspector: <https://modelcontextprotocol.io/docs/tools/inspector>
- Webex Contact Center for Developers: <https://developer.webex.com/docs/contact-center>
- Server README and VERIFY/TODO checklist: `wxcc-mcp-server/README.md`
- Client primitive support discussion: <https://github.com/anthropics/claude-ai-mcp/issues/23>
- Resources as overlooked primitive: <https://layered.dev/mcp-resources-the-overlooked-primitive/>
- Prompts and resources patterns: <https://dev.to/aws-heroes/mcp-prompts-and-resources-the-primitives-youre-not-using-3oo1>
