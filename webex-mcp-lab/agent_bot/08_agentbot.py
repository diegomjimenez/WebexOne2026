"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 08 - agent bot + MCP: connect to 06_full_server.py via mcp_client module.
# diff 07_agentbot.py 08_agentbot.py to see exactly what MCP adds.

import os, sys
from dotenv import load_dotenv
from webex_bot.models.command import Command
from webex_bot.webex_bot import WebexBot
import mcp_client                                                        # NEW

load_dotenv()

# Load configuration from .env.
bot_token   = os.getenv("BOT_TOKEN")
domain      = os.getenv("DOMAIN")
MODEL       = "gpt-4o-mini"
MAX_HISTORY = 20

# Stop early if credentials are missing.
for name, val in [("BOT_TOKEN", bot_token), ("DOMAIN", domain)]:
    if not val:
        sys.exit(f"ERROR: {name} is not set in .env")

# Connect to the MCP server (companion 06_full_server.py).                # NEW
mcp_client.connect(                                                       # NEW
    command=os.getenv("MCP_SERVER_COMMAND", "python"),                     # NEW
    args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),    # NEW
    cwd=os.getenv("MCP_SERVER_CWD", "."),                                 # NEW
)                                                                         # NEW

SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for managing "
    "Contact Center resources. Be concise."
)

# Per-user conversation history.
conversations: dict[str, list] = {}


# Chat command — send messages through the MCP agentic loop.
class ChatCommand(Command):
    def __init__(self):
        super().__init__(command_keyword="help",
                         help_message="Chat — I can query your Contact Center via MCP.")
    def pre_execute(self, message, attachment_actions, activity):
        return "Thinking…"
    def execute(self, message, attachment_actions, activity):
        uid = activity["actor"]["emailAddress"]
        if not message or not message.strip():
            return "Type a message and I'll help."
        if uid not in conversations:
            conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversations[uid].append({"role": "user", "content": message.strip()})
        result = mcp_client.agentic_loop(conversations[uid], model=MODEL)  # NEW
        conversations[uid].append({"role": "assistant", "content": result})
        while len(conversations[uid]) > 1 + MAX_HISTORY * 2:
            conversations[uid].pop(1); conversations[uid].pop(1)
        return result[:7000]


# Reset command — clear conversation history.
class ResetCommand(Command):
    def __init__(self):
        super().__init__(command_keyword="reset", help_message="Clear history",
                         exact_command_keyword_match=True)
    def execute(self, message, attachment_actions, activity):
        conversations.pop(activity["actor"]["emailAddress"], None)
        return "History cleared."


# Start the bot.
bot = WebexBot(teams_bot_token=bot_token, bot_name="Agent Bot (Step 08)",
               approved_domains=domain, include_demo_commands=False,
               help_command=ChatCommand())
bot.add_command(ResetCommand())
bot.run()
