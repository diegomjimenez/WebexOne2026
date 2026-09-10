"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# MCP Client module — tools + resources + prompts + ELICITATION.
# diff mcp_client_prompts.py mcp_client_full.py to see exactly what elicitation adds.

import asyncio, json, logging, sys, threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types                                       # NEW
from openai import OpenAI

log = logging.getLogger(__name__)
_openai = OpenAI()

# Module state, populated by connect().
_loop = None
_session = None
_tools = []
_resources_text = ""
_prompts = {}
_interactive = False                                                     # NEW


# Elicitation callback — the server asks the user a question mid-call.    NEW
async def _on_elicit(context, params):                                   # NEW
    message = getattr(params, "message", "Confirm?")                     # NEW
    if _interactive:                                                      # NEW
        answer = input(f"\n⚠ {message}\naccept? [y/N] ").strip().lower() # NEW
        action = "accept" if answer in ("y", "yes") else "decline"       # NEW
    else:                                                                 # NEW
        log.info("Auto-accept elicitation: %s "                          # NEW
                 "(production: use Adaptive Cards)", message)             # NEW
        action = "accept"                                                # NEW
    return mcp_types.ElicitResult(action=action, content={"ok": True})   # NEW


# Spawn the MCP server, initialize the session, discover tools, resources, and prompts.
def connect(command, args, cwd=".", timeout=30, interactive=False):
    global _loop, _session, _tools, _resources_text, _prompts
    global _interactive                                                  # NEW
    _interactive = interactive                                           # NEW
    error = None

    async def _run(params):
        nonlocal error
        global _session, _tools, _resources_text, _prompts
        try:
            async with stdio_client(params) as (r, w):
                async with ClientSession(                                # NEW
                    r, w,                                                 # NEW
                    elicitation_callback=_on_elicit,                      # NEW
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
          f"elicitation={'interactive' if _interactive else 'auto-accept'}",  # NEW
          file=sys.stderr)
    return _tools


# Return the concatenated resource text (empty string if none).
def get_resources_text():
    return _resources_text


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
        return asyncio.run_coroutine_threadsafe(_do(), _loop).result(timeout=30)
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
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    # Interactive mode — the demo asks you to confirm deletes at the console.
    connect(
        command=os.getenv("MCP_SERVER_COMMAND", "python"),
        args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
        cwd=os.getenv("MCP_SERVER_CWD", "."),
        interactive=True,                                                # NEW
    )
    print("\n--- Elicitation demo ---")
    print("Calling delete_address_book with a fake id to trigger elicitation.")
    print("The server will ask you to confirm. Type y or n.\n")
    result = call_tool("delete_address_book",
                       {"address_book_id": "demo-fake-id"})
    print(f"\nResult: {result}")
