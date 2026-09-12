# Lab Guide — From Webex Bot to AI Agent Harness

**Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot**

Diego Manuel Jimenez Moreno · Mo Eyad Musallam

---

## What You'll Build

You already have an LLM-powered Webex bot (`05_llmbot.py`). In this lab you will evolve it into a full AI agent in three steps:

| File | What It Does | Lines |
|------|--------------|-------|
| `07_agentbot.py` | Plain LLM chat — the base | ~75 |
| `08_agentbot.py` | 07 + **MCP tools** (via `mcp_client` module) | ~80 |
| `09_agentbot.py` | 08 + **Agent Skills** (via `skills_loader` module) | ~95 |
| `10_agentbot.py` | 08 + **full MCP** — resources, prompts, elicitation (via `mcp_client_full`) | ~85 |

Plus reusable modules the attendees build first:

| Module | What It Does | Lines |
|--------|--------------|-------|
| `mcp_client.py` | Connect to any MCP server, discover tools, agentic loop | ~100 |
| `mcp_client_resources.py` | mcp_client + **resources** (read conventions) | ~120 |
| `mcp_client_prompts.py` | + **prompts** (render server workflows) | ~140 |
| `mcp_client_full.py` | + **elicitation** (server asks user mid-call) | ~160 |
| `skills_loader.py` | Discover and activate Agent Skills (agentskills.io) | ~100 |

**The key insight:** `diff` between adjacent files shows exactly what each primitive adds.

---

## Prerequisites

1. **Python 3.11+** with:

   ```
   pip install webex-bot openai mcp python-dotenv
   ```

2. **`.env` file** in `02-interactive/`:

   ```
   BOT_TOKEN=<your Webex bot token>
   DOMAIN=<your approved email domain>
   OPENAI_API_KEY=<your OpenAI key>
   MCP_SERVER_COMMAND=python
   MCP_SERVER_ARGS=06_full_server.py
   MCP_SERVER_CWD=<path to the WebexOne2026 mcp_servers folder>
   ```

