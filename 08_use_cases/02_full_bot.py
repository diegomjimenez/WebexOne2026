"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Lab 8 — Full bot: imports the upgraded agent_bot modules for persistent MCP
sessions, Adaptive Card elicitation, and card-tap handling. Write operations
with server-side elicitation (e.g., update_desktop_profile) now post an
Adaptive Card and wait for the user to tap Confirm or Decline.
"""

import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

LAB_ROOT = Path(__file__).resolve().parent.parent
AGENT_BOT_DIR = str(LAB_ROOT / "webex-mcp-lab" / "agent_bot")

# Import the upgraded modules from agent_bot/utils — persistent sessions,
# Adaptive Card elicitation, card-tap WebSocket, and skills.
sys.path.insert(0, AGENT_BOT_DIR)

from utils import mcp_client, elicit, skills          # persistent MCP + elicit bridge
from utils.websocket import WebSocketClientCards       # messages + card taps
from local_agent_tools import webex_status             # local Webex status tool

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("full-bot")

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
bot_token = os.getenv("BOT_TOKEN")
MODEL = os.getenv("MODEL", "").strip()
if not MODEL:
    sys.exit(
        "ERROR: MODEL is not set in .env. Set it to the model your OpenAI "
        "project has access to, e.g.:\n"
        "  MODEL=gpt-5-nano\n"
    )
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
MCP_SERVERS_DIR = str(LAB_ROOT / "webex-mcp-lab" / "mcp_servers")

if not bot_token:
    sys.exit("ERROR: BOT_TOKEN is not set in .env")


def load_persona():
    path = os.path.join(SCRIPT_DIR, "system_prompt.txt")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            return text
    except OSError:
        pass
    log.warning("system_prompt.txt not found; using built-in persona.")
    return (
        "You are a Webex Contact Center troubleshooting assistant. Be concise. "
        "When a tool needs confirmation, call it directly — the server shows a "
        "confirmation card and handles approval."
    )


# ── Connect to MCP servers 06 and 07 (persistent sessions) ────────────────
_configs = [
    {
        "name": "address-books",
        "command": sys.executable,
        "args": ["06_manage_address_books.py"],
        "cwd": MCP_SERVERS_DIR,
    },
    {
        "name": "desktop-profiles",
        "command": sys.executable,
        "args": ["07_verify_desktop_profiles.py"],
        "cwd": MCP_SERVERS_DIR,
    },
]
mcp_client.connect_all(_configs, interactive=False)

# Wire the Adaptive Card elicitation bridge to all connections.
elicit.init(bot_token)
mcp_client.set_elicit_bridge(elicit)

# Discover skills, then build extra tools + dispatch for the agentic loop.
skills_catalog = skills.discover(SKILLS_DIR)
extra_tools = ([skills.tool_spec(skills_catalog)] if skills_catalog else []) \
    + [webex_status.status_tool_spec()] \
    + mcp_client.get_prompt_tools()
dispatch = {
    "load_skill": lambda a: skills.load_skill(skills_catalog, a.get("name", "")),
    **webex_status.status_dispatch(),
    **mcp_client.get_prompt_dispatch(),
}

# Build the modular system prompt: persona + skills catalog + server resources.
SYSTEM_PROMPT = (
    load_persona()
    + skills.catalog_prompt(skills_catalog)
    + "\n\n"
    + mcp_client.get_resources_text()
)

# Per-user conversation history.
conversations: dict[str, list] = {}

# REST session for sending replies.
api = requests.Session()
api.headers.update({
    "Authorization": f"Bearer {bot_token}",
    "Content-Type": "application/json",
})


def send(room_id, text):
    resp = api.post("https://webexapis.com/v1/messages",
                    json={"roomId": room_id, "text": text[:7000]})
    return resp.json().get("id", "") if resp.ok else ""


def _clear_thinking(thinking_id):
    if thinking_id:
        try:
            api.delete(f"https://webexapis.com/v1/messages/{thinking_id}")
        except Exception:
            pass


def _run_agent(uid, text, room_id):
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
    text = message.get("text", "").strip()
    room_id = message.get("roomId", "")
    uid = message.get("personEmail", "unknown")

    if not text:
        log.warning("Empty text, skipping.")
        return

    if text.lower() == "/reset":
        conversations.pop(uid, None)
        send(room_id, "History cleared.")
        return

    thinking_id = send(room_id, "Thinking...")
    reply = _run_agent(uid, text, room_id)
    _clear_thinking(thinking_id)
    send(room_id, reply)


def on_card(inputs, room=""):
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
