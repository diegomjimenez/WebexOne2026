"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Test client for 03_list_entries.py - id chaining across two tool calls.
# Lists address books, picks the first id, then calls list_entries with it.
#
#     python mcp_clients/03_list_entries_client.py            # high-level output
#     python mcp_clients/03_list_entries_client.py --verbose   # + raw JSON-RPC frames

from __future__ import annotations

import json

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
    except Exception as exc:
        print(f"  Tool call failed: {exc}")
        return

    raw_text = ""
    for item in result.content:
        text = item.text if hasattr(item, "text") else str(item)
        print(f"  {text}")
        raw_text = text

    book_id = None
    try:
        data = json.loads(raw_text)
        books = data.get("address_books", [])
        if books:
            book_id = books[0].get("id")
    except (json.JSONDecodeError, AttributeError, IndexError):
        pass

    if not book_id:
        print("\n  No address books to chain into list_entries -- create one in step 04.")
        return

    banner(f"Call: list_entries (chained book_id={book_id[:12]}...)")
    try:
        result = await client.call_tool("list_entries", {"address_book_id": book_id})
        for item in result.content:
            print(f"  {item.text if hasattr(item, 'text') else item}")
    except Exception as exc:
        print(f"  Tool call failed: {exc}")


if __name__ == "__main__":
    run_client("03_list_entries.py", exercise, description="Test client for 03_list_entries.py (id chaining)")
