"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 05 - deleting with a safety net: elicitation asks "are you sure?" mid-call.

import os
import sys
from typing import Annotated

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

# Elicitation imports: the resolver pattern lets the server ask the user a question mid-call.
from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from pydantic import BaseModel

# Load credentials from .env.
load_dotenv()

TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")
CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")

# Stop early if any credential is missing.
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")

# Build the API base URL and common headers.
ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

# Create an MCP server instance.
mcp = MCPServer("webex-mcp-lab-05")


# The confirmation form the user sees: one boolean field.
class Confirm(BaseModel):
    ok: bool


# Resolver for address book deletion — always asks before proceeding.
async def confirm_delete_book(address_book_id: str) -> Elicit[Confirm]:
    return Elicit(f"Delete address book '{address_book_id}'? This cannot be undone.", Confirm)


# Resolver for entry deletion — always asks before proceeding.
async def confirm_delete_entry(address_book_id: str, entry_id: str) -> Elicit[Confirm]:
    return Elicit(
        f"Delete entry '{entry_id}' from book '{address_book_id}'? This cannot be undone.",
        Confirm,
    )


# Delete an address book after the user confirms via elicitation.
@mcp.tool()
async def delete_address_book(
    address_book_id: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_book)],
) -> dict:
    """Delete an address book by id. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.delete(
                    f"{ORG}/v3/address-book/{address_book_id}", headers=HEADERS
                )
            if r.status_code not in (200, 204):
                return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
            return {"deleted": True, "address_book_id": address_book_id}
        case AcceptedElicitation():
            return {"deleted": False, "reason": "You chose not to delete."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"deleted": False, "reason": "Confirmation was declined or dismissed."}


# Delete a single contact after the user confirms via elicitation.
@mcp.tool()
async def delete_entry(
    address_book_id: str,
    entry_id: str,
    confirm: Annotated[ElicitationResult[Confirm], Resolve(confirm_delete_entry)],
) -> dict:
    """Delete a single contact from an address book. The server asks you to confirm first."""
    match confirm:
        case AcceptedElicitation(data=Confirm(ok=True)):
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.delete(
                    f"{ORG}/v2/address-book/{address_book_id}/entry/{entry_id}",
                    headers=HEADERS,
                )
            if r.status_code not in (200, 204):
                return {"error": f"Webex Contact Center returned HTTP {r.status_code}."}
            return {"deleted": True, "entry_id": entry_id}
        case AcceptedElicitation():
            return {"deleted": False, "reason": "You chose not to delete."}
        case DeclinedElicitation() | CancelledElicitation():
            return {"deleted": False, "reason": "Confirmation was declined or dismissed."}


# Start the server on stdio and wait for a client to connect.
if __name__ == "__main__":
    print(
        "webex-mcp-lab-05 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
