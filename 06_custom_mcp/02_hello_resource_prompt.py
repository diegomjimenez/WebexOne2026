"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - all three MCP primitives (tool, resource, prompt) without credentials.

import sys
from mcp.server import MCPServer

# Create an MCP server instance.
mcp = MCPServer("webex-mcp-lab-02")


# Register a tool that counts words and characters in a piece of text.
@mcp.tool()
async def count_words(text: str) -> dict:
    """Count the words and characters in a piece of text."""
    words = text.split()
    return {"words": len(words), "characters": len(text)}


# Register a resource with greeting rules the tool cannot know on its own.
@mcp.resource("lab://greeting-rules")
def greeting_rules() -> str:
    return (
        "Webex Contact Center greeting rules for this organization:\n"
        "1. 12 words maximum.\n"
        "2. Must include the agent's first name.\n"
        "3. Never use 'ASAP' or 'obviously'.\n"
    )


# Register a prompt that chains the resource and the tool into a review workflow.
@mcp.prompt()
def review_greeting(greeting: str = "") -> str:
    """Review an agent greeting against the organization rules."""
    return (
        f"Review this agent greeting:\n\n"
        f"{greeting or '<paste a greeting here>'}\n\n"
        "1. Read the lab://greeting-rules resource for the org rules.\n"
        "2. Call count_words to measure the greeting.\n"
        "3. Tell me pass or fail, and why."
    )


# Start the server on stdio and wait for a client to connect.
if __name__ == "__main__":
    print(
        "webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
