"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Webex bot from Lab 6, plus the skill loader.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

LAB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB_ROOT / "06_mcp_bot"))
sys.path.insert(0, str(LAB_ROOT / "05_bot"))

from llm import as_openai_tools, run_turn
from mcp_client import McpClient
from mcp_hub import McpHub
from skill_loader import SkillLoader
from websocket_client import WebSocketClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MESSAGING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-messaging"
MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
CUSTOM_SERVER = LAB_ROOT / "03_custom_mcp" / "03_read_books.py"
SKILLS_DIR = Path(__file__).resolve().parent / "skills"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-skills-bot")

load_dotenv(LAB_ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
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

skill_loader = SkillLoader(SKILLS_DIR)
log.info(f"Loaded {len(skill_loader.skills)} skill(s): {', '.join(sorted(skill_loader.skills))}")

READ_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "read_skill_runbook",
        "description": "Read the full instructions for a skill. Pass the skill name from the system prompt.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill name, for example meeting-review.",
                }
            },
            "required": ["skill_name"],
        },
    },
}


def read_skill_runbook(arguments):
    skill_name = arguments.get("skill_name")
    skill = skill_loader.get_skill(skill_name)
    if skill:
        log.info(f"LLM reading skill: {skill_name}")
        return skill.instructions
    return f"Skill '{skill_name}' not found. Available: {', '.join(sorted(skill_loader.skills)) or '(none)'}"


servers = [
    (MESSAGING_MCP_URL, MESSAGING_TOKEN),
    (MEETING_MCP_URL, MEETING_TOKEN),
]
if ACCESS_TOKEN and CUSTOM_SERVER.is_file():
    servers.append(
        McpClient(
            command=sys.executable,
            args=[str(CUSTOM_SERVER)],
            cwd=str(LAB_ROOT),
        )
    )
else:
    log.info("Custom MCP server not connected. Set ACCESS_TOKEN to include it.")

hub = McpHub(servers)


async def answer(question, sender):
    tools = as_openai_tools(await hub.list_tools()) + [READ_SKILL_TOOL]
    log.info(f"Offering {len(tools)} tool(s) to {OPENAI_MODEL}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex assistant helping {sender}. Today is {today} (UTC). "
                "Answer only from tool results, never from memory. "
                "If a user's request matches a skill below, call read_skill_runbook "
                "with that skill's name, then follow the instructions exactly.\n\n"
                f"{skill_loader.get_all_skills_summary()}"
            ),
        },
        {"role": "user", "content": question},
    ]
    return await run_turn(hub, messages, tools, extra={"read_skill_runbook": read_skill_runbook})


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
        bot.send_message(message["roomId"], "Sorry, I could not answer that right now.")
        return
    bot.send_message(message["roomId"], reply, is_markdown=True)
    log.info(f"Sent to {sender}: {reply}")


if __name__ == "__main__":
    bot = WebSocketClient(access_token=BOT_TOKEN, on_message=handle_message)
    log.info(f"Listening as {bot.me['emails'][0]} via WebSocket... (Ctrl+C to stop)")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")

