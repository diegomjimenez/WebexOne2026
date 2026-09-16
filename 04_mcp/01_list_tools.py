"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Connect to the Webex Meetings MCP server and list its tools.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from mcp_client import McpClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MEETING_MCP_URL = os.getenv("WEBEX_MEETING_MCP_URL", "https://mcp.webexapis.com/mcp/webex-meeting")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-list-tools")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
if not MEETING_TOKEN:
    raise SystemExit("Set WEBEX_MEETING_MCP_TOKEN in your .env file")


async def main():
    tools = await McpClient(MEETING_TOKEN, MEETING_MCP_URL).list_tools()
    if not tools:
        return
    log.info(f"{len(tools)} tool(s) from {MEETING_MCP_URL}")
    for tool in tools:
        log.info(f"  - {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
