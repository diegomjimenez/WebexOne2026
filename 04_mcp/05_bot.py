"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Connecting the LLM with the MCP hub to a Webex bot.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from llm import as_openai_tools, run_turn
from mcp_hub import McpHub

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_bot"))
from websocket_client import WebSocketClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MESSAGING_MCP_URL = os.getenv("WEBEX_MESSAGING_MCP_URL", "https://mcp.webexapis.com/mcp/webex-messaging")
MEETING_MCP_URL = os.getenv("WEBEX_MEETING_MCP_URL", "https://mcp.webexapis.com/mcp/webex-meeting")
ERROR_REPLY = "Sorry, I could not answer that right now. Please try again in a moment."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-bot")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

BOT_TOKEN = os.getenv("BOT_TOKEN")
MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in your .env file")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")
if not MESSAGING_TOKEN and not MEETING_TOKEN:
    raise SystemExit(
        "Set WEBEX_MESSAGING_MCP_TOKEN and/or WEBEX_MEETING_MCP_TOKEN in your .env file"
    )

hub = McpHub(
    [
        (MESSAGING_MCP_URL, MESSAGING_TOKEN),
        (MEETING_MCP_URL, MEETING_TOKEN),
    ]
)


async def answer(question, sender):
    tools = as_openai_tools(await hub.list_tools())
    log.info(f"Offering {len(tools)} tool(s) from {len(hub.clients)} MCP server(s) to {OPENAI_MODEL}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex assistant helping {sender}. Today is {today} (UTC). "
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
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
