"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - first real Webex call: list Contact Center address books.

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

# Fail fast at startup and name the missing credential.
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")

ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

mcp = MCPServer("webex-mcp-lab-02")


@mcp.tool()
async def list_address_books(limit: int = 50) -> dict:
    """List the address books configured in this Contact Center organization."""
    # URL only, never the token.
    log.debug("list_address_books: GET %s/v3/address-book", ORG)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit}
        )
    log.debug("list_address_books: Webex responded HTTP %s", response.status_code)

    if response.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}

    # Collections come back under "data"; return only the fields the model needs.
    books = [
        {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
        for book in response.json().get("data", [])
    ]
    return {"count": len(books), "address_books": books}


if __name__ == "__main__":
    print(
        "webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
