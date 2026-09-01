"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - the second primitive: a resource (reference material the client attaches).

import re
import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-02")


# WHO reads this? The CLIENT (not the server, not the tool below).
# The client fetches the text and hands it to the model as context, like
# dropping a spec sheet into the conversation. Nothing in this file calls
# phone_format_rules() itself - that is the client's job.
@mcp.resource("lab://phone-format")
def phone_format_rules() -> str:
    return (
        "Phone numbers must be in E.164 format:\n"
        "- Start with a leading '+'.\n"
        "- Country code, then subscriber number.\n"
        "- Digits only. No spaces, dashes, or parentheses.\n"
        "Examples: +14155550101 (US), +447700900123 (UK).\n"
        "Note: format_phone assumes '+1' when given exactly 10 digits."
    )


# WHO calls this? The AI assistant, once it has seen the rules above.
# WHERE does the return go? Back to the assistant, which shows it to the user.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form. See lab://phone-format for the rules."""
    digits = re.sub(r"\D", "", number)
    if not number.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


if __name__ == "__main__":
    print(
        "webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
