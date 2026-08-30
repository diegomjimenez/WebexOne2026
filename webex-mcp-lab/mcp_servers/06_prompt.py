"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 06 - the third primitive: a prompt (a starting point the user picks).

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

mcp = MCPServer("webex-mcp-lab-06")


@mcp.prompt()
def set_up_address_book(book_name: str = "", team: str = "") -> str:
    """Set up an address book end to end: create it and add its first contacts.

    Prompt arguments become fields the client asks the user to fill in. What
    this returns is not an answer - it is the opening message of a workflow
    the model then carries out with the tools below.
    """
    log.debug("set_up_address_book prompt invoked (book_name=%r, team=%r)", book_name, team)
    return (
        f"Set up an address book called {book_name or '<book name>'} for the "
        f"{team or '<team>'} team.\n"
        "\n"
        "1. Read the webex://address-books/conventions resource and follow it.\n"
        "2. Call list_address_books first - if a book for this team already\n"
        "   exists, use it instead of creating a duplicate.\n"
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
        "- Store numbers in E.164 format: a leading +, country code, no spaces,\n"
        "  e.g. +14155550101.\n"
        "- Give every entry a human name; never add a bare number.\n"
        "- Do not put internal notes or ticket ids in a contact's name field.\n"
    )


def _fail(response: httpx.Response) -> dict:
    """Turn an HTTP failure into a sentence the model can pass on to the user."""
    log.debug("Contact Center request failed: HTTP %s", response.status_code)
    if response.status_code == 401:
        return {"error": "Webex rejected the token. Check that it has not expired."}
    if response.status_code == 403:
        return {"error": "The token lacks Contact Center config permission (cjp:config_write)."}
    if response.status_code == 404:
        return {"error": "No such address book in this organization."}
    if response.status_code == 429:
        return {"error": "Rate limited by Webex. Wait a moment and try again."}
    return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}


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
        return _fail(response)

    books = [
        {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
        for book in response.json().get("data", [])
    ]
    return {"count": len(books), "address_books": books}


@mcp.tool()
async def create_address_book(name: str, description: str = "") -> dict:
    """Create a new address book, following webex://address-books/conventions.

    Returns its id, which add_entry then needs. The MCP client asks the user
    for approval before this runs.
    """
    log.debug("create_address_book: POST %s/v3/address-book (name=%r)", ORG, name)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(
            f"{ORG}/v3/address-book",
            headers=HEADERS,
            json={"name": name, "description": description, "parentType": "ORGANIZATION"},
        )
    log.debug("create_address_book: Webex responded HTTP %s", response.status_code)

    if response.status_code not in (200, 201):
        return _fail(response)

    book = response.json()
    return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}


@mcp.tool()
async def list_entries(address_book_id: str, search: str = "") -> dict:
    """List the contacts inside one address book, optionally filtered by `search`."""
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
        return _fail(response)

    entries = [
        {"id": entry.get("id"), "name": entry.get("name"), "number": entry.get("number")}
        for entry in response.json().get("data", [])
    ]
    return {"count": len(entries), "entries": entries}


@mcp.tool()
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
    """Add a contact to an address book, following webex://address-books/conventions.

    `number` should be E.164, e.g. +14155550101. `address_book_id` is what
    create_address_book returned. The MCP client asks the user for approval
    before this runs.
    """
    log.debug("add_entry: POST %s/address-book/%s/entry", ORG, address_book_id)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(
            f"{ORG}/address-book/{address_book_id}/entry",
            headers=HEADERS,
            json={"name": name, "number": number},
        )
    log.debug("add_entry: Webex responded HTTP %s", response.status_code)

    if response.status_code not in (200, 201):
        return _fail(response)

    return {"added": True, "entry_id": response.json().get("id"), "name": name}


if __name__ == "__main__":
    print(
        "webex-mcp-lab-06 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
