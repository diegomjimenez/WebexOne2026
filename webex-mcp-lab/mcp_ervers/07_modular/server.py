"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam
"""
# Step 07 - the same server, built to grow: one file per domain.
#
# To add a Webex API family, write tools/<domain>.py with a
# register(mcp, client) function and add it to the DOMAINS list below.

import logging
import sys

from mcp.server import MCPServer

from tools import address_books
from webex_client import WebexClient

# "webex" logger is configured in webex_client.py - we just ask for it by name.
log = logging.getLogger("webex")

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

    print(
        "webex-mcp-lab running on stdio - waiting for a client (Ctrl+C to stop).",
        file=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()
