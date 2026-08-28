"""Throwaway verification harness. Not part of the lab; deleted before delivery.

Connects to a numbered script over stdio as a real MCP client would, and prints
the tools, resources, and prompts it advertises.

    python _check.py 01_hello_mcp.py
    python _check.py 02_list_books.py --call list_address_books
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters, stdio_client


async def main() -> None:
    script = sys.argv[1]
    call = None
    if "--call" in sys.argv:
        call = sys.argv[sys.argv.index("--call") + 1]

    # The SDK gives the child a minimal environment by default, so the token
    # has to be handed over explicitly - exactly as an MCP client config does.
    params = StdioServerParameters(command=sys.executable, args=[script], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            info = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
            print(f"server: {info.name} {info.version}")

            tools = await session.list_tools()
            print(f"tools ({len(tools.tools)}):")
            for tool in tools.tools:
                raw = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", {})
                schema = raw.get("properties", {})
                first_line = (tool.description or "").strip().splitlines()
                print(f"  - {tool.name}({', '.join(schema)}): {first_line[0] if first_line else ''}")

            for label, fetch in (("resources", session.list_resources), ("prompts", session.list_prompts)):
                try:
                    result = await fetch()
                    items = getattr(result, label)
                    if items:
                        print(f"{label} ({len(items)}):")
                        for item in items:
                            print(f"  - {getattr(item, 'uri', None) or item.name}")
                except Exception as exc:
                    print(f"{label}: none ({type(exc).__name__})")

            if call:
                print(f"\ncalling {call}...")
                result = await session.call_tool(call, {})
                for block in result.content:
                    print(json.dumps(getattr(block, "text", str(block))[:800], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
