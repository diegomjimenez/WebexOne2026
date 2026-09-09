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

Plus two reusable modules the attendees build first:

| Module | What It Does | Lines |
|--------|--------------|-------|
| `mcp_client.py` | Connect to any MCP server, discover tools, agentic loop | ~100 |
| `skills_loader.py` | Discover and activate Agent Skills (agentskills.io) | ~100 |

**The key insight:** `diff 07 08` shows exactly what MCP adds. `diff 08 09` shows exactly what skills add.

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

## Example Skills

| Skill | Purpose |
|-------|---------|
| `address-book-setup` | End-to-end: check existing, create book, add contacts |
| `troubleshoot-agent-state` | Diagnose agent state issues, suggest fixes |

Add your own: create `skills/<name>/SKILL.md` with `name` + `description` frontmatter, restart the bot.

---

## Architecture

```
07_agentbot.py       08_agentbot.py       09_agentbot.py
  OpenAI chat    -->   + mcp_client    -->   + skills_loader
  (no tools)           (MCP tools)           (MCP + skills)
                            |                     |
                       mcp_client.py         skills_loader.py
                            |                     |
                       06_full_server.py     skills/*/SKILL.md
```

---

## Production Notes

- **Elicitation:** `06_full_server.py` confirms deletes server-side. This client skips that — see `06_mcpbot.py` for Adaptive-Card approval.
- **Frameworks:** [deepagents](https://docs.langchain.com/oss/python/deepagents/skills), [AG2](https://docs.ag2.ai/docs/user-guide/skills/), [MS Agent Framework](https://learn.microsoft.com/en-us/agent-framework/agents/skills)
- **Full spec:** [agentskills.io/specification](https://agentskills.io/specification)
