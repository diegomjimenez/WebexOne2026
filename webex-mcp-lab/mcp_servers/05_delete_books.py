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

# Elicitation: the server pauses a tool call to ask the user a question.
# These imports wire that up with the resolver pattern (works on every client).
from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from pydantic import BaseModel

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

mcp = MCPServer("webex-mcp-lab-05")


# ---------------------------------------------------------------------------
# The confirmation schema and resolver — shared by both delete tools.
# ---------------------------------------------------------------------------

class Confirm(BaseModel):
    """The user sees one boolean field: 'ok'. That is the entire form."""
    ok: bool


# WHO is asked? The USER, via a form rendered by the MCP client.
# WHEN? Before the delete tool body runs — the resolver runs first.
async def confirm_delete_book(address_book_id: str) -> Elicit[Confirm]:
    """Always ask — deletion is irreversible."""
    return Elicit(f"Delete address book '{address_book_id}'? This cannot be undone.", Confirm)


async def confirm_delete_entry(address_book_id: str, entry_id: str) -> Elicit[Confirm]:
    """Always ask — deletion is irreversible."""
    return Elicit(
        f"Delete entry '{entry_id}' from book '{address_book_id}'? This cannot be undone.",
        Confirm,
    )


# ---------------------------------------------------------------------------
# Delete tools — guarded by elicitation.
# The id to delete comes from the create→fill→delete narrative (chapters 03/04),
# not from a list tool in this chapter.
# ---------------------------------------------------------------------------

# WHAT happens for each outcome:
#   AcceptedElicitation(ok=True)  → DELETE fires, item is removed.
#   AcceptedElicitation(ok=False) → user submitted the form but said "no" — skip.
#   DeclinedElicitation           → user clicked "decline" — skip.
#   CancelledElicitation          → user dismissed the dialog — skip.

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


if __name__ == "__main__":
    print(
        "webex-mcp-lab-05 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
