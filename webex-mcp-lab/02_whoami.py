"""Step 02 - the first real Webex call.

New in this step: the tool actually talks to Webex, using a token read from
the environment.

Run it:
    python 02_whoami.py
"""

import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

WEBEX_API = "https://webexapis.com/v1"

# Server-side logging -> stderr (never stdout, which carries the MCP protocol),
# independent of the client, DEBUG by default. The token is never logged.
log = logging.getLogger("webex")
log.setLevel(logging.DEBUG)
log.propagate = False
log.addHandler(logging.StreamHandler(sys.stderr))

# Load .env so the token is present however this script is launched - from a
# terminal or by an MCP client - with no --env-file flag needed.
load_dotenv()

# Read the token once, at startup. A missing token discovered mid-tool-call
# shows up as a confusing 401 instead of the clear message below.
TOKEN = os.environ.get("WEBEX_ACCESS_TOKEN")
if not TOKEN:
    sys.exit("WEBEX_ACCESS_TOKEN is not set. Copy .env.example to .env, add "
             "your token, and re-run.")

mcp = MCPServer("webex-mcp-lab-02")


@mcp.tool()
async def whoami() -> dict:
    """Return the Webex identity that this server's token belongs to."""
    # Now that a real HTTP call is involved, the log earns its keep: you can
    # see the request leave and the status come back, without a debugger.
    log.debug("whoami: GET %s/people/me", WEBEX_API)
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(
            f"{WEBEX_API}/people/me",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    log.debug("whoami: Webex responded HTTP %s", response.status_code)

    if response.status_code != 200:
        # Hand the model a sentence, not a stack trace. It can relay this to
        # the user, and the server stays up for the next call.
        return {"error": f"Webex returned HTTP {response.status_code}."}

    person = response.json()

    # Return the three fields that matter, not the whole payload. Everything
    # here is read by a language model, so the token must never appear in it.
    return {
        "display_name": person.get("displayName"),
        "email": (person.get("emails") or [None])[0],
        "type": person.get("type"),
    }


if __name__ == "__main__":
    # A one-line banner to stderr so the terminal shows the server is alive.
    # It must go to stderr, not stdout - stdout carries the MCP protocol.
    print("webex-mcp-lab-02 running on stdio - waiting for a client (Ctrl+C to stop).",
          file=sys.stderr)
    mcp.run()
