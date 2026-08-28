"""Step 01 - the smallest MCP server that works.

No Webex, no network, no token. The only question this file answers is:
what does it take to make a Python function callable by an AI assistant?

Run it:
    python 01_hello_mcp.py

It prints one line to stderr to say it is ready, then waits silently. That is
correct - an MCP server talks over stdin and stdout, so there is nothing more to
see until a client connects to it.

It also keeps a log. Every tool call writes a DEBUG line to stderr so you can
watch the server work. That log goes to stderr on purpose - stdout carries the
MCP protocol - and it does not depend on the client at all.
"""

import logging
import sys

from mcp.server import MCPServer

# Server-side logging -> stderr (never stdout, which carries the MCP protocol),
# independent of the client, DEBUG by default. The token is never logged.
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
log.addHandler(logging.StreamHandler(sys.stderr))

# The server. Its name is what an MCP client displays in its UI.
#
# Note for anyone following an older tutorial: this class used to be called
# FastMCP and lived in mcp.server.fastmcp. It was renamed in the 2.x SDK.
mcp = MCPServer("webex-mcp-lab-01")


@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone by name.

    Three things happen because of the decorator above:

    1. The client discovers a tool called `greet`.
    2. This docstring becomes the tool's description - it is how the model
       decides whether this tool is the right one to call.
    3. The `name: str` annotation becomes the tool's input schema, so the
       client knows to send one string argument.

    That is the whole idea. A tool is a function the model is allowed to call.
    """
    # One DEBUG line per call. This is the whole point of the log: proof, in
    # the terminal, that the model reached your code and with what argument.
    log.debug("greet called: name=%r", name)
    return f"Hello, {name}. Your first MCP tool just ran."


if __name__ == "__main__":
    # A one-line banner to stderr so the terminal shows the server is alive.
    # It must go to stderr, not stdout - stdout carries the MCP protocol.
    print("webex-mcp-lab-01 running on stdio - waiting for a client (Ctrl+C to stop).",
          file=sys.stderr)
    mcp.run()
