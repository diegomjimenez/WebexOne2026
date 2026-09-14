"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

The tool-calling loop from 03, behind a Webex bot: the user asks in a space, the
LLM picks the Meetings MCP tool, and the LLM writes the reply.

"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from mcp.shared.exceptions import MCPError

from mcp_client import McpClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_bot"))
from websocket_client import WebSocketClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_STEPS = 5  # stop runaway tool loops
ERROR_REPLY = "Sorry, I could not answer that right now. Please try again in a moment."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-bot")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in your .env file")
if not MEETING_TOKEN:
    raise SystemExit("Set WEBEX_MEETING_MCP_TOKEN in your .env file")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")

mcp = McpClient(MEETING_TOKEN, MEETING_MCP_URL)
tool_cache = None  # the tool list does not change while the bot runs


def ask_llm(messages, tools):
    """One Chat Completions round. Returns the assistant message (text or tool calls)."""
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": OPENAI_MODEL, "messages": messages, "tools": tools},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


async def openai_tools():
    # An MCP tool already describes itself with a JSON schema, which is what OpenAI wants.
    global tool_cache
    if tool_cache is None:
        tool_cache = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in await mcp.list_tools()
        ]
        log.info(f"Offering {len(tool_cache)} Meetings MCP tool(s) to {OPENAI_MODEL}")
    return tool_cache


async def run_turn(question, sender):
    tools = await openai_tools()
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

    for _ in range(MAX_STEPS):
        # requests blocks, so keep it off the WebSocket's event loop.
        message = await asyncio.to_thread(ask_llm, messages, tools)
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return message.get("content") or "(no answer)"

        for call in tool_calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"] or "{}")
            log.info(f"LLM asked for {name} {arguments}")
            try:
                result = await mcp.call_tool(name, arguments)
            except MCPError as exc:
                log.error(f"{name} failed: {exc}")
                result = f"Tool error: {exc}"
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    return f"I stopped after {MAX_STEPS} tool steps without an answer."


def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")
    asyncio.create_task(reply_with_assistant(message, sender, text))


async def reply_with_assistant(message, sender, question):
    try:
        reply = await run_turn(question, sender)
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
