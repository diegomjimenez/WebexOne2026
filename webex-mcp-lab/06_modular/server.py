"""Step 06 - the same server, built to grow.

Steps 01 to 05 each put everything in one file, which is the right shape for
learning and the wrong shape for a server you keep. This one splits into three
kinds of file and nothing else:

    webex_client.py   credentials and HTTP, resolved once
    tools/<domain>.py one file per subject area
    server.py         this file - decides which domains are switched on

The whole extension mechanism is the DOMAINS list below. To add a subject area,
write `tools/your_domain.py` with a `register(mcp, client)` function and add it
to the list. Nothing else in the server changes, and no existing domain module
is touched. To switch one off, delete its line.

Right now there is one domain, `address_books`, and it carries every primitive
the lab taught - four tools, a resource, and a prompt. `tools/_template.py` is
the starting point for a second API family (Calling, Meetings, ...); it is
deliberately absent from DOMAINS until you wire it in.

Run it:
    python 06_modular/server.py
"""

import logging
import sys

from mcp.server import MCPServer

from tools import address_books
from webex_client import WebexClient

# The "webex" logger is configured once in webex_client, imported above. Here
# we only ask for it by name - same logger, same stderr and file handlers, no
# setup.
log = logging.getLogger("webex")

# Registration is an explicit list, not a directory scan. You can read this and
# know precisely what the server exposes - and so can a reviewer.
DOMAINS = [
    address_books,
]


def main() -> None:
    """Resolve credentials once, hand them to every domain, and serve."""
    client = WebexClient()
    mcp = MCPServer("webex-mcp-lab")

    for domain in DOMAINS:
        log.debug("registering domain: %s", domain.__name__)
        domain.register(mcp, client)

    # A one-line banner to stderr so the terminal shows the server is alive.
    # It must go to stderr, not stdout - stdout carries the MCP protocol.
    print("webex-mcp-lab running on stdio - waiting for a client (Ctrl+C to stop).",
          file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
