"""Step 03 - returning a collection.

New in this step: the API returns a list, and we decide what the model sees.

Run it:
    python 03_rooms.py
"""

import os
import sys

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

WEBEX_API = "https://webexapis.com/v1"

# Load .env so the token is present however this script is launched - from a
# terminal or by an MCP client - with no --env-file flag needed.
load_dotenv()

# Read the token once, at startup. A missing token discovered mid-tool-call
# shows up as a confusing 401 instead of the clear message below.
TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
if not TOKEN:
    sys.exit("WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
             "your token, and re-run.")

mcp = MCPServer("webex-mcp-lab-03")


@mcp.tool()
async def list_rooms(limit: int = 20) -> dict:
    """List the Webex spaces this token can see, most recently active first.

    `limit` has a default, which makes it optional in the tool's schema - the
    model can call this with no arguments at all.
    """
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(
            f"{WEBEX_API}/rooms",
            headers={"Authorization": f"Bearer {TOKEN}"},
            params={"max": limit, "sortBy": "lastactivity"},
        )

    if response.status_code != 200:
        return {"error": f"Webex returned HTTP {response.status_code}."}

    # Webex wraps collections in an "items" key. Unwrap it, then keep only the
    # four useful fields - the raw record has around twenty, and every one we
    # pass along is context the model has to read and pay for.
    rooms = [
        {
            "id": room.get("id"),
            "title": room.get("title"),
            "type": room.get("type"),
            "last_activity": room.get("lastActivity"),
        }
        for room in response.json().get("items", [])
    ]
    return {"count": len(rooms), "rooms": rooms}


if __name__ == "__main__":
    mcp.run()
