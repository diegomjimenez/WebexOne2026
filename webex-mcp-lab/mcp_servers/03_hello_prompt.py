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
# lab://phone-policy, calls format_phone on each line, and PARTITIONS the
# results according to policy.
@mcp.prompt()
def clean_contact_list(raw_numbers: str = "") -> str:
    return (
        "Review these phone numbers against our policy:\n\n"
        f"{raw_numbers or '<paste numbers here, one per line - policy will be applied>'}\n\n"
        "1. Read the lab://phone-policy resource for the org rules.\n"
        "2. Call format_phone once for every line to normalize it.\n"
        "3. Reject any number that violates rule 1 (country) or rule 2 (test range).\n"
        "4. Return two lists back to me: accepted (E.164) and rejected (with reason)."
    )


# WHO reads this? The CLIENT, which passes the text to the model as context.
@mcp.resource("lab://phone-policy")
def phone_policy() -> str:
    return (
        "Contact Center phone-number policy for this organization:\n"
        "\n"
        "1. Allowed country codes: +1 (US/Canada), +44 (UK), +49 (Germany).\n"
        "   Numbers with any other country code MUST be refused.\n"
        "\n"
        "2. The +1-555-0100 through +1-555-0199 range is reserved for\n"
        "   internal testing. Refuse any number in that range.\n"
        "\n"
        "3. Normalize with format_phone before checking rules 1 and 2."
    )


# WHO calls this? The MODEL, once per number in the user's list.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form. See lab://phone-policy for organization rules."""
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
