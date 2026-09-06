"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 04 - writing: create an address book, then fill it with contacts.

import os
import sys
import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer


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

mcp = MCPServer("webex-mcp-lab-04")


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
async def create_address_book(name: str, description: str = "") -> dict:
    """Create a new address book. Returns its id, which add_entry then needs.

    The MCP client asks the user for approval before this runs.
    """
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(
            f"{ORG}/v3/address-book",
            headers=HEADERS,
            json={"name": name, "description": description, "parentType": "ORGANIZATION"},)

    if response.status_code not in (200, 201):
        return _fail(response)

    book = response.json()
    return {"created": True, "address_book_id": book.get("id"), "name": book.get("name")}


@mcp.tool()
async def add_entry(address_book_id: str, name: str, number: str) -> dict:
    """Add a contact to an address book. `number` should be E.164, e.g. +14155550101.

    `address_book_id` is what create_address_book returned. The MCP client asks
    the user for approval before this runs.
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
    print(
        "webex-mcp-lab-04 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
