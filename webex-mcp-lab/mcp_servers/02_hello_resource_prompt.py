"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - all three MCP primitives (tool, resource, prompt) without credentials.

import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-02")


# WHO calls this? The AI assistant, when the prompt workflow asks it to measure text.
# WHERE does the return go? Back to the assistant, which compares against the rules.
@mcp.tool()
async def count_words(text: str) -> dict:
    """Count the words and characters in a piece of text."""
    words = text.split()
    return {"words": len(words), "characters": len(text)}


# WHO reads this? The CLIENT, which passes the text to the model as context.
# The tool above knows how to count — but it has no idea what the limits are.
# Only this resource says "12 words max" and "never say ASAP". That is why
# a resource matters: it carries rules the tool cannot encode.
@mcp.resource("lab://greeting-rules")
def greeting_rules() -> str:
    return (
        "Rules for agent chat greetings:\n"
        "1. 12 words maximum.\n"
        "2. Must include the agent's first name.\n"
        "3. Never use 'ASAP' or 'obviously'.\n"
    )


# WHO triggers this? The USER, from a slash command or menu in their client.
# The returned text becomes the opening message the model sees, chaining
# the resource and the tool into a single review workflow.
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


if __name__ == "__main__":
    print(
        "webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
