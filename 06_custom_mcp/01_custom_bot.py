"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Connect the AI Assistant to both the remote Messaging MCP and the local Custom MCP.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Add paths to import from other labs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "05_service_apps"))
from token_manager import TokenManager

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "04_mcp"))
from llm import as_openai_tools, run_turn

# Import the updated client and hub from the current directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_client import McpClient
from mcp_hub import McpHub

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_bot"))
from websocket_client import WebSocketClient

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MESSAGING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-messaging"
ERROR_REPLY = "Sorry, I could not answer that right now. Please try again in a moment."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("custom-mcp-bot")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")

# Initialize the Token Manager (reading from the global .env file)
token_manager = TokenManager()
service_app_token = token_manager.get_token()

# 1. Create the remote client (Messaging MCP)
messaging_client = McpClient(access_token=service_app_token, url=MESSAGING_MCP_URL)

# 2. Create the local custom client (stdio)
server_script = str(Path(__file__).resolve().parent / "server.py")
custom_client = McpClient(
    command="python", 
    args=[server_script], 
    env={"ACCESS_TOKEN": service_app_token}
)

# 3. Combine them in the Hub
hub = McpHub([messaging_client, custom_client])

async def answer(question, sender):
    tools = as_openai_tools(await hub.list_tools())
    log.info(f"Offering {len(tools)} tool(s) from {len(hub.clients)} MCP server(s) to {OPENAI_MODEL}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex assistant for the organization helping {sender}. Today is {today} (UTC). "
                "Answer only from tool results, never from memory, and reply in a short "
                "friendly chat message."
            ),
        },
        {"role": "user", "content": question},
    ]
    return await run_turn(hub, messages, tools)

def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")
    asyncio.create_task(reply_with_assistant(message, sender, text))

async def reply_with_assistant(message, sender, question):
    try:
        reply = await answer(question, sender)
    except Exception:
        log.exception("Assistant turn failed")
        reply = ERROR_REPLY
    
    bot.send_message(message["roomId"], reply)
    log.info(f"Sent to {sender}: {reply}")

if __name__ == "__main__":
    bot = WebSocketClient(access_token=service_app_token, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
