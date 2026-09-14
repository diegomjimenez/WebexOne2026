"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# MCP Client module — tools + resources + prompts + elicitation.
# Discovers everything from whatever MCP server it is pointed at; it holds no
# knowledge of any specific server.

import asyncio, json, logging, sys, threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types
from openai import OpenAI
from dotenv import load_dotenv

log = logging.getLogger(__name__)
load_dotenv()
_openai = OpenAI()

# Module state, populated by connect().
_loop = None
_session = None
_tools = []
_resources_text = ""
_prompts = {}
_prompt_tools = []
_prompt_dispatch = {}
_interactive = False
_elicit_bridge = None
_current_room = None


# Elicitation callback — the server asks the user a question mid-call.
async def _on_elicit(context, params):
    message = getattr(params, "message", "Confirm?")
    if _interactive:
        answer = input(f"\n⚠ {message}\naccept? [y/N] ").strip().lower()
        action = "accept" if answer in ("y", "yes") else "decline"
    elif _elicit_bridge:
        confirmed = _elicit_bridge.request(message)
        action = "accept" if confirmed else "decline"
    else:
        log.info("Auto-accept elicitation: %s "
                 "(no bridge, auto-accepting)", message)
        action = "accept"
    return mcp_types.ElicitResult(action=action, content={"ok": True})


# Spawn the MCP server, initialize the session, discover tools, resources, and prompts.
def connect(command, args, cwd=".", timeout=30, interactive=False):
    global _loop, _session, _tools, _resources_text, _prompts
    global _prompt_tools, _prompt_dispatch
    global _interactive
    _interactive = interactive
    error = None

    async def _run(params):
        nonlocal error
        global _session, _tools, _resources_text, _prompts
        global _prompt_tools, _prompt_dispatch
        try:
            async with stdio_client(params) as (r, w):
                async with ClientSession(
                    r, w,
                    elicitation_callback=_on_elicit,
                ) as s:
                    await s.initialize()
                    _session = s
                    _tools = [
                        {"type": "function", "function": {
                            "name": t.name,
                            "description": getattr(t, "description", "") or "",
                            "parameters": getattr(t, "inputSchema", None)
                                          or {"type": "object", "properties": {}},
                        }} for t in (await s.list_tools()).tools
                    ]
                    # Read every resource the server advertises.
                    resources = (await s.list_resources()).resources
                    parts = []
                    for r_info in resources:
                        content = await s.read_resource(r_info.uri)
                        for block in content.contents:
                            if hasattr(block, "text"):
                                parts.append(block.text)
                    _resources_text = "\n".join(parts)
                    # Discover prompts.
                    prompt_list = (await s.list_prompts()).prompts
                    _prompts = {p.name: p for p in prompt_list}
                    # Build meta-tools so the LLM can trigger prompts.
                    _prompt_tools = []
                    _prompt_dispatch = {}
                    for p in prompt_list:
                        fname = f"prompt__{p.name}"
                        props = {a.name: {"type": "string"}
                                 for a in (p.arguments or [])}
                        _prompt_tools.append({"type": "function", "function":
                            {"name": fname,
                             "description": f"Activate workflow: "
                                            f"{getattr(p, 'description', '') or p.name}",
                             "parameters": {"type": "object",
                                            "properties": props}}})
                        def _make_handler(pname):
                            def handler(args):
                                r = get_prompt(pname, args)
                                if isinstance(r, list):
                                    return "\n".join(m["content"] for m in r)
                                return r
                            return handler
                        _prompt_dispatch[fname] = _make_handler(p.name)
                    ready.set()
                    while True:
                        await asyncio.sleep(1)
        except Exception as exc:
            error = str(exc)
            ready.set()

    ready = threading.Event()
    params = StdioServerParameters(command=command, args=args, cwd=cwd)

    def _bg():
        global _loop
        _loop = asyncio.new_event_loop()
        _loop.run_until_complete(_run(params))

    threading.Thread(target=_bg, daemon=True).start()
    if not ready.wait(timeout) or _session is None:
        sys.exit(f"ERROR: MCP server failed — {error or 'timeout'}")
    print(f"MCP ready — {len(_tools)} tool(s), "
          f"{len(_resources_text)} chars of resource text, "
          f"{len(_prompts)} prompt(s), "
          f"elicitation={'interactive' if _interactive else 'auto-accept'}",
          file=sys.stderr)
    return _tools


