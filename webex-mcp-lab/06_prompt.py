"""Step 06 - the third primitive: a prompt.

New in this step: `post_status_update`, registered with @mcp.prompt.

Now all three primitives are in one file, and the split is worth naming:

    tool      the model decides to call it        an action
    resource  the client attaches it              reference material
    prompt    the *user* picks it from a menu     a starting point

A prompt is a pre-written request, usually surfaced as a slash command or a
menu item. It is the one primitive a human triggers directly.

Run it:
    uv run --env-file .env python 06_prompt.py
"""

import os
import sys

import httpx
from mcp.server import MCPServer

WEBEX_API = "https://webexapis.com/v1"

# Read the token once, at startup. A missing token discovered mid-tool-call
# shows up as a confusing 401 instead of the clear message below.
TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
if not TOKEN:
    sys.exit("WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
             "your token, and re-run with --env-file .env")

mcp = MCPServer("webex-mcp-lab-06")


@mcp.prompt()
def post_status_update(space: str = "", topic: str = "") -> str:
    """Draft a status update and post it to a Webex space.

    The arguments become fields the client asks the user to fill in. What this
    returns is not an answer - it is the opening message of a conversation,
    which the model then carries out using the tools below.
    """
    return (
        f"Post a status update about {topic or '<topic>'} to the "
        f"{space or '<space>'} space.\n"
        "\n"
        "1. Read the webex://guidelines/posting resource and follow it.\n"
        "2. Call list_rooms to find the space and get its id.\n"
        "3. Show me the draft and the space you picked before sending.\n"
        "4. Once I approve, call send_message."
    )


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
