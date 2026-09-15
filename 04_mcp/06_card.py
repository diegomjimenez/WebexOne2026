"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Provide the LLM with a local tool to post a pre-defined Adaptive Card with Join buttons when there are meetings.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
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

MESSAGING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-messaging"
MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
MESSAGES_URL = "https://webexapis.com/v1/messages"
CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"
ERROR_REPLY = "Sorry, I could not answer that right now. Please try again in a moment."
SEND_MEETINGS_CARD = {
    "type": "function",
    "function": {
        "name": "send_meetings_card",
        "description": (
            "Post an Adaptive Card in the Webex space with title, time, host, and a Join "
            "button for each meeting. Call this after webex-list-meetings when "
            "data.meetings is not empty. Pass that meetings array. Do not invent meetings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "meetings": {
                    "type": "array",
                    "description": "The meetings array from webex-list-meetings (data.meetings).",
                }
            },
            "required": ["meetings"],
        },
    },
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-card-bot")

load_dotenv()

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


def when(meeting):
    start = datetime.fromisoformat(meeting["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(meeting["end"].replace("Z", "+00:00"))
    return f"{start:%a %d %b %H:%M} - {end:%H:%M} UTC"


def build_card(meetings):
    body = [
        {
            "type": "TextBlock",
            "text": f"Meetings in the next 7 days ({len(meetings)})",
            "size": "Large",
            "weight": "Bolder",
            "wrap": True,
        }
    ]
    for meeting in meetings:
        body.append(
            {
                "type": "Container",
                "separator": True,
                "items": [
                    {"type": "TextBlock", "text": meeting["title"], "weight": "Bolder", "wrap": True},
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "When", "value": when(meeting)},
                            {"title": "Host", "value": meeting.get("hostEmail", "unknown")},
                        ],
                    },
                    {
                        "type": "ActionSet",
                        "actions": [
                            {"type": "Action.OpenUrl", "title": "Join", "url": meeting["webLink"]}
                        ],
                    },
                ],
            }
        )
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.3",
        "body": body,
    }


def send_card(room_id, text, card):
    # A card rides along as an attachment; text is the fallback for clients that cannot render it.
    requests.post(
        MESSAGES_URL,
        headers={"Authorization": f"Bearer {BOT_TOKEN}"},
        json={
            "roomId": room_id,
            "text": text,
            "attachments": [{"contentType": CARD_CONTENT_TYPE, "content": card}],
        },
        timeout=30,
    ).raise_for_status()


async def answer(question, sender, room_id):
    tools = as_openai_tools(await hub.list_tools()) + [SEND_MEETINGS_CARD]
    log.info(f"Offering {len(tools)} tool(s) to {OPENAI_MODEL} (MCP + send_meetings_card)")
    posted = {"card": False}

    def send_meetings_card(arguments):
        meetings = arguments.get("meetings") or []
        if not meetings:
            return "No meetings to put on a card. Reply in a short chat message instead."
        send_card(room_id, f"You have {len(meetings)} meeting(s)", build_card(meetings))
        posted["card"] = True
        log.info(f"Sent a card with {len(meetings)} meeting(s)")
        return "Adaptive Card posted in the space. Give a short confirmation; do not re-list the meetings."

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex assistant helping {sender}. Today is {today} (UTC). "
                "Answer only from tool results, never from memory. "
                "When webex-list-meetings returns meetings, call send_meetings_card with "
                "that meetings array so the user gets Join buttons. "
                "If there are no meetings, or the question is not about meetings, reply in chat."
            ),
        },
        {"role": "user", "content": question},
    ]
    reply = await run_turn(hub, messages, tools, extra={"send_meetings_card": send_meetings_card})
    return reply, posted["card"]


def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")
    asyncio.create_task(reply_with_assistant(message, sender, text))


async def reply_with_assistant(message, sender, question):
    try:
        reply, posted_card = await answer(question, sender, message["roomId"])
    except Exception:
        log.exception("Assistant turn failed")
        bot.send_message(message["roomId"], ERROR_REPLY)
        return
    if posted_card:
        log.info(f"Card already sent to {sender}; LLM said: {reply}")
        return
    bot.send_message(message["roomId"], reply)
    log.info(f"Sent to {sender}: {reply}")


if __name__ == "__main__":
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
