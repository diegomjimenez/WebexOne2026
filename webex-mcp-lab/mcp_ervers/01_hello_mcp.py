"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 01 - the smallest MCP server: one tool, no network, no token.

import logging
import sys

from mcp.server import MCPServer

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webex")

# The decorator names below expose Python functions to any MCP client.
mcp = MCPServer("webex-mcp-lab-01")


@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone by name. The first MCP tool an assistant can call."""
    log.debug("greet called: name=%r", name)
    return f"Hello, {name}. Your first MCP tool just ran."


if __name__ == "__main__":
    # Banner to stderr - stdout carries the MCP protocol.
    print(
        "webex-mcp-lab-01 running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