3. **Companion MCP server** — clone the [WebexOne2026](https://github.com/diegomjimenez/WebexOne2026) repo.

---

## Step 1 — Build the MCP Client Module

**File:** `mcp_client.py`

Three functions:
- **`connect(command, args, cwd)`** — spawn an MCP server over stdio, discover tools
- **`call_tool(name, args)`** — call one MCP tool (sync wrapper)
- **`agentic_loop(messages, model, extra_tools, dispatch)`** — LLM → tool → result → repeat

The `dispatch` parameter lets callers intercept specific tools (used in Step 5 for skills).

---

## Step 2 — Build the Skills Loader Module

**File:** `skills_loader.py`

Four functions:
- **`discover(skills_dir)`** — scan `skills/*/SKILL.md`, parse frontmatter
- **`load_skill(catalog, name)`** — return the full SKILL.md body
- **`tool_spec(catalog)`** — OpenAI function spec for `load_skill`
- **`catalog_prompt(catalog)`** — text block for the system prompt

No PyYAML, no framework — just a frontmatter parser and four functions.

---

## Step 3 — Run the plain LLM bot

**File:** `07_agentbot.py`

This is the base: config, OpenAI chat, Webex bot wiring. No tools.

```bash
python 07_agentbot.py
```

**Verify:** Send *"hello"* — you get a plain LLM reply.

---

## Step 4 — Add MCP tools

**File:** `08_agentbot.py`

Run `diff 07_agentbot.py 08_agentbot.py` to see the changes:
- `import mcp_client`
- `mcp_client.connect(...)` at startup
- `mcp_client.agentic_loop(messages)` replaces `openai.chat.completions.create`

```bash
python 08_agentbot.py
```

**Verify:** Send *"list the address books"* — the bot calls the MCP tool and returns real data.

---

## Step 5 — Add Agent Skills

**File:** `09_agentbot.py`

Run `diff 08_agentbot.py 09_agentbot.py` to see the changes:
- `import skills_loader`
- `skills_loader.discover(SKILLS_DIR)` at startup
- Catalog injected into system prompt
- `extra_tools` and `dispatch` passed to `agentic_loop`

```bash
python 09_agentbot.py
```

**Verify:**
- *"Set up an address book for the sales team"* → activates `address-book-setup` skill, then calls MCP tools
- *"An agent is stuck in Not Ready"* → activates `troubleshoot-agent-state` skill

---

## Step 6 — Add MCP Resources to the client

**File:** `mcp_client_resources.py`

Run `diff mcp_client.py mcp_client_resources.py` to see the changes:
- `list_resources()` and `read_resource()` at connect time
- `get_resources_text()` accessor for the caller
- Resource text prepended to the system message in `agentic_loop()`

**Standalone demo** (no bot needed, needs Contact Center credentials):

```bash
python mcp_client_resources.py
```

**Verify:** The demo prints the `lab://address-books` conventions text.

---

## Step 7 — Add MCP Prompts to the client

**File:** `mcp_client_prompts.py`

Run `diff mcp_client_resources.py mcp_client_prompts.py` to see the changes:
- `list_prompts()` at connect time
- `get_prompt(name, args)` renders a server prompt into messages

**Standalone demo:**

```bash
python mcp_client_prompts.py
```

**Verify:** The demo lists prompts, renders `set_up_address_book`, and shows the unknown-prompt error.

---

## Step 8 — Add Elicitation to the client

**File:** `mcp_client_full.py`

Run `diff mcp_client_prompts.py mcp_client_full.py` to see the changes:
- `elicitation_callback` passed to `ClientSession`
- Console mode (`interactive=True`): `input()` asks for confirmation
- Bot mode (`interactive=False`): auto-accepts and logs a note

**Standalone demo:**

```bash
python mcp_client_full.py
```

**Verify:** The demo triggers a delete; the server asks you to confirm at the console. Type `y` to proceed or `n` to decline.

---

## Step 9 — Full MCP bot

**File:** `10_agentbot.py`

Run `diff 08_agentbot.py 10_agentbot.py` to see the changes:
- `import mcp_client_full as mcp_client` instead of `import mcp_client`
- `interactive=False` in `connect()`
- Resource text wired into the system prompt
- **Prompt meta-tools**: `get_prompt_tools()` and `get_prompt_dispatch()` are passed to `agentic_loop()` so the LLM can activate server-defined workflows (e.g. `set_up_address_book`) as callable functions
- **Adaptive Card elicitation**: `elicit_bridge` posts a Cisco Live branded card with Confirm/Decline buttons when the MCP server fires an elicitation (e.g. delete). The bot blocks until the user taps a button or 60 seconds pass

```bash
python 10_agentbot.py
```

**Verify:**
- *"list the address books"* → tools work as before
- *"what are the address book conventions?"* → the bot knows the conventions (resources)
- *"set up an address book for the EMEA team"* → the bot calls `prompt__set_up_address_book`, gets the server's workflow steps, then follows them (reads resource, checks existing books, creates if needed, asks for contacts)
- *"delete the HR Team address book"* → an Adaptive Card appears with ✓ Confirm / ✗ Decline buttons; tapping Confirm completes the delete, tapping Decline cancels it

---

## Step 11 — WebSocket bot (continues LAB-31123)

**Files:** `websocket_client.py`, `11_agentbot.py`

This step replaces the `webex_bot` library with the raw Mercury WebSocket client from LAB-31123. The MCP wiring is identical to Step 10 — only the transport layer changes.

Run `diff 10_agentbot.py 11_agentbot.py` to see the changes:
- No `webex_bot` imports — uses `WebSocketClient` from `websocket_client.py`
- Manual slash-command routing in `on_message()` instead of `Command` classes
- Replies via `requests.post()` instead of returning a string

```bash
python 11_agentbot.py
```

**Verify:**
- *"list the address books"* → tools work (default chat route)
- */setup EMEA team* → triggers the `set_up_address_book` prompt workflow
- */reset* → clears conversation history
- *"delete the HR Team address book"* → elicitation Adaptive Card appears

---

## Example Skills

| Skill | Purpose |
|-------|---------|
| `address-book-setup` | End-to-end: check existing, create book, add contacts |
| `troubleshoot-agent-state` | Diagnose agent state issues, suggest fixes |

Add your own: create `skills/<name>/SKILL.md` with `name` + `description` frontmatter, restart the bot.

---

## Architecture

```
07_agentbot.py       08_agentbot.py       09_agentbot.py       10_agentbot.py
  OpenAI chat    -->   + mcp_client    -->   + skills_loader -->  + mcp_client_full
  (no tools)           (MCP tools)           (MCP + skills)       (full MCP)
                            |                     |                     |
                       mcp_client.py         skills_loader.py   mcp_client_full.py
                            |                     |                     |
                       06_full_server.py     skills/*/SKILL.md  06_full_server.py
```

**Progressive client modules** (taught via `diff`):
```
mcp_client.py → mcp_client_resources.py → mcp_client_prompts.py → mcp_client_full.py
  (tools)           + resources                + prompts              + elicitation
```

---

## Production Notes

- **Elicitation:** `06_full_server.py` confirms deletes server-side. This client skips that — see `06_mcpbot.py` for Adaptive-Card approval.
- **Frameworks:** [deepagents](https://docs.langchain.com/oss/python/deepagents/skills), [AG2](https://docs.ag2.ai/docs/user-guide/skills/), [MS Agent Framework](https://learn.microsoft.com/en-us/agent-framework/agents/skills)
- **Full spec:** [agentskills.io/specification](https://agentskills.io/specification)
