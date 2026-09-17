"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 01 - the smallest MCP server: one tool, no network, no token.

import logging
import re
from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hello-mcp")

# Create an MCP server instance.
mcp = MCPServer("hello-mcp")


# Register a tool that cleans a phone number to E.164 format.
@mcp.tool()
async def format_phone(number: str) -> str:
    """Clean a phone number to E.164 form, e.g. +14155550101."""
    digits = re.sub(r"\D", "", number)
    if not number.startswith("+") and len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


# Start the server on stdio and wait for a client to connect.
if __name__ == "__main__":
    log.info("hello-mcp running on stdio - waiting for a client (Ctrl+C to stop).")
    try:
        mcp.run()
    except KeyboardInterrupt:
        log.info("Stopped.")
