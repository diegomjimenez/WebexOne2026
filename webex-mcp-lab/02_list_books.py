"""Step 02 - the first real Webex call: list address books.

Step 01 answered "what makes a function callable by an assistant?" with no
network at all. This step makes the tool actually talk to Webex Contact Center
and hand back a real collection - the address books configured in your
organization.

Everything from here on uses one domain: Contact Center address books. One API,
one set of credentials, one mental model, all the way to the modular finale.

PREREQUISITE. Unlike step 01, this needs three things in your `.env`:

  * WEBEX_ACCESS_TOKEN  - a token whose scopes include cjp:config_read
  * WEBEX_ORG_ID        - your Contact Center organization id
  * WXCC_CONFIG_API_BASE - your data centre, e.g. https://api.wxcc-us1.cisco.com

Run it:
    python 02_list_books.py
"""

import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

# Server-side logging. Two sinks now: the live stderr stream AND a file beside
# this script (02_list_books.log), both carrying the same DEBUG lines in one
# shared format. stderr is never stdout - stdout carries the MCP protocol. The
# log is independent of the client and never records the token.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
for _handler in (
    logging.StreamHandler(sys.stderr),
    logging.FileHandler(Path(__file__).with_suffix(".log"), encoding="utf-8"),
):
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    log.addHandler(_handler)

# Load .env so the credentials are present however this script is launched -
# from a terminal or by an MCP client - with no --env-file flag needed.
load_dotenv()

TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
ORG_ID = os.environ.get("WEBEX_ORG_ID")
CONFIG_API_BASE = os.environ.get("WXCC_CONFIG_API_BASE", "")

# Check every credential at startup and name the one that is missing. A server
# that starts and then fails on each call is much harder to diagnose than one
# that refuses to start and says why.
for _name, _value in (
    ("WEBEX_ACCESS_TOKEN", TOKEN),
    ("WEBEX_ORG_ID", ORG_ID),
    ("WXCC_CONFIG_API_BASE", CONFIG_API_BASE),
):
    if not _value:
        sys.exit(f"{_name} is not set. This lab needs Webex Contact Center - see .env.example.")

ORG = f"{CONFIG_API_BASE.rstrip('/')}/organization/{ORG_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

mcp = MCPServer("webex-mcp-lab-02")


@mcp.tool()
async def list_address_books(limit: int = 50) -> dict:
    """List the address books configured in this Contact Center organization."""
    # One DEBUG line before the call and one after: proof, in the terminal and
    # in the log file, that the model reached your code and what Webex said.
    log.debug("list_address_books: GET %s/v3/address-book", ORG)
    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.get(
            f"{ORG}/v3/address-book", headers=HEADERS, params={"pageSize": limit}
        )
    log.debug("list_address_books: Webex responded HTTP %s", response.status_code)

    if response.status_code != 200:
        return {"error": f"Webex Contact Center returned HTTP {response.status_code}."}

    # Webex wraps collections in an "items" key. Unwrap it, then keep only the
    # three useful fields - the raw record has many more, and every one we pass
    # along is context the model has to read and pay for.
    books = [
        {"id": book.get("id"), "name": book.get("name"), "description": book.get("description")}
        for book in response.json().get("items", [])
    ]
    return {"count": len(books), "address_books": books}


if __name__ == "__main__":
    # A one-line banner to stderr so the terminal shows the server is alive.
    # It must go to stderr, not stdout - stdout carries the MCP protocol.
    print("webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
          file=sys.stderr)
    mcp.run()
