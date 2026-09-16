"""
Webex One 2026 - Troubleshoot and Manage Your Organization with an AI Assistant

- Diego Manuel Jimenez Moreno
- Mo Eyad Musallam

Ask a pre-defined question question to the LLM. 
The LLM receives the Meetings MCP tools and decides which one to call.
LLM replies in natural language.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from llm import as_openai_tools, run_turn
from mcp_client import McpClient

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

MEETING_MCP_URL = "https://mcp.webexapis.com/mcp/webex-meeting"
QUESTION = "What meetings do I have scheduled this week?"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-llm")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MEETING_TOKEN = os.getenv("WEBEX_MEETING_MCP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
if not MEETING_TOKEN:
    raise SystemExit("Set WEBEX_MEETING_MCP_TOKEN in your .env file")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in your .env file")


async def main():
    client = McpClient(MEETING_TOKEN, MEETING_MCP_URL)
    tools = as_openai_tools(await client.list_tools())
    log.info(f"Offering {len(tools)} Meetings MCP tool(s) to {OPENAI_MODEL}")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    messages = [
        {
            "role": "system",
            "content": (
                f"You help a Webex user with their meetings. Today is {today} (UTC). "
                "Answer only from tool results, never from memory, and keep replies short."
            ),
        },
        {"role": "user", "content": QUESTION},
    ]
    return await run_turn(client, messages, tools)


if __name__ == "__main__":
    log.info(f"Question: {QUESTION}")
    log.info(asyncio.run(main()))
