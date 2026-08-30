"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Test client for 01_hello_mcp.py - the simplest MCP exchange. No credentials.
#
#     python mcp_clients/01_hello_mcp_client.py            # high-level output
#     python mcp_clients/01_hello_mcp_client.py --verbose   # + raw JSON-RPC frames

from __future__ import annotations

from mcp import Client

from run_client import banner, run_client


async def exercise(client: Client) -> None:
    banner("Tools")
    tools = await client.list_tools()
    for t in tools.tools:
        print(f"  {t.name}: {t.description[:80] if t.description else ''}")

    banner("Call: greet")
    result = await client.call_tool("greet", {"name": "Lab"})
    for item in result.content:
        print(f"  {item.text if hasattr(item, 'text') else item}")


if __name__ == "__main__":
    run_client("01_hello_mcp.py", exercise, description="Test client for 01_hello_mcp.py")
