"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Test the Service App token against the Messaging MCP server:
list the tools and call webex-search-spaces.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '04_mcp'))
from mcp_client import McpClient

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MESSAGING_MCP_URL = os.getenv("WEBEX_MESSAGING_MCP_URL", "https://mcp.webexapis.com/mcp/webex-messaging")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-service-app")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# We use the token generated from the UI or the refresh script
SERVICE_APP_TOKEN = os.getenv("ACCESS_TOKEN")

if not SERVICE_APP_TOKEN:
    raise SystemExit("Set ACCESS_TOKEN in your .env file")

async def main():
    log.info("Connecting to Messaging MCP with Service App token...")

    client = McpClient(SERVICE_APP_TOKEN, MESSAGING_MCP_URL)

    # List tools to prove the token is authorized for spark:mcp
    tools = await client.list_tools()

    if not tools:
        log.warning("No tools found or connection failed.")
        return

    log.info(f"Success! Found {len(tools)} tool(s) available for the Service App")

    # Call a tool: a machine has no spaces of its own, so expect an empty list
    arguments = {"max": 10}
    log.info(f"Calling webex-search-spaces {arguments}")
    result = await client.call_tool("webex-search-spaces", arguments)
    if not result:
        return
    log.info(result)

if __name__ == "__main__":
    asyncio.run(main())
