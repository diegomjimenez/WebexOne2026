"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 07 - agent bot: plain LLM chat over Webex.
# No tools, no MCP, no skills. This is the base for steps 08 and 09.

import os, sys
from dotenv import load_dotenv
from openai import OpenAI
from webex_bot.models.command import Command
from webex_bot.webex_bot import WebexBot

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

openai_client = OpenAI()

SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for managing "
    "Contact Center resources. Be concise."
)

# Per-user conversation history.
conversations: dict[str, list] = {}


# Chat command — send messages to OpenAI and return the reply.
class ChatCommand(Command):
    def __init__(self):
        super().__init__(command_keyword="help",
                         help_message="Chat — ask me anything.")
    def pre_execute(self, message, attachment_actions, activity):
        return "Thinking…"
    def execute(self, message, attachment_actions, activity):
        uid = activity["actor"]["emailAddress"]
        if not message or not message.strip():
            return "Type a message and I'll help."
        if uid not in conversations:
            conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversations[uid].append({"role": "user", "content": message.strip()})
        resp = openai_client.chat.completions.create(
            model=MODEL, messages=conversations[uid],
        )
        result = resp.choices[0].message.content or ""
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
bot = WebexBot(teams_bot_token=bot_token, bot_name="Agent Bot (Step 07)",
               approved_domains=domain, include_demo_commands=False,
               help_command=ChatCommand())
bot.add_command(ResetCommand())
bot.run()
