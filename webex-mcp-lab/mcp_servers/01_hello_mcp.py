"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 01 - the smallest MCP server: one tool, no network, no token.

import re
import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-01")


# WHO calls this? The AI assistant, when the user asks to clean a number.
# WHERE does the return go? Straight back to the assistant, which shows it
# to the user. The Python here runs on the server; the assistant does not.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form, e.g. +14155550101."""
    digits = re.sub(r"\D", "", number)
    if not number.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


if __name__ == "__main__":
    print(
        "webex-mcp-lab-01 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
