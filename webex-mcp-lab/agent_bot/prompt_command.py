"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Importable /setup command — triggers an MCP prompt as an explicit slash command.
# Usage in your bot:
#   import prompt_command
#   prompt_command.init(mcp_client, conversations, SYSTEM_PROMPT, MODEL, MAX_HISTORY)
#   bot.add_command(prompt_command.SetupCommand())   # webex_bot
#   reply = prompt_command.run(uid, user_msg, room_id)  # any transport

from webex_bot.models.command import Command

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
    """Load the set_up_address_book prompt, run the agentic loop, return reply."""
    if uid not in _convos:
        _convos[uid] = [{"role": "system", "content": _system}]
    result = _mcp.get_prompt("set_up_address_book",
                             {"book_name": "", "team": ""})
    if isinstance(result, list):
        workflow = "\n".join(m["content"] for m in result)
    else:
        workflow = result
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


class SetupCommand(Command):
    """Slash command: /setup — triggers the set_up_address_book prompt."""

    def __init__(self):
        super().__init__(command_keyword="setup",
                         help_message="/setup — guided address-book setup workflow",
                         exact_command_keyword_match=False)

    def pre_execute(self, message, attachment_actions, activity):
        return "Thinking…"

    def execute(self, message, attachment_actions, activity):
        uid = activity["actor"]["emailAddress"]
        user_msg = message.strip() if message and message.strip() else ""
        room_id = activity.get("target", {}).get("globalId", "")
        return run(uid, user_msg, room_id)
