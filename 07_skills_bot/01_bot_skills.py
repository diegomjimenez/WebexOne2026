import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure we can import from 06_mcp_bot and 05_bot
LAB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB_ROOT / "06_mcp_bot"))
sys.path.insert(0, str(LAB_ROOT / "05_bot"))

from llm import as_openai_tools, run_turn
from mcp_hub import McpHub
from mcp_client import McpClient
from websocket_client import WebSocketClient
from skill_loader import SkillLoader

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-skills-bot")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise SystemExit("Set BOT_TOKEN and OPENAI_API_KEY in your .env file")

# Load Skills
skills_dir = Path(__file__).resolve().parent / "skills"
skill_loader = SkillLoader(skills_dir)
log.info(f"Loaded {len(skill_loader.skills)} skill(s).")

# Define the local tool for reading skills
READ_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "read_skill_runbook",
        "description": "Read the full instructions for a specific skill/runbook.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The name of the skill to read (e.g., 'troubleshoot-status').",
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
    return f"Skill '{skill_name}' not found."

# Setup MCP Hub
CUSTOM_SERVER = LAB_ROOT / "03_custom_mcp" / "06_calling_hub.py"
custom = McpClient(
    command=sys.executable,
    args=[str(CUSTOM_SERVER)],
    cwd=str(LAB_ROOT),
)

hub = McpHub([
    ("https://mcp.webexapis.com/mcp/webex-messaging", MESSAGING_TOKEN),
    ("https://mcp.webexapis.com/mcp/webex-meeting", MEETING_TOKEN),
    custom,
])

async def answer(question, sender, room_id):
    tools = as_openai_tools(await hub.list_tools()) + [READ_SKILL_TOOL]
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Inject the skills summary into the system prompt
    skills_summary = skill_loader.get_all_skills_summary()
    
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a Webex assistant helping {sender}. Today is {today} (UTC). "
                "Answer only from tool results, never from memory. "
                "You have access to several operational runbooks (Skills). "
                "If a user's request matches a skill, call read_skill_runbook to get the instructions, "
                "and strictly follow those instructions.\n\n"
                f"{skills_summary}"
            ),
        },
        {"role": "user", "content": question},
    ]
    
    reply = await run_turn(hub, messages, tools, extra={"read_skill_runbook": read_skill_runbook})
    return reply

def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text:
        return

    sender = message["personEmail"]
    log.info(f"Received from {sender}: {text}")
    asyncio.create_task(reply_with_assistant(message, sender, text))

async def reply_with_assistant(message, sender, question):
    try:
        reply = await answer(question, sender, message["roomId"])
    except Exception as e:
        log.exception("Assistant turn failed")
        bot.send_message(message["roomId"], "Sorry, I encountered an error.")
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