# Return the concatenated resource text (empty string if none).
def get_resources_text():
    return _resources_text


# OpenAI function specs for prompt meta-tools (pass as extra_tools).
def get_prompt_tools():
    return list(_prompt_tools)


# Dispatch dict for prompt meta-tools (merge into dispatch).
def get_prompt_dispatch():
    return dict(_prompt_dispatch)


# Names of the prompts the connected server advertises.
def get_prompt_names():
    return list(_prompts)


# Register an elicit bridge (Adaptive Card) for bot mode.
def set_elicit_bridge(bridge):
    global _elicit_bridge
    _elicit_bridge = bridge


# Set the Webex room id for the next elicitation card.
def set_current_room(room_id):
    if _elicit_bridge:
        _elicit_bridge.set_room(room_id)


# Render a server prompt by name and return the messages list.
def get_prompt(name, arguments=None):
    if name not in _prompts:
        return f"[Prompt Error] Unknown prompt '{name}'. " \
               f"Available: {', '.join(_prompts) or '(none)'}"
    async def _do():
        result = await _session.get_prompt(name, arguments or {})
        return [{"role": m.role, "content": m.content.text}
                for m in result.messages
                if hasattr(m.content, "text")]
    try:
        return asyncio.run_coroutine_threadsafe(
            _do(), _loop).result(timeout=30)
    except Exception as exc:
        return f"[Prompt Error] {exc}"


# Call a single MCP tool synchronously.
def call_tool(name, args):
    async def _do():
        res = await _session.call_tool(name, args)
        return "\n".join(b.text for b in res.content if hasattr(b, "text")) or '{"ok":true}'
    try:
        # Timeout must exceed elicit.request()'s timeout (180s) so eliciting
        # tools return real results, not a spurious error.
        return asyncio.run_coroutine_threadsafe(_do(), _loop).result(timeout=210)
    except Exception as exc:
        return f"[Tool Error] {exc}"


# Agentic loop — LLM picks tools, we call them, repeat until text reply.
def agentic_loop(messages, model="gpt-4o-mini", max_iter=10,
                 extra_tools=None, dispatch=None):
    all_tools = list(_tools) + (extra_tools or [])
    msgs = list(messages)
    # Prepend resource context so the model knows the conventions.
    if _resources_text:
        msgs.insert(0, {"role": "system",
                         "content": _resources_text})
    for _ in range(max_iter):
        resp = _openai.chat.completions.create(
            model=model, messages=msgs, tools=all_tools or None,
        )
        choice = resp.choices[0]
        if not choice.message.tool_calls:
            return choice.message.content or ""
        msgs.append(choice.message.model_dump())
        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            if dispatch and tc.function.name in dispatch:
                result = dispatch[tc.function.name](args)
            else:
                log.info("MCP tool: %s(%s)", tc.function.name, args)
                result = call_tool(tc.function.name, args)
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    return "Hit tool-call limit — try a simpler request."


# Standalone demo — run this file directly to see elicitation in action.
# The server is resolved from .env; there is no hardcoded server default.
if __name__ == "__main__":
    import os
    load_dotenv()
    server_args = os.getenv("MCP_SERVER_ARGS", "")
    if not server_args:
        sys.exit(
            "ERROR: MCP_SERVER_ARGS is not set. Point it at an MCP server "
            "in .env (see .env.example), e.g. MCP_SERVER_ARGS=06_full_server.py"
        )
    # Interactive mode — the demo asks you to confirm risky actions at the console.
    connect(
        command=os.getenv("MCP_SERVER_COMMAND", "python"),
        args=server_args.split(","),
        cwd=os.getenv("MCP_SERVER_CWD", "."),
        interactive=True,
    )
    print("\n--- Elicitation demo ---")
    print("Calling a delete tool with a fake id to trigger elicitation.")
    print("The server will ask you to confirm. Type y or n.\n")
    result = call_tool("delete_address_book",
                       {"address_book_id": "demo-fake-id"})
    print(f"\nResult: {result}")
