"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Test client for 02_list_books.py - list tools and call list_address_books.
# Needs the same .env credentials as 02_list_books.py.
#
#     python mcp_clients/02_list_books_client.py            # high-level output
#     python mcp_clients/02_list_books_client.py --verbose   # + raw JSON-RPC frames

from __future__ import annotations

from mcp import Client

from run_client import banner, run_client


async def exercise(client: Client) -> None:
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
    run_client("02_list_books.py", exercise, description="Test client for 02_list_books.py")
