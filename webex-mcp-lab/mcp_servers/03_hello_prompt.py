"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 03 - the third primitive: a prompt (a workflow the user triggers).

import re
import sys
from mcp.server import MCPServer

mcp = MCPServer("webex-mcp-lab-03")


# WHO triggers this? The USER, from a slash command or menu in their client.
# The prompt argument (raw_numbers) becomes a field the client asks the user
# to fill in. WHAT we return here is not an answer - it becomes the opening
# message the model sees, as if the user had typed it. The model then reads
# lab://phone-format and calls format_phone once per line to carry it out.
@mcp.prompt()
def clean_contact_list(raw_numbers: str = "") -> str:
    return (
        "Clean these phone numbers to E.164 format:\n\n"
        f"{raw_numbers or '<paste your numbers here, one per line>'}\n\n"
        "1. Read the lab://phone-format resource first.\n"
        "2. Call format_phone once for every line above and collect the results.\n"
        "3. Show me the cleaned list. Flag any line that looks invalid."
    )


# WHO reads this? The CLIENT, which passes the text to the model as context.
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


# WHO calls this? The MODEL, once per number in the user's list.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form. See lab://phone-format for the rules."""
    digits = re.sub(r"\D", "", number)
    if not number.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


if __name__ == "__main__":
    print(
        "webex-mcp-lab-03 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
