"""Messaging domain - spaces and messages, from steps 03 to 06.

Registers two tools, one resource, and one prompt, which is all three MCP
primitives in a single domain module.
"""

from webex_client import WEBEX_API, failure


def register(mcp, client) -> None:
    """Add this domain's tools, resource, and prompt to the server."""

    @mcp.tool()
    async def list_rooms(limit: int = 20) -> dict:
        """List the Webex spaces this token can see, most recently active first."""
        response = await client.request(
            "GET", f"{WEBEX_API}/rooms", params={"max": limit, "sortBy": "lastactivity"}
        )
        if response.status_code != 200:
            return failure(response)

        rooms = [
            {"id": room.get("id"), "title": room.get("title"), "type": room.get("type")}
            for room in response.json().get("items", [])
        ]
        return {"count": len(rooms), "rooms": rooms}

    @mcp.tool()
    async def send_message(room_id: str, text: str) -> dict:
        """Post a message to a Webex space. Use `list_rooms` first to find the room_id.

        Your MCP client asks for your approval before this runs. The server
        does not ask a second time.
        """
        response = await client.request(
            "POST", f"{WEBEX_API}/messages", json={"roomId": room_id, "text": text}
        )
        if response.status_code not in (200, 201):
            return failure(response)

        message = response.json()
        return {"sent": True, "message_id": message.get("id"), "created": message.get("created")}

    @mcp.resource("webex://guidelines/posting")
    def posting_guidelines() -> str:
        """House style for messages posted by an assistant."""
        return (
            "# Posting guidelines\n"
            "\n"
            "- Open with what happened, not with a greeting.\n"
            "- One message per topic. Do not batch unrelated updates.\n"
            "- Name the person you need something from, and say what you need.\n"
            "- Never post credentials, tokens, or customer phone numbers.\n"
        )

    @mcp.prompt()
    def post_status_update(space: str = "", topic: str = "") -> str:
        """Draft a status update and post it to a Webex space."""
        return (
            f"Post a status update about {topic or '<topic>'} to the "
            f"{space or '<space>'} space.\n"
            "\n"
            "1. Read the webex://guidelines/posting resource and follow it.\n"
            "2. Call list_rooms to find the space and get its id.\n"
            "3. Show me the draft before sending, then call send_message."
        )
