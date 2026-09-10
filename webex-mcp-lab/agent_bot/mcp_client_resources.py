"""
Cisco Live 2026 - LABCOL-1007: Building Your First Webex Bot

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# MCP Client module — tools + RESOURCES.
# diff mcp_client.py mcp_client_resources.py to see exactly what resources add.

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
_resources_text = ""                                                     # NEW


# Spawn the MCP server, initialize the session, discover tools and resources.
def connect(command, args, cwd=".", timeout=30):
    global _loop, _session, _tools, _resources_text                      # NEW
    error = None

    async def _run(params):
        nonlocal error
        global _session, _tools, _resources_text                         # NEW
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
                    # Read every resource the server advertises.              NEW
                    resources = (await s.list_resources()).resources           # NEW
                    parts = []                                                # NEW
                    for r_info in resources:                                   # NEW
                        content = await s.read_resource(r_info.uri)           # NEW
                        for block in content.contents:                        # NEW
                            if hasattr(block, "text"):                        # NEW
                                parts.append(block.text)                      # NEW
                    _resources_text = "\n".join(parts)                        # NEW
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
    print(f"MCP ready — {len(_tools)} tool(s), "                        # NEW
          f"{len(_resources_text)} chars of resource text",              # NEW
          file=sys.stderr)
    return _tools


# Return the concatenated resource text (empty string if none).          NEW
def get_resources_text():                                                # NEW
    return _resources_text                                               # NEW


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
    # Prepend resource context so the model knows the conventions.        NEW
    if _resources_text:                                                   # NEW
        msgs.insert(0, {"role": "system",                                # NEW
                         "content": _resources_text})                     # NEW
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


# Standalone demo — run this file directly to see resources in action.
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    connect(
        command=os.getenv("MCP_SERVER_COMMAND", "python"),
        args=os.getenv("MCP_SERVER_ARGS", "06_full_server.py").split(","),
        cwd=os.getenv("MCP_SERVER_CWD", "."),
    )
    print("\n--- Resources text ---")
    print(get_resources_text() or "(no resources)")
