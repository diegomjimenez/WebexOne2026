"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Configurable slash command — triggers an MCP prompt as an explicit command.
# Which prompt it triggers and under which keyword are read from .env, so the
# same command works against any MCP server:
#   SETUP_COMMAND_KEYWORD  (default "setup")  → the "/setup" style keyword
#   SETUP_PROMPT_NAME       (default "")       → the server prompt to activate
#   SETUP_PROMPT_ARGS       (default "{}")     → JSON default arguments
#
# Usage in your bot:
#   from utils import commands
#   commands.init(mcp_client, conversations, SYSTEM_PROMPT, MODEL, MAX_HISTORY)
#   reply = commands.run(uid, user_msg, room_id)   # any transport

import json
import os

from dotenv import load_dotenv

load_dotenv()

# Command configuration (server-agnostic, from .env).
KEYWORD = os.getenv("SETUP_COMMAND_KEYWORD", "setup").strip().lstrip("/")
PROMPT_NAME = os.getenv("SETUP_PROMPT_NAME", "").strip()
try:
    PROMPT_ARGS = json.loads(os.getenv("SETUP_PROMPT_ARGS", "{}") or "{}")
except (ValueError, TypeError):
    PROMPT_ARGS = {}

_mcp = None
_convos = None
_system = ""
_model = "gpt-4o-mini"
_max_history = 20


def init(mcp_client, conversations, system_prompt, model, max_history=20):
    global _mcp, _convos, _system, _model, _max_history
    _mcp = mcp_client
    _convos = conversations
    _system = system_prompt
    _model = model
    _max_history = max_history


def run(uid, user_msg="", room_id=""):
    """Load the configured prompt, run the agentic loop, return the reply.

    If no prompt is configured, or the configured prompt is not offered by the
    connected server, return an explanatory message instead of a broken flow.
    """
    if not PROMPT_NAME:
        return (f"No prompt is configured for /{KEYWORD}. "
                f"Set SETUP_PROMPT_NAME in .env to a prompt the server offers.")

    # get_prompt returns a messages list on success, or an error string
    # (including the "Unknown prompt … Available: …" message) on failure.
    result = _mcp.get_prompt(PROMPT_NAME, PROMPT_ARGS)
    if isinstance(result, str):
        return result[:7000]
    workflow = "\n".join(m["content"] for m in result)

    if uid not in _convos:
        _convos[uid] = [{"role": "system", "content": _system}]
    instruction = f"Follow this workflow:\n{workflow}"
    if user_msg:
        instruction += f"\n\nUser context: {user_msg}"
    _convos[uid].append({"role": "user", "content": instruction})
    _mcp.set_current_room(room_id)
    reply = _mcp.agentic_loop(_convos[uid], model=_model)
    _convos[uid].append({"role": "assistant", "content": reply})
    while len(_convos[uid]) > 1 + _max_history * 2:
        _convos[uid].pop(1); _convos[uid].pop(1)
    return reply[:7000]


# Optional webex_bot framework integration (not required by the WebSocket bot).
try:
    from webex_bot.models.command import Command

    class SetupCommand(Command):
        """Slash command that triggers the configured MCP prompt."""

        def __init__(self):
            super().__init__(
                command_keyword=KEYWORD,
                help_message=f"/{KEYWORD} — run the configured prompt workflow",
                exact_command_keyword_match=False,
            )

        def pre_execute(self, message, attachment_actions, activity):
            return "Thinking…"

        def execute(self, message, attachment_actions, activity):
            uid = activity["actor"]["emailAddress"]
            user_msg = message.strip() if message and message.strip() else ""
            room_id = activity.get("target", {}).get("globalId", "")
            return run(uid, user_msg, room_id)

except ImportError:  # webex_bot is optional
    SetupCommand = None
