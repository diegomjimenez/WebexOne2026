"""Step 05 - the second primitive: a resource.

New in this step: `posting_guidelines`, registered with @mcp.resource.

Tools and resources are both things the server offers, and the difference is
who reaches for them. A tool is an action the *model* decides to take. A
resource is reference material the *client* can attach to the conversation,
the way you would attach a file. Nothing happens when a resource is read.

The resource below is a house style for messages. Read it, then look at
`send_message` - the resource is what tells the model how to use the tool.

Run it:
    python 05_resource.py
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

mcp = MCPServer("webex-mcp-lab-05")


@mcp.resource("webex://guidelines/posting")
def posting_guidelines() -> str:
    """House style for messages posted by an assistant.

    The URI above is how a client refers to this resource. The docstring is
    what the client shows in its picker.
    """
    return (
        "# Posting guidelines\n"
        "\n"
        "- Open with what happened, not with a greeting.\n"
        "- One message per topic. Do not batch unrelated updates.\n"
        "- Name the person you need something from, and say what you need.\n"
        "- Never post credentials, tokens, or customer phone numbers.\n"
        "- If a message would be longer than five lines, post a summary and\n"
        "  offer the detail on request.\n"
    )


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
    """Post a message to a Webex space, following the posting guidelines resource.

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
