"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 09 - agent bot + MCP + skills: add Agent Skills on top of step 08.
# diff 08_agentbot.py 09_agentbot.py to see exactly what skills add.

import os, sys
from dotenv import load_dotenv
from webex_bot.models.command import Command
from webex_bot.webex_bot import WebexBot
import mcp_client
import skills_loader                                                      # NEW

load_dotenv()

# Load configuration from .env.
bot_token   = os.getenv("BOT_TOKEN")
domain      = os.getenv("DOMAIN")
SKILLS_DIR  = os.getenv("SKILLS_DIR",                                    # NEW
                         os.path.join(os.path.dirname(__file__), "skills"))# NEW
MODEL       = "gpt-4o-mini"
MAX_HISTORY = 20

# Stop early if credentials are missing.
for name, val in [("BOT_TOKEN", bot_token), ("DOMAIN", domain)]:
    if not val:
        sys.exit(f"ERROR: {name} is not set in .env")

# Connect to the MCP server (companion 06_full_server.py).
mcp_client.connect(
    command=os.getenv("MCP_SERVER_COMMAND", "python"),
    args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
    cwd=os.getenv("MCP_SERVER_CWD", "."),
)

# Discover skills at startup (only name + description loaded).             # NEW
skills = skills_loader.discover(SKILLS_DIR)                               # NEW
extra_tools = [skills_loader.tool_spec(skills)] if skills else []         # NEW
dispatch = {                                                              # NEW
    "load_skill": lambda a: skills_loader.load_skill(skills, a.get("name", ""))
}                                                                         # NEW

SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for managing "
    "Contact Center resources. Be concise."
    + skills_loader.catalog_prompt(skills)                                # NEW
)

# Per-user conversation history.
conversations: dict[str, list] = {}


# Chat command — MCP tools + skills in one agentic loop.
class ChatCommand(Command):
    def __init__(self):
        super().__init__(command_keyword="help",
                         help_message="Chat — I have MCP tools + Agent Skills.")
    def pre_execute(self, message, attachment_actions, activity):
        return "Thinking…"
    def execute(self, message, attachment_actions, activity):
        uid = activity["actor"]["emailAddress"]
        if not message or not message.strip():
            return "Type a message and I'll help."
        if uid not in conversations:
            conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversations[uid].append({"role": "user", "content": message.strip()})
        result = mcp_client.agentic_loop(                                 # NEW
            conversations[uid], model=MODEL,                              # NEW
            extra_tools=extra_tools, dispatch=dispatch,                    # NEW
        )                                                                 # NEW
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
bot = WebexBot(teams_bot_token=bot_token, bot_name="Agent Bot (Step 09)",
               approved_domains=domain, include_demo_commands=False,
               help_command=ChatCommand())
bot.add_command(ResetCommand())
bot.run()

# In production, swap the DIY skills loader for:
# deepagents SkillsMiddleware, AG2 SkillPlugin, MS Agent Framework, or skills-ref.
