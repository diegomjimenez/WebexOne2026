"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# A Webex bot that fronts one or more MCP servers. Tools, resources, and
# prompts are discovered from whatever server(s) .env points at; the persona
# lives in a file. Nothing here is tied to a specific server or use case.

import logging
import os
import sys

import requests
from dotenv import load_dotenv

from utils import mcp_client, skills, elicit, commands
from utils.websocket import WebSocketClientCards
from local_agent_tools import webex_status

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agent-bot")

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
bot_token   = os.getenv("BOT_TOKEN")
MODEL       = os.getenv("MODEL", "").strip()
if not MODEL:
    sys.exit(
        "ERROR: MODEL is not set in .env. Set it to the model your OpenAI "
        "project has access to, e.g.:\n"
        "  MODEL=gpt-5-nano\n"
        "  MODEL=gpt-4o\n"
        "  MODEL=gpt-4o-mini\n"
        "Any OpenAI-compatible provider works — just set OPENAI_BASE_URL too."
    )
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
SKILLS_DIR  = os.getenv("SKILLS_DIR", os.path.join(SCRIPT_DIR, "skills"))

# Fallback persona used only if the prompt file is missing. Kept generic on
# purpose — domain guidance comes from the MCP server's resources.
_DEFAULT_PERSONA = (
    "You are a helpful assistant connected to tools, resources, and workflows "
    "provided by an MCP server. Be concise.\n"
    "When a tool needs confirmation, call it directly — the server shows a "
    "confirmation card and handles approval. Do not ask the user to confirm "
    "in text.\n"
    "Read any resources the server provides for house conventions before acting."
)

if not bot_token:
    sys.exit("ERROR: BOT_TOKEN is not set in .env")


def resolve_mcp_configs():
    """Resolve one or more MCP servers from .env.

    Multi-server: reads MCP_SERVER_ARGS_1/CWD_1, MCP_SERVER_ARGS_2/CWD_2, …
    Single-server fallback: reads the un-suffixed MCP_SERVER_ARGS/CWD.
    Returns a list of {"name", "command", "args", "cwd"} dicts.
    """
    command = os.getenv("MCP_SERVER_COMMAND", "python")
    configs = []
    # Try indexed vars first (MCP_SERVER_ARGS_1, _2, …).
    for i in range(1, 10):
        args = os.getenv(f"MCP_SERVER_ARGS_{i}", "").strip()
        if not args:
            break
        cwd = os.getenv(f"MCP_SERVER_CWD_{i}", "").strip() or "."
        name = os.getenv(f"MCP_SERVER_NAME_{i}", f"server-{i}").strip()
        configs.append({
            "name": name,
            "command": command,
            "args": [a.strip() for a in args.split(",")],
            "cwd": cwd,
        })
    # Fallback to un-suffixed single-server vars.
    if not configs:
        args = os.getenv("MCP_SERVER_ARGS", "").strip()
        cwd = os.getenv("MCP_SERVER_CWD", "").strip() or "."
        if not args:
            sys.exit(
                "ERROR: No MCP server configured in .env. Set either:\n"
                "  Multi-server:  MCP_SERVER_ARGS_1, MCP_SERVER_CWD_1, …\n"
                "  Single-server: MCP_SERVER_ARGS, MCP_SERVER_CWD\n"
                "See .env.example for a runnable example."
            )
        configs.append({
            "name": "default",
            "command": command,
            "args": [a.strip() for a in args.split(",")],
            "cwd": cwd,
        })
    return configs


def load_persona():
    """Load the base system persona from a file (SYSTEM_PROMPT_FILE or the
    default system_prompt.txt), falling back to a generic built-in persona."""
    path = os.getenv("SYSTEM_PROMPT_FILE", os.path.join(SCRIPT_DIR, "system_prompt.txt"))
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            return text
    except OSError:
        pass
    log.warning("System prompt file not found (%s); using built-in persona.", path)
    return _DEFAULT_PERSONA


# ── Connect to MCP server(s) from .env ─────────────────────────────────────
_configs = resolve_mcp_configs()
mcp_client.connect_all(_configs, interactive=False)

# Wire the Adaptive Card elicitation bridge to all connections.
elicit.init(bot_token)
mcp_client.set_elicit_bridge(elicit)

