"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 03 - the third primitive: a prompt (a workflow the user triggers).

import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-03")


@mcp.prompt()
def greet_team(team_name: str = "") -> str:
    """Greet every member of a team one by one.

    Prompt arguments become fields the client asks the user to fill in.
    What this returns is not an answer - it is the opening message of a
    workflow the model carries out with the tools and resources below.
    """
    return (
        f"Greet every member of the {team_name or '<team>'} team.\n"
        "\n"
        "1. Read the lab://greeting-style resource and follow its rules.\n"
        "2. For each person, call the greet tool with their first name.\n"
        "3. Show me each greeting before moving to the next person."
    )


@mcp.resource("lab://greeting-style")
def greeting_style() -> str:
    """How this organization prefers to greet people."""
    return (
        "Always use the person's first name. "
        "Keep it warm but professional. "
        "End with a note about the workshop."
    )


@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone by name. Read lab://greeting-style for the house rules."""
    return f"Hello, {name}! Welcome to the Webex One 2026 workshop."


if __name__ == "__main__":
    print(
        "webex-mcp-lab-03 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
