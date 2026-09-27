"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# MCP Client module — tools + resources + prompts + elicitation.
# Discovers everything from whatever MCP server(s) it is pointed at; it holds
# no knowledge of any specific server.
#
# Supports two modes:
#   1. Single-server: call connect() — works exactly like the original module.
#   2. Multi-server:  call connect_all() — merges tools/resources from N servers
#      and routes tool calls to the owning server automatically.

import asyncio, json, logging, sys, threading
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types
from openai import OpenAI
from dotenv import load_dotenv

log = logging.getLogger(__name__)
load_dotenv()
_openai = OpenAI()


class MCPConnection:
    """Encapsulates a single MCP server session with its tools, resources,
    prompts, and elicitation state."""

    def __init__(self):
        self._loop = None
        self._session = None
        self._tools = []
        self._resources_text = ""
        self._prompts = {}
        self._prompt_tools = []
        self._prompt_dispatch = {}
        self._interactive = False
        self._elicit_bridge = None
        self._current_room = None

    async def _on_elicit(self, context, params):
        message = getattr(params, "message", "Confirm?")
        if self._interactive:
            answer = input(f"\n⚠ {message}\naccept? [y/N] ").strip().lower()
            action = "accept" if answer in ("y", "yes") else "decline"
        elif self._elicit_bridge:
            confirmed = self._elicit_bridge.request(message)
            action = "accept" if confirmed else "decline"
        else:
            log.info("Auto-accept elicitation: %s "
                     "(no bridge, auto-accepting)", message)
            action = "accept"
        return mcp_types.ElicitResult(action=action, content={"ok": True})

    def connect(self, command, args, cwd=".", timeout=30, interactive=False):
        self._interactive = interactive
        error = None

        async def _run(params):
            nonlocal error
            try:
                async with stdio_client(params) as (r, w):
                    async with ClientSession(
                        r, w,
                        elicitation_callback=self._on_elicit,
                    ) as s:
                        await s.initialize()
                        self._session = s
                        self._tools = [
                            {"type": "function", "function": {
                                "name": t.name,
                                "description": getattr(t, "description", "") or "",
                                "parameters": getattr(t, "inputSchema", None)
                                              or {"type": "object", "properties": {}},
                            }} for t in (await s.list_tools()).tools
                        ]
                        resources = (await s.list_resources()).resources
                        parts = []
                        for r_info in resources:
                            content = await s.read_resource(r_info.uri)
                            for block in content.contents:
                                if hasattr(block, "text"):
                                    parts.append(block.text)
                        self._resources_text = "\n".join(parts)
                        prompt_list = (await s.list_prompts()).prompts
                        self._prompts = {p.name: p for p in prompt_list}
                        self._prompt_tools = []
                        self._prompt_dispatch = {}
                        for p in prompt_list:
                            fname = f"prompt__{p.name}"
                            props = {a.name: {"type": "string"}
                                     for a in (p.arguments or [])}
                            self._prompt_tools.append({"type": "function", "function":
                                {"name": fname,
                                 "description": f"Activate workflow: "
                                                f"{getattr(p, 'description', '') or p.name}",
                                 "parameters": {"type": "object",
                                                "properties": props}}})
                            def _make_handler(pname, conn):
                                def handler(args):
                                    r = conn.get_prompt(pname, args)
                                    if isinstance(r, list):
                                        return "\n".join(m["content"] for m in r)
                                    return r
                                return handler
                            self._prompt_dispatch[fname] = _make_handler(p.name, self)
                        ready.set()
                        while True:
                            await asyncio.sleep(1)
            except Exception as exc:
                error = str(exc)
                ready.set()

        ready = threading.Event()
        params = StdioServerParameters(command=command, args=args, cwd=cwd)

        def _bg():
            self._loop = asyncio.new_event_loop()
            self._loop.run_until_complete(_run(params))

        threading.Thread(target=_bg, daemon=True).start()
        if not ready.wait(timeout) or self._session is None:
            sys.exit(f"ERROR: MCP server failed — {error or 'timeout'}")
        print(f"MCP ready — {len(self._tools)} tool(s), "
              f"{len(self._resources_text)} chars of resource text, "
              f"{len(self._prompts)} prompt(s), "
              f"elicitation={'interactive' if self._interactive else 'auto-accept'}",
              file=sys.stderr)
        return self._tools

    @property
    def tools(self):
        return list(self._tools)

    @property
    def tool_names(self):
        return {t["function"]["name"] for t in self._tools}

    def get_resources_text(self):
        return self._resources_text

    def get_prompt_tools(self):
        return list(self._prompt_tools)

    def get_prompt_dispatch(self):
        return dict(self._prompt_dispatch)

    def get_prompt_names(self):
        return list(self._prompts)

    def set_elicit_bridge(self, bridge):
        self._elicit_bridge = bridge

    def set_current_room(self, room_id):
        if self._elicit_bridge:
            self._elicit_bridge.set_room(room_id)

    def get_prompt(self, name, arguments=None):
        if name not in self._prompts:
            return (f"[Prompt Error] Unknown prompt '{name}'. "
                    f"Available: {', '.join(self._prompts) or '(none)'}")
        async def _do():
            result = await self._session.get_prompt(name, arguments or {})
            return [{"role": m.role, "content": m.content.text}
                    for m in result.messages
                    if hasattr(m.content, "text")]
        try:
            return asyncio.run_coroutine_threadsafe(
                _do(), self._loop).result(timeout=30)
        except Exception as exc:
            return f"[Prompt Error] {exc}"

    def call_tool(self, name, args):
        async def _do():
            res = await self._session.call_tool(name, args)
            return "\n".join(
                b.text for b in res.content if hasattr(b, "text")
            ) or '{"ok":true}'
        try:
            return asyncio.run_coroutine_threadsafe(
                _do(), self._loop).result(timeout=210)
        except Exception as exc:
            return f"[Tool Error] {exc}"


