"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 10 - agent bot + full MCP: tools, resources, prompts, and elicitation.
# diff 08_agentbot.py 10_agentbot.py to see exactly what the full client adds.

import os, sys
from dotenv import load_dotenv
from webex_bot.models.command import Command
from webex_bot.webex_bot import WebexBot
import mcp_client_full as mcp_client                                     # NEW
import elicit_bridge                                                     # NEW

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

# Connect to the MCP server (companion 06_full_server.py).
# interactive=False → elicitation auto-accepts (see Production Notes).
mcp_client.connect(
    command=os.getenv("MCP_SERVER_COMMAND", "python"),
    args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
    cwd=os.getenv("MCP_SERVER_CWD", "."),
    interactive=False,                                                   # NEW
)

# Wire the Adaptive Card elicitation bridge.                              NEW
elicit_bridge.init(bot_token)                                            # NEW
mcp_client.set_elicit_bridge(elicit_bridge)                              # NEW

# Expose MCP prompts as meta-tools the LLM can call.
prompt_tools = mcp_client.get_prompt_tools()                             # NEW
prompt_dispatch = mcp_client.get_prompt_dispatch()                       # NEW

# Build system prompt with server resource text (conventions, policies).
SYSTEM_PROMPT = (
    "You are a helpful Webex assistant for managing "
    "Contact Center resources. Be concise.\n\n"
    + mcp_client.get_resources_text()                                    # NEW
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
        # Handle Adaptive Card button taps (elicitation confirm/decline).  NEW
        if attachment_actions:                                            # NEW
            data = attachment_actions.inputs                              # NEW
            confirmed = data.get("action") == "confirm"                  # NEW
            elicit_bridge.resolve(data.get("elicit_id", ""), confirmed)  # NEW
            return "✓ Confirmed." if confirmed else "✗ Declined."        # NEW
        uid = activity["actor"]["emailAddress"]
        if not message or not message.strip():
            return "Type a message and I'll help."
        if uid not in conversations:
            conversations[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversations[uid].append({"role": "user", "content": message.strip()})
        # Set the room so the bridge can post cards here.                 NEW
        room_id = activity.get("target", {}).get("globalId", "")         # NEW
        mcp_client.set_current_room(room_id)                             # NEW
        result = mcp_client.agentic_loop(
            conversations[uid], model=MODEL,
            extra_tools=prompt_tools, dispatch=prompt_dispatch)
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
bot = WebexBot(teams_bot_token=bot_token, bot_name="Agent Bot (Step 10)",
               approved_domains=domain, include_demo_commands=False,
               help_command=ChatCommand())
bot.add_command(ResetCommand())
bot.run()
