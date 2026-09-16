"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Call the Meetings MCP tool webex-list-meetings with a fixed date window.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from mcp_client import McpClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-list-meetings")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
if not MEETING_TOKEN:
    raise SystemExit("Set WEBEX_MEETING_MCP_TOKEN in your .env file")


async def main():
    now = datetime.now(timezone.utc)
    arguments = {
        "from": now.strftime("%Y-%m-%dT00:00:00Z"),
        "to": (now + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59Z"),
        "meetingType": "scheduledMeeting",
    }
    log.info(f"Calling webex-list-meetings {arguments}")
    result = await McpClient(MEETING_TOKEN, MEETING_MCP_URL).call_tool(
        "webex-list-meetings",
        arguments,
    )
    if not result:
        return
    log.info(result)


if __name__ == "__main__":
    asyncio.run(main())
