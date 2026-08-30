"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Test client for 05_resource.py - exercises resources AND tools.
# Lists resources, reads the first one, lists tools, calls list_address_books.
#
#     python mcp_clients/05_resource_client.py            # high-level output
#     python mcp_clients/05_resource_client.py --verbose  # + raw JSON-RPC frames

from __future__ import annotations

from mcp import Client

from run_client import banner, run_client


async def exercise(client: Client) -> None:
    banner("Resources")
    resources = await client.list_resources()
    for r in resources.resources:
        print(f"  {r.uri}")

    if resources.resources:
        uri = str(resources.resources[0].uri)
        banner(f"Resource: {uri}")
        content = await client.read_resource(uri)
        for item in content.contents:
            print(f"  {item.text if hasattr(item, 'text') else item}")

    banner("Tools")
    tools = await client.list_tools()
    for t in tools.tools:
        print(f"  {t.name}: {t.description[:80] if t.description else ''}")

    banner("Call: list_address_books")
    try:
        result = await client.call_tool("list_address_books", {"limit": 5})
        for item in result.content:
            print(f"  {item.text if hasattr(item, 'text') else item}")
    except Exception as exc:
        print(f"  Tool call failed: {exc}")


if __name__ == "__main__":
    run_client("05_resource.py", exercise, description="Test client for 05_resource.py")
