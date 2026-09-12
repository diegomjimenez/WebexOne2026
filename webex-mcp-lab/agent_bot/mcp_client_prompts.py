"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# MCP Client module — tools + resources + PROMPTS.
# diff mcp_client_resources.py mcp_client_prompts.py to see exactly what prompts add.

import asyncio, json, logging, sys, threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

log = logging.getLogger(__name__)
_openai = OpenAI()

# Module state, populated by connect().
_loop = None
_session = None
_tools = []
_resources_text = ""
_prompts = {}                                                            # NEW
_prompt_tools = []                                                       # NEW
_prompt_dispatch = {}                                                    # NEW


# Spawn the MCP server, initialize the session, discover tools, resources, and prompts.
def connect(command, args, cwd=".", timeout=30):
    global _loop, _session, _tools, _resources_text, _prompts             # NEW
    global _prompt_tools, _prompt_dispatch                               # NEW
    error = None

    async def _run(params):
        nonlocal error
        global _session, _tools, _resources_text, _prompts                # NEW
        global _prompt_tools, _prompt_dispatch                           # NEW
        try:
            async with stdio_client(params) as (r, w):
                async with ClientSession(r, w) as s:
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
                    # Discover prompts.                                       NEW
                    prompt_list = (await s.list_prompts()).prompts             # NEW
                    _prompts = {p.name: p for p in prompt_list}               # NEW
                    # Build meta-tools so the LLM can trigger prompts.        NEW
                    _prompt_tools = []                                         # NEW
                    _prompt_dispatch = {}                                      # NEW
                    for p in prompt_list:                                      # NEW
                        fname = f"prompt__{p.name}"                            # NEW
                        props = {a.name: {"type": "string"}                   # NEW
                                 for a in (p.arguments or [])}                # NEW
                        _prompt_tools.append({"type": "function", "function": # NEW
                            {"name": fname,                                   # NEW
                             "description": f"Activate workflow: "            # NEW
                                            f"{getattr(p, 'description', '') or p.name}",
                             "parameters": {"type": "object",                 # NEW
                                            "properties": props}}})           # NEW
                        def _make_handler(pname):                             # NEW
                            def handler(args):                                # NEW
                                r = get_prompt(pname, args)                   # NEW
                                if isinstance(r, list):                       # NEW
                                    return "\n".join(m["content"] for m in r) # NEW
                                return r                                      # NEW
                            return handler                                    # NEW
                        _prompt_dispatch[fname] = _make_handler(p.name)       # NEW
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
          f"{len(_prompts)} prompt(s)",                                  # NEW
          file=sys.stderr)
    return _tools


# Return the concatenated resource text (empty string if none).
def get_resources_text():
    return _resources_text


# OpenAI function specs for prompt meta-tools (pass as extra_tools).      NEW
def get_prompt_tools():                                                  # NEW
    return list(_prompt_tools)                                           # NEW


# Dispatch dict for prompt meta-tools (merge into dispatch).              NEW
def get_prompt_dispatch():                                               # NEW
    return dict(_prompt_dispatch)                                        # NEW


# Render a server prompt by name and return the messages list.            NEW
def get_prompt(name, arguments=None):                                    # NEW
    if name not in _prompts:                                             # NEW
        return f"[Prompt Error] Unknown prompt '{name}'. " \             # NEW
               f"Available: {', '.join(_prompts) or '(none)'}"          # NEW
    async def _do():                                                     # NEW
        result = await _session.get_prompt(name, arguments or {})        # NEW
        return [{"role": m.role, "content": m.content.text}              # NEW
                for m in result.messages                                  # NEW
                if hasattr(m.content, "text")]                           # NEW
    try:                                                                 # NEW
        return asyncio.run_coroutine_threadsafe(                         # NEW
            _do(), _loop).result(timeout=30)                             # NEW
    except Exception as exc:                                             # NEW
        return f"[Prompt Error] {exc}"                                   # NEW


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


# Standalone demo — run this file directly to see prompts in action.
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    connect(
        command=os.getenv("MCP_SERVER_COMMAND", "python"),
        args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
        cwd=os.getenv("MCP_SERVER_CWD", "."),
    )
    print("\n--- Available prompts ---")
    for name in _prompts:
        print(f"  {name}")
    print("\n--- Prompt meta-tools for LLM ---")
    for t in get_prompt_tools():
        print(f"  {t['function']['name']}: {t['function']['description'][:80]}")
    print("\n--- Rendered: set_up_address_book ---")
    result = get_prompt("set_up_address_book",
                        {"book_name": "Demo Team", "team": "support"})
    if isinstance(result, list):
        for msg in result:
            print(f"  [{msg['role']}] {msg['content'][:200]}")
    else:
        print(f"  {result}")
    print("\n--- Unknown prompt test ---")
    print(f"  {get_prompt('does_not_exist')}")