# ---------------------------------------------------------------------------
# Module-level state — populated by connect() or connect_all().
# ---------------------------------------------------------------------------
_default = MCPConnection()
_connections: dict[str, MCPConnection] = {}
_tool_to_conn: dict[str, MCPConnection] = {}
_tools: list = []
_resources_text: str = ""
_prompts: dict = {}
_prompt_tools: list = []
_prompt_dispatch: dict = {}


def _rebuild_merged_state():
    """Rebuild module-level merged state from all connections."""
    global _tools, _resources_text, _prompts, _prompt_tools, _prompt_dispatch
    global _tool_to_conn
    _tools = []
    _tool_to_conn = {}
    all_resources = []
    _prompts = {}
    _prompt_tools = []
    _prompt_dispatch = {}
    for conn in _connections.values():
        for t in conn.tools:
            tname = t["function"]["name"]
            if tname not in _tool_to_conn:
                _tools.append(t)
                _tool_to_conn[tname] = conn
        if conn.get_resources_text():
            all_resources.append(conn.get_resources_text())
        _prompts.update(dict(zip(conn.get_prompt_names(),
                                 [conn] * len(conn.get_prompt_names()))))
        _prompt_tools.extend(conn.get_prompt_tools())
        _prompt_dispatch.update(conn.get_prompt_dispatch())
    _resources_text = "\n".join(all_resources)


# ---------------------------------------------------------------------------
# Single-server API (backwards-compatible).
# ---------------------------------------------------------------------------
def connect(command, args, cwd=".", timeout=30, interactive=False):
    global _connections
    _default.connect(command, args, cwd, timeout, interactive)
    _connections = {"default": _default}
    _rebuild_merged_state()
    return _tools


# ---------------------------------------------------------------------------
# Multi-server API.
# ---------------------------------------------------------------------------
def connect_all(configs, timeout=30, interactive=False):
    """Connect to multiple MCP servers.

    configs: list of {"name": str, "command": str, "args": list[str], "cwd": str}
    Returns: dict mapping name → MCPConnection.
    """
    global _connections
    _connections = {}
    for cfg in configs:
        conn = MCPConnection()
        conn.connect(
            command=cfg.get("command", "python"),
            args=cfg["args"],
            cwd=cfg.get("cwd", "."),
            timeout=timeout,
            interactive=interactive,
        )
        _connections[cfg["name"]] = conn
    _rebuild_merged_state()
    return dict(_connections)


# ---------------------------------------------------------------------------
# Module-level convenience functions (delegate to merged state / routing).
# ---------------------------------------------------------------------------
def get_resources_text():
    return _resources_text


def get_prompt_tools():
    return list(_prompt_tools)


def get_prompt_dispatch():
    return dict(_prompt_dispatch)


def get_prompt_names():
    return list(_prompts)


def set_elicit_bridge(bridge):
    for conn in _connections.values():
        conn.set_elicit_bridge(bridge)


def set_current_room(room_id):
    for conn in _connections.values():
        conn.set_current_room(room_id)


def call_tool(name, args):
    conn = _tool_to_conn.get(name)
    if conn is None:
        return f"[Tool Error] Unknown tool '{name}'."
    log.info("MCP tool: %s(%s) → %s", name, args,
             next((n for n, c in _connections.items() if c is conn), "?"))
    return conn.call_tool(name, args)


def get_prompt(name, arguments=None):
    conn = _prompts.get(name)
    if conn is None:
        return (f"[Prompt Error] Unknown prompt '{name}'. "
                f"Available: {', '.join(_prompts) or '(none)'}")
    return conn.get_prompt(name, arguments)


# Agentic loop — LLM picks tools, we call them, repeat until text reply.
def agentic_loop(messages, model, max_iter=10,
                 extra_tools=None, dispatch=None):
    all_tools = list(_tools) + (extra_tools or [])
    msgs = list(messages)
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
            "in .env (see .env.example), e.g. MCP_SERVER_ARGS=06_manage_address_books.py"
        )
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
