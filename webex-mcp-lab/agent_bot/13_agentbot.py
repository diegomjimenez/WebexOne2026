"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 13 - agents use case: 12 + SKILLS + a LOCAL (non-MCP) tool.
# diff 12_agentbot.py 13_agentbot.py to see exactly what this adds:
#   • points at 07_agents_server.py instead of 06_full_server.py
#   • skills_loader (load_skill) — same wiring as step 09
#   • local_tools.check_webex_status — a tool that is NOT from the MCP server
#   • prompt meta-tools — so the server's diagnose_agent_availability prompt is
#     callable by the LLM (replaces step 12's address-book-only /setup command)
# The point: skills, MCP tools, server prompts, and local tools all work
# together in one agentic loop.

import logging
import os, sys
import requests
from dotenv import load_dotenv
from websocket_client_cards import WebSocketClientCards
import mcp_client_full as mcp_client
import elicit_bridge
import skills_loader                                                      # NEW
import local_tools                                                        # NEW

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agent-bot-13")

load_dotenv()

# Load configuration from .env.
bot_token   = os.getenv("BOT_TOKEN")
MODEL       = "gpt-4o-mini"
MAX_HISTORY = 20
SKILLS_DIR  = os.getenv("SKILLS_DIR",                                    # NEW
                        os.path.join(os.path.dirname(__file__), "skills"))# NEW

if not bot_token:
    sys.exit("ERROR: BOT_TOKEN is not set in .env")

# Connect to the MCP server (companion 07_agents_server.py).
mcp_client.connect(
    command=os.getenv("MCP_SERVER_COMMAND", "python"),
    args=os.getenv("MCP_SERVER_ARGS", "07_agents_server.py").split(","),  # NEW server
    cwd=os.getenv("MCP_SERVER_CWD", "."),
    interactive=False,
)

# Wire the Adaptive Card elicitation bridge.
elicit_bridge.init(bot_token)
mcp_client.set_elicit_bridge(elicit_bridge)

# Discover skills, then build extra tools + dispatch for the agentic loop.  NEW
# Three kinds of non-MCP-tool callables ride here together:                NEW
#   1. load_skill         — from skills_loader (client-side playbooks)     NEW
#   2. check_webex_status — from local_tools  (a plain HTTP call)          NEW
#   3. prompt__* meta-tools — from the MCP server's prompts (workflows)    NEW
skills = skills_loader.discover(SKILLS_DIR)                               # NEW
extra_tools = ([skills_loader.tool_spec(skills)] if skills else []) \
    + [local_tools.status_tool_spec()] \
    + mcp_client.get_prompt_tools()                                        # NEW
dispatch = {                                                              # NEW
    "load_skill": lambda a: skills_loader.load_skill(skills, a.get("name", "")),
    **local_tools.status_dispatch(),                                       # NEW
    **mcp_client.get_prompt_dispatch(),                                    # NEW
}                                                                         # NEW

# Build system prompt with server resource text + the skills catalog.
SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for troubleshooting "
    "Contact Center agents. Be concise.\n\n"
    "IMPORTANT — reassign tool:\n"
    "• To reassign an agent, call reassign_desktop_profile with `agent_id` "
    "and `desktop_profile_id` (ids come from list_agents / get_desktop_profile).\n"
    "• Do NOT ask the user to confirm in text — call the tool directly; "
    "the server will show a confirmation card and handle approval.\n"
    + skills_loader.catalog_prompt(skills)                                # NEW
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
    """Post a text reply to a Webex room. Returns the message id."""
    resp = api.post("https://webexapis.com/v1/messages",
                    json={"roomId": room_id, "text": text[:7000]})
    return resp.json().get("id", "") if resp.ok else ""


def on_message(message):
    """Route incoming messages: /reset or default chat."""
    text = message.get("text", "").strip()
    room_id = message.get("roomId", "")
    uid = message.get("personEmail", "unknown")

    if not text:
        log.warning("Empty text, skipping. Full message: %s", message)
        return

    # /reset — clear conversation history.
    if text.lower() == "/reset":
        conversations.pop(uid, None)
        send(room_id, "History cleared.")
        return

    # Default — run through the MCP + skills + local-tools agentic loop.
    thinking_id = send(room_id, "Thinking…")
    if uid not in conversations:
        conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversations[uid].append({"role": "user", "content": text})
    mcp_client.set_current_room(room_id)
    reply = mcp_client.agentic_loop(                                       # NEW
        conversations[uid], model=MODEL,                                  # NEW
        extra_tools=extra_tools, dispatch=dispatch,                        # NEW
    )                                                                     # NEW
    conversations[uid].append({"role": "assistant", "content": reply})
    while len(conversations[uid]) > 1 + MAX_HISTORY * 2:
        conversations[uid].pop(1); conversations[uid].pop(1)
    # Remove the "Thinking…" bubble before posting the reply.
    if thinking_id:
        try:
            api.delete(f"https://webexapis.com/v1/messages/{thinking_id}")
        except Exception:
            pass
    send(room_id, reply)


def on_card(inputs, room=""):
    """Handle Adaptive Card button taps received over Mercury."""
    elicit_id = inputs.get("elicit_id", "")
    confirmed = inputs.get("action") == "confirm"
    if elicit_id:
        elicit_bridge.resolve(elicit_id, confirmed, room=room)
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
