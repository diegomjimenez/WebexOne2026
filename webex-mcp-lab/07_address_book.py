"""Step 07 - a second API family: Webex Contact Center.

PREREQUISITE. Unlike steps 01-06, this one needs more than a developer token:

  * a Webex Contact Center organization, and a token whose scopes include
    cjp:config_read and cjp:config_write
  * WEBEX_ORG_ID   - your Contact Center organization id
  * WEBEX_CC_API_BASE - your data centre, e.g. https://api.wxcc-us1.cisco.com

If you do not have a Contact Center organization, stop here. Step 08 revisits
everything you need without it.

Nothing about MCP changes in this file. The decorators, the result shapes, and
the consent model are identical to step 04 - only the host and the URLs differ.
That is the point: once you can wrap one API, you can wrap any API.

Note there are no delete tools here. Address books are shared configuration and
this is a shared lab organization, so the destructive verbs are left out on
purpose. Cleaning up afterwards is an administrator's job.

Run it:
    python 07_address_book.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

# Load .env so the credentials are present however this script is launched -
# from a terminal or by an MCP client - with no --env-file flag needed.
load_dotenv()

TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")
CC_API_BASE = os.environ.get("WEBEX_CC_API_BASE", "")

# Check every credential at startup and name the one that is missing. A server
# that starts and then fails on each call is much harder to diagnose than one
# that refuses to start and says why.
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WEBEX_CC_API_BASE", CC_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This step needs Webex Contact Center - see .env.example.")

if "REGION" in CC_API_BASE:
    sys.exit("WEBEX_CC_API_BASE still says REGION. Replace it with your data centre, e.g. us1.")

ORG = f"{CC_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

mcp = MCPServer("webex-mcp-lab-07")


def _fail(response: httpx.Response) -> dict:
    """Turn an HTTP failure into a sentence the model can pass on to the user."""
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
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit}
        )

    if response.status_code != 200:
        return _fail(response)

    books = [
        {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
        for book in response.json().get("items", [])
    ]
    return {"count": len(books), "address_books": books}


@mcp.tool()
async def create_address_book(name: str, description: str = "") -> dict:
    """Create a new address book.

    Your MCP client asks for approval before this runs.
    """
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(
            f"{ORG}/v3/address-book",
            headers=HEADERS,
            json={"name": name, "description": description, "parentType": "ORGANIZATION"},
        )

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

    # Listing entries is the one operation on v2; the others below are v1.
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v2/address-book/{address_book_id}/entry", headers=HEADERS, params=params
        )

    if response.status_code != 200:
        return _fail(response)

    entries = [
        {"id": entry.get("id"), "name": entry.get("name"), "number": entry.get("number")}
        for entry in response.json().get("items", [])
    ]
    return {"count": len(entries), "entries": entries}


@mcp.tool()
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
    """Add a contact to an address book. `number` should be E.164, e.g. +14155550101.

    Your MCP client asks for approval before this runs.
    """
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(
            f"{ORG}/address-book/{address_book_id}/entry",
            headers=HEADERS,
            json={"name": name, "number": number},
        )

    if response.status_code not in (200, 201):
        return _fail(response)

    return {"added": True, "entry_id": response.json().get("id"), "name": name}


if __name__ == "__main__":
    mcp.run()