# Discover skills, then build extra tools + dispatch for the agentic loop.
# Three kinds of non-MCP-tool callables ride here together:
#   1. load_skill            — from utils.skills          (client-side playbooks)
#   2. check_webex_status    — from local_agent_tools     (a plain HTTP call)
#   3. prompt__* meta-tools  — from the MCP server's prompts (workflows)
skills_catalog = skills.discover(SKILLS_DIR)
extra_tools = ([skills.tool_spec(skills_catalog)] if skills_catalog else []) \
    + [webex_status.status_tool_spec()] \
    + mcp_client.get_prompt_tools()
dispatch = {
    "load_skill": lambda a: skills.load_skill(skills_catalog, a.get("name", "")),
    **webex_status.status_dispatch(),
    **mcp_client.get_prompt_dispatch(),
}

# Build the modular system prompt: file persona + skills catalog + server resources.
SYSTEM_PROMPT = (
    load_persona()
    + skills.catalog_prompt(skills_catalog)
    + "\n\n"
    + mcp_client.get_resources_text()
)

# Per-user conversation history.
conversations: dict[str, list] = {}

# Wire the configurable slash command (e.g. /setup) against the connected server.
commands.init(mcp_client, conversations, SYSTEM_PROMPT, MODEL, MAX_HISTORY)

# REST session for sending replies.
api = requests.Session()
api.headers.update({
    "Authorization": f"Bearer {bot_token}",
    "Content-Type": "application/json",
})


def send(room_id, text):
    """Post a text reply to a Webex room. Returns the message id."""
    resp = api.post("https://webexapis.com/v1/messages",
                    json={"roomId": room_id, "text": text[:7000]})
    return resp.json().get("id", "") if resp.ok else ""


def _clear_thinking(thinking_id):
    """Remove the 'Thinking…' bubble before posting a reply (best-effort)."""
    if thinking_id:
        try:
            api.delete(f"https://webexapis.com/v1/messages/{thinking_id}")
        except Exception:
            pass


def _run_agent(uid, text, room_id):
    """Append the user turn, run the agentic loop, and trim history."""
    if uid not in conversations:
        conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversations[uid].append({"role": "user", "content": text})
    mcp_client.set_current_room(room_id)
    reply = mcp_client.agentic_loop(
        conversations[uid], model=MODEL,
        extra_tools=extra_tools, dispatch=dispatch,
    )
    conversations[uid].append({"role": "assistant", "content": reply})
    while len(conversations[uid]) > 1 + MAX_HISTORY * 2:
        conversations[uid].pop(1); conversations[uid].pop(1)
    return reply


def on_message(message):
    """Route incoming messages: /reset, the configured command, or default chat."""
    text = message.get("text", "").strip()
    room_id = message.get("roomId", "")
    uid = message.get("personEmail", "unknown")

    if not text:
        log.warning("Empty text, skipping. Full message: %s", message)
        return

    lower = text.lower()

    # /reset — clear conversation history.
    if lower == "/reset":
        conversations.pop(uid, None)
        send(room_id, "History cleared.")
        return

    # Configured prompt command (e.g. /setup) — triggers a server prompt.
    keyword = commands.KEYWORD
    if commands.PROMPT_NAME and (lower == f"/{keyword}"
                                 or lower.startswith(f"/{keyword} ")):
        rest = text[len(keyword) + 1:].strip()
        thinking_id = send(room_id, "Thinking…")
        reply = commands.run(uid, rest, room_id)
        _clear_thinking(thinking_id)
        send(room_id, reply)
        return

    # Default — run through the MCP + skills + local-tools agentic loop.
    thinking_id = send(room_id, "Thinking…")
    reply = _run_agent(uid, text, room_id)
    _clear_thinking(thinking_id)
    send(room_id, reply)


def on_card(inputs, room=""):
    """Handle Adaptive Card button taps received over Mercury."""
    elicit_id = inputs.get("elicit_id", "")
    confirmed = inputs.get("action") == "confirm"
    if elicit_id:
        elicit.resolve(elicit_id, confirmed, room=room)
        log.info("Card tap: %s", "confirmed" if confirmed else "declined")
    else:
        log.warning("Card tap with no elicit_id: %s", inputs)


# Start the WebSocket listener — messages AND card taps, one connection.
client = WebSocketClientCards(
    access_token=bot_token,
    on_message=on_message,
    on_card=on_card,
)
log.info("Listening as %s via Mercury (messages + cards)... (Ctrl+C to stop)",
         client.me.get("emails", ["?"])[0])
try:
    client.run()
except KeyboardInterrupt:
    log.info("Stopped.")
