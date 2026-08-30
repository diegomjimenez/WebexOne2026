"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 01 (companion) - Python logging vs the deprecated ctx.log().
#
#   1. Python `logging` -> stderr, server-owned, always works. Use this.
#   2. `ctx.log()`      -> JSON-RPC notification to the client. Deprecated by
#                          SEP-2577 (2026-07-28); still runs but warns.

import logging
import sys
import warnings

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*logging capability.*")

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("webex")

mcp = MCPServer("webex-mcp-lab-01-protocol-log")


@mcp.tool()
async def greet(name: str, ctx: Context) -> str:
    """Greet someone by name, showing both logging paths."""
    # Durable: server-owned, visible in the terminal no matter which client called.
    log.debug("greet called: name=%r", name)
    # Deprecated: sent to the client over JSON-RPC only if it opted in.
    await ctx.log("debug", f"greet called: name={name!r}")
    return f"Hello, {name}. This tool used both Python logging AND ctx.log()."


if __name__ == "__main__":
    print(
        "webex-mcp-lab-01-protocol-log running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()
