"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 07 - capstone: prompt + resource + tools on the real Contact Center API.
# All three MCP primitives in one server. Logs go to 07_full_server.log only.

import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

_LOG_FILE = Path(__file__).parent / "07_full_server.log"
logging.basicConfig(
    filename=str(_LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
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
        sys.exit(f"{_name} is not set. See .env.example.")

ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-mcp-lab-07")


@mcp.prompt()
def set_up_address_book(book_name: str = "", team: str = "") -> str:
    """Set up an address book end to end: create it and add its first contacts."""
    log.debug("set_up_address_book prompt invoked (book_name=%r, team=%r)", book_name, team)
    return (
        f"Set up an address book called {book_name or '<book name>'} for the "
        f"{team or '<team>'} team.\n\n"
        "1. Read the webex://address-books/conventions resource and follow it.\n"
        "2. Call list_address_books first - reuse a matching book, do not duplicate.\n"
        "3. Otherwise call create_address_book and keep the id it returns.\n"
        "4. Ask me for the contacts to add (name and E.164 number each).\n"
        "5. Show me the list and, once I approve, call add_entry for each."
    )


@mcp.resource("webex://address-books/conventions")
def address_book_conventions() -> str:
    """House style for address books in this organization."""
    log.debug("address_book_conventions resource read")
    return (
        "# Address book conventions\n"
        "\n"
        "- Name a book for its team or purpose, e.g. 'Sales - EMEA', not 'Book1'.\n"
        "- Before creating a book, list existing books and reuse one if it fits.\n"
        "- Store numbers in E.164 format: +, country code, no spaces, e.g. +14155550101.\n"
        "- Give every entry a human name; never add a bare number.\n"
        "- Do not put internal notes or ticket ids in a contact's name field.\n"
    )


@mcp.tool()
async def list_address_books(limit: int = 50) -> dict:
    """List the address books configured in this Contact Center organization."""
    log.debug("list_address_books: GET %s/v3/address-book", ORG)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit})
    log.debug("list_address_books: HTTP %s", r.status_code)
    if r.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    books = [
        {"id": b.get("id"), "name": b.get("name"), "description": b.get("description")}
        for b in r.json().get("data", [])
    ]
    return {"count": len(books), "address_books": books}


@mcp.tool()
async def create_address_book(name: str, description: str = "") -> dict:
    """Create a new address book, following webex://address-books/conventions."""
    log.debug("create_address_book: POST %s/v3/address-book (name=%r)", ORG, name)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            f"{ORG}/v3/address-book", headers=HEADERS,
            json={"name": name, "description": description, "parentType": "ORGANIZATION"},
        )
    log.debug("create_address_book: HTTP %s", r.status_code)
    if r.status_code not in (200, 201):
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    book = r.json()
    return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}


@mcp.tool()
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
    """Add a contact to an address book. number should be E.164, e.g. +14155550101."""
    log.debug("add_entry: POST %s/address-book/%s/entry", ORG, address_book_id)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            f"{ORG}/address-book/{address_book_id}/entry", headers=HEADERS,
            json={"name": name, "number": number},
        )
    log.debug("add_entry: HTTP %s", r.status_code)
    if r.status_code not in (200, 201):
        return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
    return {"added": True, "entry_id": r.json().get("id"), "name": name}


if __name__ == "__main__":
    print(
        "webex-mcp-lab-07 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
