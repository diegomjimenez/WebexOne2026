"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - the second primitive: a resource (reference material the client attaches).

import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-02")


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
        "webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
