"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Lab 8 — Naive bot: compose Lab 5/6/7 modules to troubleshoot address books.
Read operations work. Write operations with server-side elicitation
(e.g., update_desktop_profile) silently fail because Lab 6's McpClient
creates ClientSession without an elicitation_callback.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

LAB_ROOT = Path(__file__).resolve().parent.parent

# Import modules built in earlier labs — no rewriting.
sys.path.insert(0, str(LAB_ROOT / "05_bot"))
sys.path.insert(0, str(LAB_ROOT / "06_mcp_bot"))
sys.path.insert(0, str(LAB_ROOT / "07_skills_bot"))

from websocket_client import WebSocketClient          # Lab 5: Webex WebSocket
from mcp_client import McpClient                      # Lab 6: one-shot MCP sessions
from mcp_hub import McpHub                            # Lab 6: multi-server tool routing
from llm import as_openai_tools, run_turn             # Lab 6: agentic LLM loop
from skill_loader import SkillLoader                  # Lab 7: skill discovery

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MCP_SERVERS_DIR = str(LAB_ROOT / "webex-mcp-lab" / "mcp_servers")
ERROR_REPLY = "Sorry, I could not answer that right now. Please try again in a moment."

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("naive-bot")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("MODEL", "gpt-5-nano")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in your .env file")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")

# ── Local tool: Webex status check (no MCP, just a plain HTTP call) ────────
_STATUS_URL = "https://status.webex.com/status.json"


def check_webex_status() -> str:
    try:
        data = requests.get(_STATUS_URL, timeout=10).json()
        cc = [c for c in data.get("components", [])
              if "contact center" in c.get("name", "").lower()]
        cc_line = ", ".join(f"{c['name']}: {c['status']}" for c in cc) or "no data"
        indicator = data.get("status", {}).get("indicator", "unknown")
        incidents = [i["name"] for i in data.get("incidents", [])]
        inc_line = f"Active: {', '.join(incidents)}" if incidents else "No incidents"
        return f"CC: {cc_line}. Platform: {indicator}. {inc_line}."
    except Exception:
        return "Webex status unavailable."


STATUS_TOOL = {"type": "function", "function": {
    "name": "check_webex_status",
    "description": "Check the public Webex status page for platform or "
                   "Contact Center incidents. Call before investigating "
                   "agent configuration issues.",
    "parameters": {"type": "object", "properties": {}},
}}

# ── Connect to the two Contact Center MCP servers over stdio ───────────────
address_books = McpClient(
    command=sys.executable,
    args=["06_manage_address_books.py"],
    cwd=MCP_SERVERS_DIR,
)
desktop_profiles = McpClient(
    command=sys.executable,
    args=["07_verify_desktop_profiles.py"],
    cwd=MCP_SERVERS_DIR,
)

hub = McpHub([address_books, desktop_profiles])

# ── Load the troubleshoot skill ────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
loader = SkillLoader(os.path.join(SCRIPT_DIR, "skills"))
skill_summary = loader.get_all_skills_summary()


async def answer(question, sender):
    tools = as_openai_tools(await hub.list_tools()) + [STATUS_TOOL]
    log.info(f"Offering {len(tools)} tool(s) to {OPENAI_MODEL}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    skill_block = ""
    if skill_summary and skill_summary != "No skills loaded.":
        skill_block = (
            "\n\nAvailable Skills (runbooks). When relevant, ask the user which "
            "skill to follow, then load it and execute its steps:\n" + skill_summary
        )

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex Contact Center troubleshooting assistant "
                f"helping {sender}. Today is {today} (UTC). "
                "Answer only from tool results, never from memory. "
                "When a tool needs confirmation, call it directly."
                + skill_block
            ),
        },
        {"role": "user", "content": question},
    ]
    return await run_turn(
        hub, messages, tools,
        extra={"check_webex_status": lambda a: check_webex_status()},
    )


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
    log.info(f"Model: {OPENAI_MODEL}")
    log.info(f"Skills: {skill_summary}")
    log.info("NOTE: This bot uses Lab 6 one-shot MCP sessions. Read tools work; "
             "write tools with server-side elicitation will silently fail.")
    try:
        bot.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
