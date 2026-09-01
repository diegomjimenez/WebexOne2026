"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 02 - the second primitive: a resource (organizational policy the client attaches).

import re
import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-02")


# WHO reads this? The CLIENT (not the server, not the tool below).
# The client fetches the text and hands it to the model as context, so the
# model sees the ORG RULES the tool code does not enforce. format_phone
# only knows how to normalize digits; only this resource says which
# countries are allowed and which ranges are reserved.
@mcp.resource("lab://phone-policy")
def phone_policy() -> str:
    return (
        "phone-number policy for this organization:\n"
        "\n"
        "1. Allowed country codes: +1 (US/Canada), +44 (UK), +49 (Germany).\n"
        "   Numbers with any other country code MUST be refused.\n"
        "\n"
        "2. The +1-555-0100 through +1-555-0199 range is reserved for\n"
        "   internal testing. Refuse any number in that range.\n"
        "\n"
        "3. Normalize with format_phone before checking rules 1 and 2."
    )


# WHO calls this? The AI assistant, after reading the policy above.
# WHERE does the return go? Back to the assistant, which then decides
# whether the cleaned number satisfies the policy before showing the user.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form. See lab://phone-policy for organization rules."""
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
