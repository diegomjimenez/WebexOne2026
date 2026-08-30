"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 03 - id chaining: use a book id from step 02 to list its entries.

import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webex")

load_dotenv()

TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")
CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")

for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")

ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-mcp-lab-03")


@mcp.tool()
async def list_address_books(limit: int = 50) -> dict:
    """List the address books configured in this Contact Center organization."""
    log.debug("list_address_books: GET %s/v3/address-book", ORG)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit}
        )
    log.debug("list_address_books: Webex responded HTTP %s", response.status_code)

    if response.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}

    books = [
        {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
        for book in response.json().get("data", [])
    ]
    return {"count": len(books), "address_books": books}


@mcp.tool()
async def list_entries(address_book_id: str, search: str = "") -> dict:
    """List the contacts inside one address book, optionally filtered by `search`.

    Pass the `address_book_id` returned by list_address_books.
    """
    params: dict = {"page": 0, "pageSize": 100}
    if search:
        params["search"] = search

    log.debug("list_entries: GET %s/v2/address-book/%s/entry", ORG, address_book_id)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v2/address-book/{address_book_id}/entry", headers=HEADERS, params=params
        )
    log.debug("list_entries: Webex responded HTTP %s", response.status_code)

    if response.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}

    entries = [
        {"id": entry.get("id"), "name": entry.get("name"), "number": entry.get("number")}
        for entry in response.json().get("data", [])
    ]
    return {"count": len(entries), "entries": entries}


if __name__ == "__main__":
    print(
        "webex-mcp-lab-03 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
