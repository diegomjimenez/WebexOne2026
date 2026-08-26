"""Step 04 - the first write.

New in this step: a tool that changes something. Everything up to now only read.

Look closely at `send_message` and notice what is *not* in it: no `confirm`
argument, no dry-run mode, no approval prompt raised by the server. It posts
the message. That is deliberate, and the docstring explains why.

Run it:
    python 04_send_message.py
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

mcp = MCPServer("webex-mcp-lab-04")


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


@mcp.tool()
async def send_message(room_id: str, text: str) -> dict:
    """Post a message to a Webex space.

    Use `list_rooms` first to find the room_id.

    This tool writes, and it asks you for nothing before doing so. It does not
    need to: your MCP client shows you the tool name and both arguments and
    waits for your approval before this function is ever entered. Approval is
    the host's job, not the server's, and that is true of every MCP server you
    will write. Building a second approval step in here would only teach people
    to click through two dialogs instead of one.
    """
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.post(
            f"{WEBEX_API}/messages",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"roomId": room_id, "text": text},
        )

    if response.status_code not in (200, 201):
        return {"error": f"Webex returned HTTP {response.status_code}."}

    message = response.json()
    return {
        "sent": True,
        "message_id": message.get("id"),
        "room_id": message.get("roomId"),
        "created": message.get("created"),
    }


if __name__ == "__main__":
    mcp.run()
