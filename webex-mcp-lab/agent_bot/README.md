# Agent Bot — a server-agnostic Webex front-end for any MCP server

This bot connects Webex to a **Model Context Protocol (MCP)** server. It
discovers the server's tools, resources, and prompts at startup and exposes them
through a Webex space — over a single outbound WebSocket, with no webhook and no
inbound connections. Nothing in the bot is tied to a specific server or use case;
point it at a different MCP server via `.env` and it adapts.

## Core principles

The bot composes four kinds of capability into one agentic loop:

| Source | What it provides | Where it lives |
|---|---|---|
| **MCP tools** | Server-defined actions (read/write) | discovered from the server |
| **MCP resources** | House conventions / domain guidance (text) | discovered from the server |
| **MCP prompts** | Guided workflows, exposed to the model as `prompt__*` meta-tools | discovered from the server |
| **Skills** | Client-side playbooks (`skills/<name>/SKILL.md`) | `skills/` + `utils/skills.py` |
| **Local tools** | Non-MCP helpers (e.g. the public Webex status check) | `local_agent_tools/` |

Two design ideas make it reusable:

- **Server-agnostic connection.** The MCP server is resolved entirely from
  `.env`. There is no hardcoded server default — if the required config is
  missing, the bot exits with a clear message.
- **Modular system prompt.** The persona is a plain text file
  (`system_prompt.txt`) kept intentionally domain-neutral. The effective prompt
  is `persona + skills catalog + the server's resource text`, so all
  domain-specific guidance comes from the connected server's resources.

## Layout

```
agent_bot/
├── agentbot.py            # entrypoint: config, wiring, message/card routing
├── system_prompt.txt      # editable, domain-neutral base persona
├── local_agent_tools/          # namespace package (no __init__.py needed)
│   └── webex_status.py    # Webex status / incident check (a local tool)
├── utils/                      # namespace package (no __init__.py needed)
│   ├── mcp_client.py      # MCP tools + resources + prompts + elicitation
│   ├── websocket.py       # Webex Mercury WebSocket (messages + card taps)
│   ├── elicit.py          # MCP elicitation → Webex Adaptive Card
│   ├── skills.py          # Agent Skills discovery/activation
│   └── commands.py        # configurable "/keyword" → server prompt
└── skills/                # SKILL.md playbooks
```

## Configuration

Copy `.env.example` to `.env` and fill it in. Key variables:

- `BOT_TOKEN` — Webex bot token (**required**).
- `OPENAI_API_KEY` — used by the agentic loop (**required**).
- `MCP_SERVER_ARGS` — the server script/args to launch (**required**; the bot
  fails fast if unset). Comma-separate multiple args.
- `MCP_SERVER_COMMAND` (default `python`) and `MCP_SERVER_CWD` (default `.`) —
  how and where to launch the server.
- `SYSTEM_PROMPT_FILE` (optional) — path to a different persona file.
- `SETUP_COMMAND_KEYWORD` / `SETUP_PROMPT_NAME` / `SETUP_PROMPT_ARGS` (optional) —
  wire an explicit `/keyword` to one of the server's prompts. Leave
  `SETUP_PROMPT_NAME` empty to disable the command.

## Run

From the `agent_bot/` directory (so the package imports resolve):

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env
python agentbot.py
```

Chat commands in the Webex space:

- `/reset` — clear your conversation history.
- `/<SETUP_COMMAND_KEYWORD>` — run the configured server prompt (if enabled).
- anything else — a normal request, answered via the agentic loop.

## Point it at a different MCP server

1. Set `MCP_SERVER_ARGS` / `MCP_SERVER_CWD` to the new server.
2. (Optional) swap `system_prompt.txt` or set `SYSTEM_PROMPT_FILE` for a persona
   that fits the new domain — but note domain rules should ideally live in the
   server's **resources**, not the persona.
3. (Optional) update `SETUP_PROMPT_NAME` to a prompt the new server offers.

No code changes are required — the bot re-discovers the new server's tools,
resources, and prompts on the next start.
