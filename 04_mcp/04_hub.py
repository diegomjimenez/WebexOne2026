"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

LLM sees Messaging and Meetings tools together.
It picks a tool name; McpHub sends the call to the server that advertised it.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from llm import as_openai_tools, run_turn
from mcp_hub import McpHub

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MESSAGING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-messaging"
MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
QUESTION = "What meetings do I have this week, and how many spaces do I have?"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-hub")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MESSAGING_TOKEN = os.getenv("WEBEX_MESSAGING_MCP_TOKEN")
MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")
if not MESSAGING_TOKEN and not MEETING_TOKEN:
    raise SystemExit(
        "Set WEBEX_MESSAGING_MCP_TOKEN and/or WEBEX_MEETING_MCP_TOKEN in your .env file"
    )


async def main():
    hub = McpHub(
        [
            (MESSAGING_MCP_URL, MESSAGING_TOKEN),
            (MEETING_MCP_URL, MEETING_TOKEN),
        ]
    )
    tools = as_openai_tools(await hub.list_tools())
    log.info(f"Offering {len(tools)} tool(s) from {len(hub.clients)} MCP server(s) to {OPENAI_MODEL}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You help a Webex user with messaging and meetings. Today is {today} (UTC). "
                "Answer only from tool results, never from memory, and keep replies short."
            ),
        },
        {"role": "user", "content": QUESTION},
    ]
    return await run_turn(hub, messages, tools)


if __name__ == "__main__":
    log.info(f"Question: {QUESTION}")
    log.info(asyncio.run(main()))
