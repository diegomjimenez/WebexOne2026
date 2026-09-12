"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 11 - same as Step 10 but on a raw Mercury WebSocket (no webex_bot library).
# diff 10_agentbot.py 11_agentbot.py to see: webex_bot library → raw WebSocket.
# This continues from LAB-31123 which teaches the WebSocketClient.

import logging
import os, sys
import requests
from dotenv import load_dotenv
from websocket_client import WebSocketClient
import mcp_client_full as mcp_client
import elicit_bridge
import prompt_command

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agent-bot-ws")

load_dotenv()

# Load configuration from .env.
bot_token = os.getenv("BOT_TOKEN")
MODEL     = "gpt-4o-mini"
MAX_HISTORY = 20

if not bot_token:
    sys.exit("ERROR: BOT_TOKEN is not set in .env")

# Connect to the MCP server (companion 06_full_server.py).
mcp_client.connect(
    command=os.getenv("MCP_SERVER_COMMAND", "python"),
    args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
    cwd=os.getenv("MCP_SERVER_CWD", "."),
    interactive=False,
)

# Wire the Adaptive Card elicitation bridge.
elicit_bridge.init(bot_token)
mcp_client.set_elicit_bridge(elicit_bridge)

# Build system prompt with server resource text.
SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for managing "
    "Contact Center resources. Be concise.\n\n"
    + mcp_client.get_resources_text()
)

# Per-user conversation history.
conversations: dict[str, list] = {}

# Wire the /setup prompt command.
prompt_command.init(mcp_client, conversations, SYSTEM_PROMPT, MODEL, MAX_HISTORY)

# REST session for sending replies.
api = requests.Session()
api.headers.update({
    "Authorization": f"Bearer {bot_token}",
    "Content-Type": "application/json",
})


def send(room_id, text):
    """Post a text reply to a Webex room."""
    api.post("https://webexapis.com/v1/messages",
             json={"roomId": room_id, "text": text[:7000]})


def on_message(message):
    """Route incoming messages: /reset, /setup, or default chat."""
    text = message.get("text", "").strip()
    room_id = message.get("roomId", "")
    uid = message.get("personEmail", "unknown")

    if not text:
        return

    # /reset — clear conversation history.
    if text.lower() == "/reset":
        conversations.pop(uid, None)
        send(room_id, "History cleared.")
        return

    # /setup — trigger the set_up_address_book prompt.
    if text.lower().startswith("/setup"):
        send(room_id, "Thinking…")
        user_msg = text[len("/setup"):].strip()
        reply = prompt_command.run(uid, user_msg, room_id)
        send(room_id, reply)
        return

    # Default — run through the MCP agentic loop.
    send(room_id, "Thinking…")
    if uid not in conversations:
        conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversations[uid].append({"role": "user", "content": text})
    mcp_client.set_current_room(room_id)
    reply = mcp_client.agentic_loop(conversations[uid], model=MODEL)
    conversations[uid].append({"role": "assistant", "content": reply})
    while len(conversations[uid]) > 1 + MAX_HISTORY * 2:
        conversations[uid].pop(1); conversations[uid].pop(1)
    send(room_id, reply)


# Start the WebSocket listener.
client = WebSocketClient(access_token=bot_token, on_message=on_message)
log.info("Listening as %s via WebSocket... (Ctrl+C to stop)",
         client.me.get("emails", ["?"])[0])
try:
    client.run()
except KeyboardInterrupt:
    log.info("Stopped.")
