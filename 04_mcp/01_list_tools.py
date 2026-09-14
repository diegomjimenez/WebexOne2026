"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Connect to the Webex Messaging and Meetings MCP servers
"""

MESSAGING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-messaging"
MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp.shared.exceptions import MCPError

from mcp_client import McpClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-list-tools")

load_dotenv()

MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")


async def list_server(name, url, token):
    if not token:
        log.warning(f"Skipping {name}: set the token in your .env file")
        return
    try:
        tools = await McpClient(token, url).list_tools()
    except MCPError as exc:
        log.error(f"{name} handshake failed: {exc}")
        return
    log.info(f"{name}: {len(tools)} tool(s) from {url}")
    for tool in tools:
        log.info(f"  - {tool.name}: {tool.description}")


async def main():
    if not MESSAGING_TOKEN and not MEETING_TOKEN:
        raise SystemExit(
            "Set WEBEX_MESSAGING_MCP_TOKEN and/or WEBEX_MEETING_MCP_TOKEN in your .env file"
        )
    await list_server("Messaging MCP", MESSAGING_MCP_URL, MESSAGING_TOKEN)
    await list_server("Meetings MCP", MEETING_MCP_URL, MEETING_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
