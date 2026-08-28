"""Step 05 - the third primitive: a prompt.

New in this step: `set_up_address_book`, registered with @mcp.prompt.

Now all three primitives are in one file, and the split is worth naming:

    tool      the model decides to call it        an action
    resource  the client attaches it              reference material
    prompt    the *user* picks it from a menu     a starting point

A prompt is a pre-written request, usually surfaced as a slash command or a menu
item. It is the one primitive a human triggers directly. This one packages the
whole "set up an address book" workflow - read the conventions, avoid a
duplicate, create the book, add the contacts - so a user can start it without
knowing any of the steps.

Same three credentials as step 02.

Run it:
    python 05_prompt.py
"""

import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

# Server-side logging -> stderr AND a file beside this script (05_prompt.log),
# one shared format, DEBUG by default. stdout carries the MCP protocol, so logs
# never go there. The token and a contact's number are never logged.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
for _handler in (
    logging.StreamHandler(sys.stderr),
    logging.FileHandler(Path(__file__).with_suffix(".log"), encoding="utf-8"),
):
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(_handler)

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
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

mcp = MCPServer("webex-mcp-lab-05")


@mcp.prompt()
def set_up_address_book(book_name: str = "", team: str = "") -> str:
    """Set up an address book end to end: create it and add its first contacts.

    The arguments become fields the client asks the user to fill in. What this
    returns is not an answer - it is the opening message of a conversation,
    which the model then carries out using the tools below.
    """
    # A prompt is triggered by the user. This line lets you see that happen, and
    # with which fields, before any tool runs.
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
        for book in response.json().get("items", [])
    ]
    return {"count": len(books), "address_books": books}


@mcp.tool()
async def create_address_book(name: str, description: str = "") -> dict:
    """Create a new address book, following the webex://address-books/conventions resource.

    Returns its id, which add_entry then needs. Your MCP client asks for
    approval before this runs.
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
        for entry in response.json().get("items", [])
    ]
    return {"count": len(entries), "entries": entries}


@mcp.tool()
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
    """Add a contact to an address book, following the webex://address-books/conventions resource.

    `number` should be E.164, e.g. +14155550101. `address_book_id` is the id
    create_address_book returned. Your MCP client asks for approval before this runs.
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
    # A one-line banner to stderr so the terminal shows the server is alive.
    # It must go to stderr, not stdout - stdout carries the MCP protocol.
    print("webex-mcp-lab-05 running on stdio - waiting for a client (Ctrl+C to stop).",
          file=sys.stderr)
    mcp.run()
